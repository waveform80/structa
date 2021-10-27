# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import io
import re
import csv
import json
import warnings
from chardet.universaldetector import UniversalDetector

from .errors import ValidationWarning

try:
    from ruamel import yaml
except ImportError:
    yaml = None


class Source:
    """
    A generalized data source capable of automatically recognizing certain
    popular data formats, and guessing character encodings. Constructed with a
    mandatory file-like object as the *source*, and a multitude of keyword-only
    options, the decoded content can be access from :attr:`data`

    The *source* must have a :meth:`~io.RawIOBase.read` method which, given a
    number of bytes to return, returns a :class:`bytes` string up to that
    length, but has no requirements beyond this. Note that this means files
    over sockets or pipes are acceptable inputs.

    :param file source:
        The file-like object to decode (must have a ``read`` method).
    :param str encoding:
        The character encoding used in the source, or "auto" (the default) if
        it should be guessed from a sample of the data.
    :param bool encoding_strict:
        If :data:`True` (the default), raise an exception if character decoding
        errors occur. Otherwise, replace invalid characters silently.
    :param str format:
        If "auto" (the default), guess the format of the data source. Otherwise
        can be explicitly set to "csv", "yaml", or "json" to force parsing of
        that format.
    :param str csv_delimiter:
        If "auto" (the default), attempt to guess the field delimiter when the
        "csv" format is being decoded using the :class:`csv.Sniffer` class.
        Comma, semi-colon, space, and tab characters will be attempted.
        Otherwise must be set to the single character :class:`str` used as the
        field delimiter (e.g. ",").
    :param str csv_quotechar:
        If "auto" (the default), attempt to guess the string delimiter when the
        "csv" format is being decoded using the :class:`csv.Sniffer` class.
        Otherwise must be set to the single character :class:`str` used as the
        string delimiter (e.g. '"').
    :param bool yaml_safe:
        If :data:`True` (the default) the "safe" YAML parser from
        `ruamel.yaml`_ will be used.
    :param bool json_strict:
        If :data:`True` (the default), control characters will not be permitted
        inside decoded strings.
    :param int sample_limit:
        The number of bytes to sample from the beginning of the stream when
        attempting to determine character encoding. Defaults to 1MB.

    .. _ruamel.yaml: https://pypi.org/project/ruamel.yaml/
    """
    def __init__(self, source, *, encoding='auto', encoding_strict=True,
                 format='auto', csv_delimiter='auto', csv_quotechar='auto',
                 yaml_safe=True, json_strict=True, sample_limit=1048576):
        self._source = source
        self._encoding = encoding
        self._encoding_strict = encoding_strict
        self._format = format
        self._csv_delimiter = csv_delimiter
        self._csv_quotechar = csv_quotechar
        self._csv_dialect = None
        self._yaml_safe = yaml_safe
        self._json_strict = json_strict
        self._sample_limit = sample_limit
        self._sample = b''
        self._data = None

    @property
    def encoding(self):
        """
        The character encoding detected or specified for the source, e.g.
        "utf-8".
        """
        if self._encoding == 'auto':
            self._detect_encoding()
        return self._encoding

    @property
    def format(self):
        """
        The data format detected or specified for the source, e.g. "csv",
        "yaml", or "json".
        """
        if self._format == 'auto':
            self._detect_format()
        return self._format

    @property
    def csv_dialect(self):
        """
        The :class:`csv.Dialect` used when :attr:`format` is "csv", or
        :data:`None` otherwise.
        """
        if self.format == 'csv':
            if self._csv_dialect is None:
                self._detect_csv_dialect()
            return self._csv_dialect
        else:
            return None

    @property
    def data(self):
        """
        The decoded data. Typically a :class:`list` or :class:`dict` of values,
        but can be any value representable in the source format.
        """
        if self._data is None:
            self._load_data()
        return self._data

    def _sample_bytes(self):
        if len(self._sample) < self._sample_limit:
            self._sample += self._source.read(
                self._sample_limit - len(self._sample))
        return self._sample

    def _sample_str(self):
        return self._sample_bytes().decode(self.encoding, errors='replace')

    def _detect_encoding(self):
        detector = UniversalDetector()
        detector.feed(self._sample_bytes())
        result = detector.close()
        if result['confidence'] < 0.9:
            warnings.warn(ValidationWarning(
                'Low confidence ({confidence}) in detected character set'.
                format_map(result)))
        self._encoding = result['encoding']

    def _detect_format(self):
        sample = self._sample_str()
        if sample[:5] == '<?xml':
            self._format = 'xml'
        else:
            sample = sample.lstrip()
            if sample[:1] in ('[', '{'):
                self._format = 'json'
            elif sample[:5] == '<?xml':
                warnings.warn(ValidationWarning('whitespace before xml header'))
                self._format = 'xml'
            elif sample[:1] == '<':
                warnings.warn(ValidationWarning('missing xml header'))
                self._format = 'xml'
            else:
                self._detect_yaml_or_csv()

    def _detect_yaml_or_csv(self):
        # Strip potentially partial last line off
        sample = self._sample_str().splitlines(keepends=True)[:-1]
        quote_delims = re.compile('["\']')
        field_delims = re.compile('[,; \\t]')
        csv_score = yaml_score = 0
        for line in sample:
            if (
                line.startswith(('#', ' ', '-')) or
                line.endswith(':')
            ):
                # YAML comments, indented lines, "-" prefixed items and colon
                # suffixes are all atypical in CSV and strong indicators of
                # YAML
                yaml_score += 2
                continue
            has_field_delims = bool(set(line) & set(',; \\t'))
            quote_delims = max(
                line.count(delim) for delim in ('"', "'"))
            if has_field_delims and quote_delims and not (
                quote_delims % 2):
                # Both field and quote delimiters found in the line and quote
                # delimiters are paired. Also possible for YAML (hence
                # continue) but the presence of paired quotes is a strong
                # indicator of CSV
                csv_score += 2
            elif line.count(':') == 1:
                # No quoted, field-delimited strings, but line contains
                # a single colon - weaker indicator of YAML
                yaml_score += 1
            elif has_field_delims:
                # No quote delimiters, but field delimiters are present
                # with no colon in the line - weaker indicator of CSV
                csv_score += 1
        if yaml_score > csv_score:
            self._format = 'yaml'
        elif csv_score > 0:
            self._format = 'csv'
        else:
            self._format = 'unknown'

    def _detect_csv_dialect(self):
        if self._csv_delimiter == 'auto' or self._csv_quotechar == 'auto':
            # First line is possible header; only need a few Kb for
            # analysis
            sample = self._sample_str()
            sample = ''.join(sample.splitlines(keepends=True)[1:])[:8192]
            self._csv_dialect = csv.Sniffer().sniff(
                sample,
                delimiters=",; \t"
                           if self._csv_delimiter == 'auto' else
                           self._csv_delimiter)
        else:
            class dialect(csv.Dialect):
                delimiter = self._csv_delimiter
                quotechar = self._csv_quotechar or None
                escapechar = None
                doublequote = True
                lineterminator = '\r\n'
                quoting = csv.QUOTE_MINIMAL
            self._csv_dialect = dialect

    def _load_data(self):
        # The apparently pointless _sample_bytes call below isn't actually
        # pointless; it's required to set the _sample cache in case it's
        # queried by a later query of encoding, csv_dialect, etc.
        data = self._sample_bytes() + self._source.read()
        data = data.decode(
            self.encoding,
            errors='strict' if self._encoding_strict else 'replace')

        if self.format == 'json':
            self._data = json.loads(data, strict=self._json_strict)
        elif self.format == 'csv':
            # Exclude the first row of data from analysis in case it's a header
            data = data.splitlines(keepends=True)[1:]
            reader = csv.reader(data, self.csv_dialect)
            self._data = list(reader)
        elif self.format == 'yaml':
            if not yaml:
                raise ImportError('ruamel.yaml package is not installed')
            else:
                loader = (
                    yaml.SafeLoader if self._yaml_safe else yaml.UnsafeLoader)
                self._data = yaml.load(io.StringIO(data), Loader=loader)
        elif self.format == 'xml':
            raise NotImplementedError()
        elif self.format == 'unknown':
            raise ValueError('unable to guess data format')
        else:
            assert False
