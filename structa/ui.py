import os
import io
import sys
import csv
import json
import argparse
import warnings
from datetime import datetime, timedelta
from fractions import Fraction

from chardet.universaldetector import UniversalDetector

from . import analyzer, patterns
from .duration import parse_duration_or_timestamp


def cli_main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file', nargs='?', type=argparse.FileType('rb'), default=sys.stdin,
        help="The data-file to analyze; if this is - or unspecified then "
        "stdin will be read for the data")
    parser.add_argument(
        '-f', '--format', choices=('auto', 'csv', 'json'), default='auto',
        help="The format of the data file; if this is unspecified, it will "
        "be guessed based on the first bytes of the file; valid choices are "
        "auto (the default), csv, or json")
    parser.add_argument(
        '-e', '--encoding', type=str, default='auto',
        help="The string encoding of the file, e.g. utf-8 (default: "
        '%(default)s). If "auto" then the file will be sampled to determine '
        "the encoding (see --sample-bytes)")
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
        '--csv-format', type=str, metavar='FIELD[QUOTE]', default='auto',
        help="The characters used to delimit fields and strings in a CSV "
        "file. Can be specified as a single character which will be "
        "used as the field delimiter, or two characters in which case the "
        "second will be used as the string quotation character. Can also be "
        '"auto" which indicates the delimiters should be detected. Bear in '
        "mind that some characters may require quoting for the shell, e.g. "
        "';\"'")
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
    parser.set_defaults(sample=b'', csv_dialect=None)
    config = parser.parse_args(args)
    config.field_threshold = (
        config.choice_threshold
        if config.field_threshold is None else
        config.field_threshold)

    warnings.simplefilter('ignore', category=analyzer.ValidationWarning)

    a = Analyzer.from_config(config)
    data = load_data(config)
    print(a.analyze(data))


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
            max_timestamp=config.max_timestamp)


def detect_encoding(config):
    # XXX Split this into a separate AutoEncodedFile class? Could probably
    # make the sampling a bit nicer (e.g. hide it behind a "seekable" file
    # interface)
    if config.encoding == 'auto':
        detector = UniversalDetector()
        while (
            config.encoding == 'auto' and
            len(config.sample) < config.sample_bytes
        ):
            buf = config.file.read(4096)
            config.sample += buf
            detector.feed(buf)
            if detector.done:
                break
        result = detector.close()
        if result['confidence'] < 0.9:
            warnings.warn(ValidationWarning(
                'Low confidence ({confidence}) in detected character set'.
                format_map(result)))
        config.encoding = result['encoding']
        print('Detected charset {encoding} (confidence: {confidence})'.
              format_map(result), file=sys.stderr)


def detect_format(config):
    if config.format == 'auto':
        if len(config.sample) < config.sample_bytes:
            config.sample += config.file.read(
                config.sample_bytes - len(config.sample))
        sample = config.sample.decode(config.encoding, errors='replace')
        if config.sample[:5] == '<?xml':
            config.format = 'xml'
        else:
            sample = sample[:1024].lstrip()
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
                config.format = 'csv'
                if config.csv_format == 'auto':
                    # First line is possible header, last is possibly partial
                    sample = sample[1:-1]
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
        print('Detected format {format}'.format(format=config.format.upper()),
              file=sys.stderr)
        # XXX Output CSV detected dialect?


def load_data(config):
    detect_encoding(config)
    detect_format(config)
    data = config.sample + config.file.read()
    data = data.decode(config.encoding, errors='replace')

    if config.format == 'json':
        return json.loads(data)
    elif config.format == 'csv':
        # Exclude the first row of data from analysis in case it's a header
        reader = csv.reader(data.splitlines(keepends=True)[1:],
                            config.csv_dialect)
        return list(reader)
    elif config.format == 'xml':
        raise NotImplementedError()


def main(args=None):
    try:
        cli_main(args)
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
