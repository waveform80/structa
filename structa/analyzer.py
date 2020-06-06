import warnings
from datetime import datetime, timedelta
from functools import partial
from collections import Counter

from .patterns import (
    Bool,
    Choice,
    Choices,
    DateTime,
    Dict,
    Empty,
    Float,
    Int,
    List,
    Stats,
    Str,
    URL,
    Value,
)


DEC_DIGITS = set('0123456789')
HEX_DIGITS = set('0123456789abcdefABCDEF')
DATETIME_FORMATS = {
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
}
MIN_TIMESTAMP = (datetime.now() - timedelta(days=20 * 365.25)).timestamp()
MAX_TIMESTAMP = (datetime.now() + timedelta(days=10 * 365.25)).timestamp()

def try_conv(conv, value):
    try:
        conv(value)
    except ValueError:
        return False
    else:
        return True

is_dec = partial(try_conv, partial(int, base=10))
is_hex = partial(try_conv, partial(int, base=16))
is_float = partial(try_conv, float)
def is_datetime(value, fmt):
    return try_conv(lambda v: datetime.strptime(v, fmt), value)
def likely_datetime(value):
    return is_float(value) and MIN_TIMESTAMP <= float(value) <= MAX_TIMESTAMP


class ValidationWarning(Warning):
    """
    Warning raised when a value fails to validate against the computed pattern
    or schema.
    """


class Analyzer:
    def __init__(self, *, min_coverage=95, choice_threshold=20,
                 key_threshold=20):
        self.min_coverage = min_coverage
        self.choice_threshold = choice_threshold
        self.key_threshold = key_threshold

    def _match_str(self, items):
        """
        Given a :class:`~collections.Counter` of strings in *items*, find any
        common fixed-length patterns or string-encoded ints, floats, and a
        variety of date-time formats in a majority of the entries (covering
        greater than *min_coverage* percent of them).
        """
        min_coverage = self.min_coverage / 100
        total = sum(items.values())
        coverage = 0
        cohort = set()
        for value, count in items.most_common():
            cohort.add(value)
            coverage += count
            if coverage / total >= min_coverage:
                break

        stats = Stats(len(value) for value in cohort)
        if stats.min == stats.max:
            # We're dealing with (mostly) fixed length strings
            for pattern in DATETIME_FORMATS:
                if all(is_datetime(value, pattern) for value in cohort):
                    return DateTime(cohort, pattern)
            pattern = ''
            for chars in zip(*cohort): # transpose
                chars = set(chars)
                if len(chars) == 1:
                    pattern += chars.pop()
                elif chars <= DEC_DIGITS:
                    pattern += 'd'
                elif chars <= HEX_DIGITS:
                    pattern += 'h'
                else:
                    pattern += 'c'
            return Str(cohort, pattern)
        elif all(len(value) < 50 and is_dec(value) for value in cohort):
            return Int(cohort, 10)
        elif all(len(value) < 50 and is_hex(value) for value in cohort):
            return Int(cohort, 16)
        elif all(len(value) < 50 and is_float(value) for value in cohort):
            if all(likely_datetime(float(value)) for value in cohort):
                return DateTime(cohort, float)
            else:
                return Float(cohort, float)
        elif all(value.startswith(('http://', 'https://')) for value in cohort):
            return URL()
        else:
            return Str(cohort)

    def _match(self, items, *, threshold=None, parent_card=None):
        """
        Find a pattern which matches all (or most) of *items*, an iterable of
        objects found at a particular layer of the hierarchy.
        """
        if threshold is None:
            threshold = self.choice_threshold
        items = list(items)
        if not items:
            return Empty()
        elif all(isinstance(item, list) for item in items):
            return List(len(item) for item in items)
        elif all(isinstance(item, dict) for item in items):
            return Dict(len(item) for item in items)
        else:
            try:
                card = Counter(items)
            except TypeError:
                return Value()
            else:
                if parent_card is None:
                    try:
                        parent_card = max(card.values())
                    except ValueError:
                        parent_card = 0
                if len(card) < threshold:
                    return Choices(
                        Choice(key, optional=count < parent_card)
                        for key, count in card.items()
                    )
                elif all(isinstance(value, int) for value in card):
                    return Int(card)
                elif all(isinstance(value, float) for value in card):
                    if all(likely_datetime(value) for value in card):
                        return DateTime(card, float)
                    else:
                        return Float(card)
                elif all(isinstance(value, datetime) for value in card):
                    return DateTime(card)
                elif all(isinstance(value, str) for value in card):
                    return self._match_str(card)
                else:
                    return Value()

    def _extract(self, it, path):
        """
        Extract all entries from *it* (a potentially nested iterable which is
        the top-level object passed to :func:`analyze`), at the level dictated
        by *path*, a sequence of pattern-matching objects.
        """
        if not path:
            yield it
        else:
            head, *tail = path
            if isinstance(head, Dict):
                if tail:
                    # values
                    key_pattern, *tail = tail
                    if isinstance(key_pattern, (List, Dict)):
                        assert False, "invalid key type"
                    elif isinstance(key_pattern, Choice):
                        if key_pattern.value in it:
                            yield from self._extract(
                                it[key_pattern.value], tail)
                        elif not key_pattern.optional:
                            warnings.warn(ValidationWarning(
                                "mandatory key %s missing" %
                                key_pattern.value))
                    else:
                        for key, value in it.items():
                            if key_pattern.validate(key):
                                yield from self._extract(value, tail)
                            else:
                                warnings.warn(ValidationWarning(
                                    "failed to validate %s against %r" %
                                    (key, key_pattern)))
                else:
                    # keys
                    yield from it
            elif isinstance(head, List):
                for item in it:
                    yield from self._extract(item, tail)
            else:
                assert head.validate(it)
                yield it

    def _analyze(self, it, path, *, threshold=None, card=1):
        """
        Recursively analyze the structure of *it* at the nodes described by
        *path*. The parent cardinality is tracked in *card* (for the purposes
        of determining optional choices).
        """
        pattern = self._match(self._extract(it, path),
                              threshold=threshold, parent_card=card)
        if isinstance(pattern, Dict):
            key_pattern = self._analyze(
                it, path + [pattern],
                threshold=self.key_threshold,
                card=pattern.stats.card)
            if isinstance(key_pattern, Choices):
                return pattern._replace(pattern={
                    choice: self._analyze(
                        it, path + [pattern, choice],
                        card=pattern.stats.card)
                    for choice in key_pattern
                })
            else:
                return pattern._replace(pattern={
                    key_pattern: self._analyze(
                        it, path + [pattern, key_pattern],
                        card=pattern.stats.card)
                })
        elif isinstance(pattern, List):
            item_pattern = self._analyze(
                it, path + [pattern], card=pattern.stats.card)
            return pattern._replace(pattern=[item_pattern])
        else:
            return pattern

    def analyze(self, it):
        """
        Given some value *it* (typically an iterable or mapping), return a
        description of its structure.
        """
        return self._analyze(it, [])
