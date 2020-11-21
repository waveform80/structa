import os
import io
import re
import sys
import csv
import json
import argparse
import warnings
from datetime import datetime, timedelta
from fractions import Fraction
from threading import Thread
from queue import Queue
from time import sleep

import humanize
from blessings import Terminal
from chardet.universaldetector import UniversalDetector
try:
    from ruamel import yaml
except ImportError:
    yaml = None

from . import analyzer, patterns
from .duration import parse_duration_or_timestamp


def main(args=None):
    warnings.simplefilter('ignore', category=analyzer.ValidationWarning)
    try:
        config = get_config(args)
        with Progress() as progress:
            a = Analyzer.from_config(config)
            d = load_data(config, progress)
            q = Queue()
            thread = Thread(
                target=lambda a, d, q: q.put(a.analyze(d)),
                args=(a, d, q),
                daemon=True
            )
            thread.start()
            if a.track_progress:
                progress.message('Measuring size')
            analyzing = False
            while True:
                if a.progress is not None:
                    if not analyzing:
                        analyzing = True
                        progress.message('Analyzing structure')
                    progress.position = a.progress
                thread.join(0.25)
                if not thread.is_alive():
                    break
        print(q.get(timeout=1, block=True))
    except Exception as e:
        debug = int(os.environ.get('DEBUG', '0'))
        if not debug:
            print(str(e), file=sys.stderr)
            return 1
        elif debug == 1:
            raise
        else:
            import pdb
            pdb.post_mortem()
    else:
        return 0


def get_config(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file', nargs='?', type=argparse.FileType('rb'), default=sys.stdin,
        help="The data-file to analyze; if this is - or unspecified then "
        "stdin will be read for the data")
    parser.add_argument(
        '-f', '--format', choices=('auto', 'csv', 'json', 'yaml'), default='auto',
        help="The format of the data file; if this is unspecified, it will "
        "be guessed based on the first bytes of the file; valid choices are "
        "auto (the default), csv, or json")
    parser.add_argument(
        '-e', '--encoding', type=str, default='auto',
        help="The string encoding of the file, e.g. utf-8 (default: "
        '%(default)s). If "auto" then the file will be sampled to determine '
        "the encoding (see --sample-bytes)")
    parser.add_argument(
        '--encoding-strict', action='store_true', default=True)
    parser.add_argument(
        '--no-encoding-strict', action='store_false', dest='encoding_strict',
        help="Controls whether character encoding is strictly enforced and "
        "will result in an error if invalid characters are found during "
        "analysis. If disabled, a replacement character will be inserted "
        "for invalid sequences. The default is strict decoding")
    parser.add_argument(
        '-C', '--choice-threshold', type=int, metavar='INT', default=20,
        help="If the number of distinct values in a field is less than this "
        "then they will be considered distinct choices instead of being "
        "lumped under a generic type like <str> (default: %(default)s)")
    parser.add_argument(
        '-F', '--field-threshold', type=int, metavar='INT', default=None,
        help="If the number of distinct keys in a map, or columns in a tuple "
        "is less than this then they will be considered distinct fields "
        "instead of being lumped under a generic type like <str> (defaults "
        "to the value of --choice-threshold)")
    parser.add_argument(
        '-B', '--bad-threshold', type=num, metavar='NUM', default='2%',
        help="The proportion of string values which are allowed to mismatch "
        "a pattern without preventing the pattern from being reported; the "
        'proportion of "bad" data permitted in a field (default: %(default)s)')
    parser.add_argument(
        '-E', '--empty-threshold', type=num, metavar='NUM', default='98%',
        help="The proportion of string values permitted to be empty without "
        "preventing the pattern from being reported; the proportion of "
        '"empty" data permitted in a field (default: %(default)s)')
    parser.add_argument(
        '--min-timestamp', type=min_timestamp, metavar='WHEN',
        default='20 years',
        help="The minimum timestamp to use when guessing whether floating "
        "point fields represent UNIX timestamps (default: %(default)s). Can "
        "be specified as an absolute timestamp (in ISO-8601 format) or a "
        "duration to be subtracted from the current timestamp")
    parser.add_argument(
        '--max-timestamp', type=max_timestamp, metavar='WHEN',
        default='10 years',
        help="The maximum timestamp to use when guessing whether floating "
        "point fields represent UNIX timestamps (default: %(default)s). Can "
        "be specified as an absolute timestamp (in ISO-8601 format) or a "
        "duration to be added to the current timestamp")
    parser.add_argument(
        '--max-numeric-len', type=int, metavar='LEN', default=30,
        help="The maximum number of characters that a number, integer or "
        "floating-point, may use in its representation within the file. "
        "Defaults to %(default)s")
    parser.add_argument(
        '--sample-bytes', type=size, metavar='SIZE', default='1m',
        help="The number of bytes to sample from the file for the purposes of "
        "encoding and format detection. Defaults to %(default)s. Typical "
        "suffixes of k, m, g, etc. may be specified")
    parser.add_argument(
        '--strip-whitespace', action='store_true', default=True)
    parser.add_argument(
        '--no-strip-whitespace', action='store_false', dest='strip_whitespace',
        help="Controls whether leading and trailing found in strings in the "
        "will be left alone and thus included or excluded in any data-type "
        "analysis. The default is to strip whitespace")
    parser.add_argument(
        '--csv-format', type=str, metavar='FIELD[QUOTE]', default='auto',
        help="The characters used to delimit fields and strings in a CSV "
        "file. Can be specified as a single character which will be "
        "used as the field delimiter, or two characters in which case the "
        "second will be used as the string quotation character. Can also be "
        '"auto" which indicates the delimiters should be detected. Bear in '
        "mind that some characters may require quoting for the shell, e.g. "
        "';\"'")
    if yaml:
        parser.add_argument(
            '--yaml-safe', action='store_true', default=True)
        parser.add_argument(
            '--no-yaml-safe', action='store_false', dest='yaml_safe',
            help='Controls whether the "safe" or "unsafe" YAML loader is used '
            'to parse YAML files. The default is the "safe" parser. Only use '
            "--no-yaml-safe if you trust the source of your data")
    parser.set_defaults(sample=b'', csv_dialect=None)

    config = parser.parse_args(args)
    config.field_threshold = (
        config.choice_threshold
        if config.field_threshold is None else
        config.field_threshold)
    return config


class Analyzer(analyzer.Analyzer):
    @classmethod
    def from_config(cls, config):
        return cls(
            bad_threshold=config.bad_threshold,
            empty_threshold=config.empty_threshold,
            choice_threshold=config.choice_threshold,
            field_threshold=config.field_threshold,
            max_numeric_len=config.max_numeric_len,
            strip_whitespace=config.strip_whitespace,
            min_timestamp=config.min_timestamp,
            max_timestamp=config.max_timestamp,
            track_progress=True)


class Progress:
    def __init__(self, stream=sys.__stderr__, show_bar=True, show_percent=True,
                 show_eta=True, show_spinner=False):
        self.term = Terminal(stream=stream)
        self._show_bar = show_bar and self.term.is_a_tty
        self._show_percent = show_percent
        self._show_eta = show_eta
        self._show_spinner = show_spinner and self.term.is_a_tty
        self._started = None
        self._position = 0.0
        self._last_spinner = '-'

    def hide(self):
        if self.term.is_a_tty:
            self.term.stream.write(self.term.clear_bol + self.term.move_x(0))

    def show(self):
        if self.term.is_a_tty:
            eta = pct = bar = spin = ''
            if self._show_eta and self._started is not None and self._position > 0.1:
                eta = ' ETA {eta} '.format(
                    eta=humanize.naturaldelta(
                        (1 - self._position) * (datetime.now() - self._started)
                        / self._position))
            if self._show_percent:
                pct = ' {p:4.1f}% '.format(p=self._position * 100)
            if self._show_spinner:
                self._last_spinner = {
                    '|': '/',
                    '/': '-',
                    '-': '\\',
                    '\\': '|',
                }[self._last_spinner]
                spin = ' ' + self._last_spinner
            if self._show_bar:
                size = self.term.width - len(pct) - len(eta) - len(spin) - 3
                bar = '[{bar:.<{size}}]'.format(
                    size=size, bar='#' * int(size * self._position))
            self.term.stream.write(self.term.move_x(0))
            self.term.stream.write(self.term.black_on_green)
            self.term.stream.write(pct)
            self.term.stream.write(eta)
            self.term.stream.write(self.term.normal)
            self.term.stream.write(bar)
            self.term.stream.write(spin)
            self.term.stream.flush()

    def message(self, msg):
        """
        Output the message *s* to the output stream.
        """
        self.hide()
        if self.term.stream:
            self.term.stream.write(msg)
            self.term.stream.write('\n')
            if not self.term.is_a_tty:
                self.term.stream.flush()
        self.show()

    @property
    def position(self):
        """
        The progress of the activity; a floating-point value between 0.0
        (just begun) and 1.0 (finished). Set this property to update the
        progress bar.
        """
        return self._position

    @position.setter
    def position(self, value):
        if self._started is None:
            self._started = datetime.now()
        value = min(1.0, max(0.0, value))
        self._position = float(value)
        self.show()

    def __enter__(self):
        self._position = 0.0
        self._started = None
        return self

    def __exit__(self, *exc):
        self.hide()
        if self.term.stream:
            self.term.stream.flush()


def detect_encoding(config):
    # XXX Split this into a separate AutoEncodedFile class? Could probably
    # make the sampling a bit nicer (e.g. hide it behind a "seekable" file
    # interface)
    if config.encoding == 'auto':
        detector = UniversalDetector()
        while len(config.sample) < config.sample_bytes and not detector.done:
            buf = config.file.read(4096)
            if not buf:
                break
            config.sample += buf
            detector.feed(buf)
        result = detector.close()
        if result['confidence'] < 0.9:
            warnings.warn(analyzer.ValidationWarning(
                'Low confidence ({confidence}) in detected character set'.
                format_map(result)))
        config.encoding = result['encoding']


def detect_format(config):
    if config.format == 'auto':
        if len(config.sample) < config.sample_bytes:
            config.sample += config.file.read(
                config.sample_bytes - len(config.sample))
        sample = config.sample.decode(config.encoding, errors='replace')
        if config.sample[:5] == '<?xml':
            config.format = 'xml'
        else:
            sample = sample.lstrip()
            if sample[:1] in ('[', '{'):
                config.format = 'json'
            elif sample[:5] == '<?xml':
                warnings.warn(analyzer.ValidationWarning(
                    'whitespace before xml header'))
                config.format = 'xml'
            elif sample[:1] == '<':
                warnings.warn(analyzer.ValidationWarning(
                    'missing xml header'))
                config.format = 'xml'
            else:
                # Strip potentially partial last line off
                sample = sample.splitlines(keepends=True)[:-1]
                quote_delims = re.compile('["\']')
                field_delims = re.compile('[,; \\t]')
                csv_score = yaml_score = 0
                for line in sample:
                    if (
                        line.startswith(('#', ' ', '-')) or
                        line.endswith(':')
                    ):
                        # YAML comments, indented lines, "-" prefixed items
                        # and colon suffixes are all atypical in CSV and
                        # strong indicators of YAML
                        yaml_score += 2
                        continue
                    has_field_delims = bool(set(line) & set(',; \\t'))
                    quote_delims = max(
                        line.count(delim) for delim in ('"', "'"))
                    if has_field_delims and quote_delims and not (
                        quote_delims % 2):
                        # Both field and quote delimiters found in the line and
                        # quote delimiters are paired. Also possible for YAML
                        # (hence elif) but the presence of paired quotes is a
                        # strong indicator of CSV
                        csv_score += 2
                    elif ':' in line:
                        # No quoted, field-delimited strings, but line contains
                        # a colon - weaker indicator of YAML
                        yaml_score += 1
                    elif has_field_delims:
                        # No quote delimiters, but field delimiters are present
                        # with no colon in the line - weaker indicator of CSV
                        csv_score += 1
                if yaml_score > csv_score:
                    config.format = 'yaml'
                elif csv_score > 0:
                    config.format = 'csv'
                    if config.csv_format == 'auto':
                        # First line is possible header; only need a few Kb for
                        # analysis
                        sample = ''.join(sample[1:])[:8192]
                        config.csv_dialect = csv.Sniffer().sniff(
                            sample, delimiters=",; \t")
                    else:
                        class dialect(csv.Dialect):
                            delimiter = config.csv_format[:1]
                            quotechar = (
                                None if len(config.csv_format) == 1 else
                                config.csv_format[1:])
                            escapechar = None
                            doublequote = True
                            lineterminator = '\r\n'
                            quoting = csv.QUOTE_MINIMAL
                        config.csv_dialect = dialect
                else:
                    raise ValueError('unable to guess the file format')
        # XXX Output CSV detected dialect?


def load_data(config, progress):
    detect_encoding(config)
    progress.message('Guessed encoding {config.encoding}'.format(config=config))
    detect_format(config)
    progress.message('Guessed format {config.format}'.format(config=config))
    progress.message('Reading file {config.file.name}'.format(config=config))
    data = config.sample + config.file.read()
    progress.message('Decoding file')
    data = data.decode(
        config.encoding,
        errors='strict' if config.encoding_strict else 'replace')

    progress.message('Parsing data')
    if config.format == 'json':
        return json.loads(data)
    elif config.format == 'csv':
        # Exclude the first row of data from analysis in case it's a header
        reader = csv.reader(data.splitlines(keepends=True)[1:],
                            config.csv_dialect)
        return list(reader)
    elif config.format == 'yaml':
        if not yaml:
            raise ImportError('ruamel.yaml package is not installed')
        else:
            loader = yaml.SafeLoader if config.yaml_safe else yaml.UnsafeLoader
            return yaml.load(io.StringIO(data), Loader=loader)
    elif config.format == 'xml':
        raise NotImplementedError()


_start = datetime.now()

def min_timestamp(s, now=_start):
    t = parse_duration_or_timestamp(s)
    if isinstance(t, datetime):
        return t
    else:
        return now - t

def max_timestamp(s, now=_start):
    t = parse_duration_or_timestamp(s)
    if isinstance(t, datetime):
        return t
    else:
        return now + t

def num(s):
    if s.endswith('%'):
        return Fraction(num(s[:-1]), 100)
    elif '/' in s:
        return Fraction(s)
    elif '.' in s or 'e' in s:
        return float(s)
    else:
        return int(s)

def size(s):
    s = s.lower().strip()
    suffixes = ('', 'k', 'm', 'g', 't', 'e')
    if not s[-1:].isdigit():
        return int(s[:-1]) * (2 ** 10) ** suffixes.index(s[-1:])
    else:
        return int(s)
