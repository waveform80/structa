import warnings
from math import ceil
from datetime import datetime, timedelta
from functools import partial
from collections import Counter

from dateutil.relativedelta import relativedelta

from .chars import AnyChar, Digit, OctDigit, DecDigit, HexDigit
from .patterns import (
    try_conversion,
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


FIXED_DATETIME_FORMATS = {
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%a, %d %b %Y %H:%M:%S',
    '%a, %d %b %Y %H:%M:%S %Z',
}
VAR_DATETIME_FORMATS = {
    '%Y-%m-%dT%H:%M:%S.%f%z',
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%dT%H:%M%z',
    '%Y-%m-%d %H:%M:%S.%f%z',
    '%Y-%m-%d %H:%M:%S%z',
    '%Y-%m-%d %H:%M%z',
}


class ValidationWarning(Warning):
    """
    Warning raised when a value fails to validate against the computed pattern
    or schema.
    """


class Analyzer:
    def __init__(self, *, bad_threshold=2, empty_threshold=98,
                 choice_threshold=20, key_threshold=20, max_numeric_len=50,
                 strip_whitespace=False, min_timestamp=None, max_timestamp=None):
        self.bad_threshold = bad_threshold / 100
        self.empty_threshold = empty_threshold / 100
        self.choice_threshold = choice_threshold
        self.key_threshold = key_threshold
        self.max_numeric_len = max_numeric_len
        self.strip_whitespace = strip_whitespace
        now = datetime.now()
        if min_timestamp is None:
            min_timestamp = now - relativedelta(years=20)
        if max_timestamp is None:
            max_timestamp = now + relativedelta(years=10)
        self.min_timestamp = min_timestamp.timestamp()
        self.max_timestamp = max_timestamp.timestamp()

    def _likely_datetime(self, value):
        """
        Given a :class:`float` *value*, returns :data:`True` if it represents a
        floating point value that, if treated as a UNIX timestamp (a seconds
        offset from midnight, 1st January 1970), would fall between
        :attr:`min_timestamp` and :attr:`max_timestamp`.
        """
        return self.min_timestamp <= float(value) <= self.max_timestamp

    def _float_or_datetime(self, sample, unique=False, bad_threshold=0):
        sample = try_conversion(sample, float, bad_threshold)
        if all(self._likely_datetime(value) for value in sample):
            return DateTime(sample, float, unique)
        else:
            return Float(sample, 'f', unique)  # XXX Refine pattern ('e' / 'f')

    def _match_fixed_len_str(self, items, unique=False, bad_threshold=0):
        """
        Given a :class:`set` of strings in *items*, discover any common
        fixed-length patterns that cover the entire sample.
        """
        # We're dealing with (mostly) fixed length strings
        for pattern in FIXED_DATETIME_FORMATS | VAR_DATETIME_FORMATS:
            try:
                return DateTime.from_strings(items, pattern, unique=unique,
                                             bad_threshold=bad_threshold)
            except ValueError:
                pass
        pattern = []
        base = 0
        for chars in zip(*items): # transpose
            chars = set(chars)
            if len(chars) == 1:
                pattern.append(chars.pop())
            elif chars <= HexDigit.chars:
                pattern.append(Digit)
                if chars <= OctDigit.chars:
                    base = max(base, 8)
                elif chars <= DecDigit.chars:
                    base = max(base, 10)
                else:
                    base = max(base, 16)
            else:
                pattern.append(AnyChar)
        pattern = tuple(
            (
                HexDigit if base == 16 else
                DecDigit if base == 10 else
                OctDigit
            ) if char == Digit else char
            for char in pattern
        )
        return Str(items, pattern, unique=unique)

    def _match_str(self, items, unique=False):
        """
        Given a :class:`~collections.Counter` of strings in *items*, find any
        common fixed-length patterns or string-encoded ints, floats, and a
        variety of date-time formats in a majority of the entries (covering
        greater than *min_coverage* percent of them).
        """
        total = sum(items.values())
        if '' in items:
            if items[''] / total > self.empty_threshold:
                return Str(items.keys())
            del items['']
        bad_threshold = ceil(total * self.bad_threshold)
        if unique or bad_threshold == 0:
            sample = items.keys()
        else:
            min_coverage = total - bad_threshold
            coverage = 0
            sample = set()
            for item, count in items.most_common():
                sample.add(item)
                coverage += count
                if coverage >= min_coverage:
                    # We've excluded potentially bad values based on
                    # popularity
                    bad_threshold = 0
                    break
                elif count == 1:
                    # Too many unique values to determine which should be
                    # ignored by popularity; just use regular bad_threshold
                    sample = items.keys()
                    break

        stats = Stats(len(value) for value in sample)
        if stats.min == stats.max:
            return self._match_fixed_len_str(sample, unique=unique,
                                             bad_threshold=bad_threshold)
        elif stats.max < self.max_numeric_len:
            conversions = (
                partial(Bool.from_strings, bad_threshold=bad_threshold),
                partial(Int.from_strings, base=8, unique=unique,
                        bad_threshold=bad_threshold),
                partial(Int.from_strings, base=10, unique=unique,
                        bad_threshold=bad_threshold),
                partial(Int.from_strings, base=16, unique=unique,
                        bad_threshold=bad_threshold),
                partial(self._float_or_datetime, unique=unique,
                        bad_threshold=bad_threshold),
                # XXX Add is_base64 (and others?)
            )
            for conversion in conversions:
                try:
                    return conversion(sample)
                except ValueError:
                    pass
        for pattern in VAR_DATETIME_FORMATS:
            try:
                return DateTime.from_strings(sample, pattern, unique=unique,
                                             bad_threshold=bad_threshold)
            except ValueError:
                pass
        if all(value.startswith(('http://', 'https://')) for value in sample):
            # XXX Refine this to parse URLs
            return URL(unique=unique)
        else:
            return Str(sample, unique=unique)

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
                max_card = max(card.values())
                unique = max_card == 1
                if parent_card is None:
                    try:
                        # XXX What is this for?
                        parent_card = max_card
                    except ValueError:
                        parent_card = 0
                if len(card) < threshold:
                    return Choices(
                        Choice(key, optional=count < parent_card)
                        for key, count in card.items()
                    )
                elif all(isinstance(value, bool) for value in card):
                    return Bool(card)
                elif all(isinstance(value, int) for value in card):
                    return Int(card, unique=unique)
                elif all(isinstance(value, float) for value in card):
                    if all(self._likely_datetime(value) for value in card):
                        return DateTime(card, float, unique=unique)
                    else:
                        return Float(card, unique=unique)
                elif all(isinstance(value, datetime) for value in card):
                    return DateTime(card, unique=unique)
                elif all(isinstance(value, str) for value in card):
                    if self.strip_whitespace:
                        card = Counter({
                            s.strip(): count
                            for s, count in card.items()
                        })
                    return self._match_str(card, unique=unique)
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
                                "mandatory key {key_pattern.value} "
                                "missing".format(key_pattern=key_pattern)))
                    else:
                        for key, value in it.items():
                            if key_pattern.validate(key):
                                yield from self._extract(value, tail)
                            else:
                                warnings.warn(ValidationWarning(
                                    "failed to validate {key} against "
                                    "{key_pattern!r}".format(
                                        key=key, key_pattern=key_pattern)))
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
                it, path + (pattern,),
                threshold=self.key_threshold,
                card=pattern.stats.card)
            if isinstance(key_pattern, Choices):
                return pattern._replace(pattern={
                    choice: self._analyze(
                        it, path + (pattern, choice),
                        card=pattern.stats.card)
                    for choice in key_pattern
                })
            else:
                return pattern._replace(pattern={
                    key_pattern: self._analyze(
                        it, path + (pattern, key_pattern),
                        card=pattern.stats.card)
                })
        elif isinstance(pattern, List):
            item_pattern = self._analyze(
                it, path + (pattern,), card=pattern.stats.card)
            return pattern._replace(pattern=[item_pattern])
        else:
            return pattern

    def analyze(self, it):
        """
        Given some value *it* (typically an iterable or mapping), return a
        description of its structure.
        """
        return self._analyze(it, ())
