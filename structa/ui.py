import io
import sys
import json
import argparse
import warnings
from .analyzer import Analyzer, ValidationWarning


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file', nargs='?', type=argparse.FileType('r', encoding='utf-8'),
        default=sys.stdin,
        help="The JSON file to analyze; if this is - or unspecified then "
        "stdin will be read for the data")
    parser.add_argument(
        '-C', '--choice-threshold', type=int, metavar='NUM', default=20,
        help="If the number of distinct keys in a map is less than this "
        "then they will be considered distinct choices instead of being "
        "lumped under a generic type like <str> (default: %(default)s)")
    parser.add_argument(
        '-M', '--min-coverage', type=int, metavar='NUM', default=95,
        help="The percentage of string values which must match the guessed "
        "pattern; this is to permit things like NULL values in a list of "
        "date-times from preventing the entry as being date-times (default: "
        "%(default)s)")
    config = parser.parse_args(args)
    warnings.simplefilter('ignore', category=ValidationWarning)

    analyzer = Analyzer(
        choice_threshold=config.choice_threshold,
        min_coverage=config.min_coverage)
    data = json.load(config.file)
    print(analyzer.analyze(data))


if __name__ == '__main__':
    main()
