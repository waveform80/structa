import os
import io
import sys
import json
import argparse
import warnings
from datetime import datetime, timedelta
from fractions import Fraction

from .analyzer import Analyzer, ValidationWarning
from .duration import parse_duration_or_timestamp


def cli_main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file', nargs='?', type=argparse.FileType('r', encoding='utf-8'),
        default=sys.stdin,
        help="The JSON file to analyze; if this is - or unspecified then "
        "stdin will be read for the data")
    parser.add_argument(
        '-C', '--choice-threshold', type=int, metavar='INT', default=20,
        help="If the number of distinct values in a field is less than this "
        "then they will be considered distinct choices instead of being "
        "lumped under a generic type like <str> (default: %(default)s)")
    parser.add_argument(
        '-K', '--key-threshold', type=int, metavar='INT', default=None,
        help="If the number of distinct keys in a map is less than this "
        "then they will be considered distinct choices instead of being "
        "lumped under a generic type like <str> (defaults to the value of "
        "--choice-threshold)")
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
    config = parser.parse_args(args)
    config.key_threshold = (
        config.choice_threshold
        if config.key_threshold is None else
        config.key_threshold)

    warnings.simplefilter('ignore', category=ValidationWarning)

    data = json.load(config.file)
    del config.file
    analyzer = Analyzer(**config.__dict__)
    print(analyzer.analyze(data))


def main(args=None):
    try:
        cli_main(args)
    except Exception as e:
        if int(os.environ.get('DEBUG', '0')):
            try:
                import pudb as pdb
            except ImportError:
                import pdb
            pdb.post_mortem()
        else:
            print(str(e))
            return 1
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


if __name__ == '__main__':
    main()
