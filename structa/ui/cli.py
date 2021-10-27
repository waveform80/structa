# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import argparse
import warnings
from datetime import datetime
from fractions import Fraction

from blessings import Terminal
from tqdm import tqdm
from pkg_resources import require

from ..analyzer import Analyzer
from ..errors import ValidationWarning
from ..conversions import parse_duration_or_timestamp
from ..types import sources_list, SourcesList
from ..source import Source
from ..xml import xml, get_transform


def main(args=None):
    warnings.simplefilter('ignore', category=ValidationWarning)
    try:
        config = get_config(args)
        structure = get_structure(config)
        print_structure(config, structure)
    except KeyboardInterrupt as e:
        print("Interrupted", file=sys.stderr)
        return 2
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


RANGE_CONFIGS = {
    'hidden':    0,
    'limits':    1,
    'median':    2,
    'quartiles': 3,
    'graph':     4,
}


def get_config(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--version', action='version', version=require('structa')[0].version)
    parser.add_argument(
        'file', nargs='*', type=file, default=[sys.stdin.buffer],
        help="The data-file(s) to analyze; if this is - or unspecified then "
        "stdin will be read for the data; if multiple files are specified "
        "all will be read and analyzed as an array of similar structures")
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
        '-F', '--field-threshold', type=int, metavar='INT', default=20,
        help="If the number of distinct keys in a map, or columns in a tuple "
        "is less than this then they will be considered distinct fields "
        "instead of being lumped under a generic type like <str> (default: "
        "%(default)s)")
    parser.add_argument(
        '-M', '--merge-threshold', type=num, metavar='NUM', default='50%',
        help="The proportion of mapping fields which must match other "
        "mappings for them to be considered potential merge candidates "
        "(default: %(default)s)")
    parser.add_argument(
        '-B', '--bad-threshold', type=num, metavar='NUM', default='1%',
        help="The proportion of string values which are allowed to mismatch "
        "a pattern without preventing the pattern from being reported; the "
        'proportion of "bad" data permitted in a field (default: %(default)s)')
    parser.add_argument(
        '-E', '--empty-threshold', type=num, metavar='NUM', default='99%',
        help="The proportion of string values permitted to be empty without "
        "preventing the pattern from being reported; the proportion of "
        '"empty" data permitted in a field (default: %(default)s)')
    parser.add_argument(
        '--str-limit', type=num, metavar='NUM', default=20,
        help="The length beyond which only the lengths of strs will be "
        "reported; below this the actual value of the string will be "
        "displayed (default: %(default)s)")
    parser.add_argument(
        '--hide-count', action='store_false', dest='show_count',
        default=False)
    parser.add_argument(
        '--show-count', action='store_true',
        help="If set, show the count of items in containers, the count of "
        "unique scalar values, and the count of all sample values (if "
        "--show-samples is set). If disabled, counts will be hidden")
    parser.add_argument(
        '--hide-lengths', action='store_false', dest='show_lengths',
        default=False)
    parser.add_argument(
        '--show-lengths', action='store_true',
        help="If set, display the range of lengths of string fields in the "
        "same format as specified by --show-range")
    parser.add_argument(
        '--hide-pattern', action='store_false', dest='show_pattern',
        default=True)
    parser.add_argument(
        '--show-pattern', action='store_true',
        help="If set, show the pattern determined for fixed length string "
        "fields. If disabled, pattern information will be hidden")
    parser.add_argument(
        '--hide-range', action='store_const', dest='show_range',
        const='hidden', default='limits')
    parser.add_argument(
        '--show-range', action='store', choices=RANGE_CONFIGS.keys(),
        help="Show the range of numeric (and temporal) fields in a variety of "
        "forms. The default is 'limits' which simply displays the minimum and "
        "maximum; 'median' includes the median between these; 'quartiles' "
        "shows all three quartiles between the minimum and maximum; 'graph' "
        "displays a crude chart showing the positions of the quartiles "
        "relative to the limits. Use --hide-range to hide all range info")
    parser.add_argument(
        '--hide-samples', action='store_false', dest='show_samples',
        default=False)
    parser.add_argument(
        '--show-samples', action='store_true',
        help="If set, show samples of non-unique scalar values including the "
        "most and least common values. If disabled, samples will be hidden")
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
    parser.add_argument(
        '--yaml-safe', action='store_true', default=True)
    parser.add_argument(
        '--no-yaml-safe', action='store_false', dest='yaml_safe',
        help='Controls whether the "safe" or "unsafe" YAML loader is used '
        'to parse YAML files. The default is the "safe" parser. Only use '
        "--no-yaml-safe if you trust the source of your data")
    parser.add_argument(
        '--json-strict', action='store_true', default=True)
    parser.add_argument(
        '--no-json-strict', action='store_false', dest='json_strict',
        help="Controls whether the JSON decoder permits control characters "
        "within strings, which isn't technically valid JSON. The default is "
        "to be strict and disallow such characters")

    parser.set_defaults(sample=b'', csv_dialect=None)
    return parser.parse_args(args)


def get_structure(config):
    bar_format='{desc} {percentage:4.1f}%  {elapsed} [{bar}] {remaining}'
    with tqdm(config.file, leave=False, bar_format=bar_format, maxinterval=1) as progress:
        data = sources_list()
        for file in progress:
            progress.set_description(
                'Reading file {file.name}'.format(file=file))
            source = MySource.from_config(config, file)
            if config.encoding == 'auto':
                progress.set_description(
                    'Guessed encoding {source.encoding}'.format(source=source))
            if config.format == 'auto':
                progress.set_description(
                    'Guessed format {source.format}'.format(source=source))
            progress.set_description('Parsing data')
            data.append(source.data)
    with tqdm(leave=False, bar_format=bar_format, smoothing=0, maxinterval=1) as progress:
        analyzer = MyAnalyzer.from_config(config, progress)
        progress.set_description('Measuring data')
        analyzer.measure(data)
        progress.set_description('Analyzing data')
        struct = analyzer.analyze(data)
        n = 0
        while True:
            n += 1
            progress.set_description(
                'Merging common structures (pass {})'.format(n))
            result = analyzer.merge(struct)
            if result.size == struct.size:
                break
            else:
                struct = result
    assert isinstance(struct, SourcesList)
    return struct.content[0]


def print_structure(config, structure):
    term = Terminal()
    styles = {
        'normal-style':    term.normal,
        'unique-style':    term.underline,
        'type-style':      term.cyan,
        'fill-style':      term.green,
        'suffix-style':    term.green,
        'pattern-style':   term.yellow,
        'literal-style':   term.normal,
        'required-suffix': '',
        'optional-suffix': term.red('?'),
        'ellipsis':        term.green('..'),
        'truncation':      term.green('$'),
    }
    params = {
        'show-count':      str(int(config.show_count)),
        'show-pattern':    str(int(config.show_pattern)),
        'show-samples':    str(int(config.show_samples)),
        'show-lengths':    str(int(config.show_lengths)),
        'show-range':      str(RANGE_CONFIGS[config.show_range]),
        'str-limit':       str(int(config.str_limit)),
    }
    transform = get_transform('cli.xsl')
    # XML 1.0 doesn't permit controls characters (other than whitespace) so
    # we'll use some chars from the private-use region (E000-) for the XSLT
    # params, then replace them after the transform in the vague hope no-one
    # else is going to use them in data that could be included in stats :). XML
    # 1.1 fixes this ... but nothing supports it.
    xsl_chars = {style: chr(0xE000 + i) for i, style in enumerate(styles)}
    output = str(transform(xml(structure), **{
        style: transform.strparam(char)
        for style, char in xsl_chars.items()
    }, **params))
    output = output.translate(str.maketrans({
        xsl_chars[style]: styles[style]
        for style in styles
    }))
    print(output)


class MyAnalyzer(Analyzer):
    @classmethod
    def from_config(cls, config, progress):
        return cls(
            bad_threshold=config.bad_threshold,
            empty_threshold=config.empty_threshold,
            field_threshold=config.field_threshold,
            merge_threshold=config.merge_threshold,
            max_numeric_len=config.max_numeric_len,
            strip_whitespace=config.strip_whitespace,
            min_timestamp=config.min_timestamp,
            max_timestamp=config.max_timestamp,
            progress=progress)


class MySource(Source):
    @classmethod
    def from_config(cls, config, file):
        return cls(
            source=file,
            encoding=config.encoding,
            encoding_strict=config.encoding_strict,
            format=config.format,
            csv_delimiter='auto' if config.csv_format == 'auto' else
                          config.csv_format[:1],
            csv_quotechar='auto' if config.csv_format == 'auto' else
                          config.csv_format[1:],
            yaml_safe=config.yaml_safe,
            json_strict=config.json_strict,
            sample_limit=config.sample_bytes)


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

def file(s):
    if s == '-':
        return sys.stdin.buffer
    else:
        return open(s, 'rb')
