import warnings
from math import ceil
from datetime import datetime, timedelta
from functools import partial
from fractions import Fraction
from collections import Counter, namedtuple
from operator import attrgetter
from itertools import groupby

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
    Tuple,
    TupleField,
    ScalarStats,
    Str,
    URL,
    Value,
    StrRepr,
)


BOOL_PATTERNS = (
    '0|1',
    'f|t',
    'n|y',
    'false|true',
    'no|yes',
    'off|on',
    '|x',
    '|y',
)
INT_PATTERNS = ('o', 'd', 'x')  # Order matters for these
FIXED_DATETIME_PATTERNS = {
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
VAR_DATETIME_PATTERNS = {
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
    def __init__(self, *, bad_threshold=Fraction(2, 100),
                 empty_threshold=Fraction(98, 100), choice_threshold=20,
                 field_threshold=20, max_numeric_len=30, strip_whitespace=False,
                 min_timestamp=None, max_timestamp=None):
        self.bad_threshold = bad_threshold
        self.empty_threshold = empty_threshold
        self.choice_threshold = choice_threshold
        self.field_threshold = field_threshold
        self.max_numeric_len = max_numeric_len
        self.strip_whitespace = strip_whitespace
        now = datetime.now()
        if min_timestamp is None:
            min_timestamp = now - relativedelta(years=20)
        if max_timestamp is None:
            max_timestamp = now + relativedelta(years=10)
        self.min_timestamp = min_timestamp.timestamp()
        self.max_timestamp = max_timestamp.timestamp()

    def analyze(self, it):
        """
        Given some value *it* (typically an iterable or mapping), return a
        description of its structure.
        """
        return self._analyze(it, ())

    def _analyze(self, it, path, *, threshold=None, card=1):
        """
        Recursively analyze the structure of *it* at the nodes described by
        *path*. The parent cardinality is tracked in *card* (for the purposes
        of determining optional choices).
        """
        pattern = self._match(self._extract(it, path),
                              threshold=threshold, parent_card=card)

        if isinstance(pattern, Dict):
            return self._analyze_dict(it, path, pattern)
        elif isinstance(pattern, Tuple):
            return self._analyze_tuple(it, path, pattern)
        elif isinstance(pattern, List):
            # Lists are expected to be homogeneous, therefore there's a single
            # item pattern
            item_pattern = self._analyze(
                it, path + (pattern,), card=pattern.lengths.card)
            return pattern._replace(pattern=[item_pattern])
        else:
            return pattern

    def _analyze_dict(self, it, path, pattern):
        fields = self._analyze(
            it, path + (pattern,),
            threshold=self.field_threshold,
            card=pattern.lengths.card)
        if isinstance(fields, Choices):
            # XXX: This relies on the assumption that the iteration order
            # of sets (or frozensets) is stable; for further discussion:
            # https://twitter.com/waveform80/status/1328034156450893825
            return pattern._replace(fields=fields, pattern=tuple(
                self._analyze(
                    it, path + (pattern, choice),
                    card=pattern.lengths.card)
                for choice in fields
            ))
        else:
            return pattern._replace(fields={fields}, pattern=(
                self._analyze(
                    it, path + (pattern, fields),
                    card=pattern.lengths.card),
            ))

    def _analyze_tuple(self, it, path, pattern):
        # Tuples are expected to be heterogeneous, so we attempt to treat
        # them as a tuple (possibly named) of item patterns
        fields = self._analyze(
            it, path + (pattern,),
            threshold=self.field_threshold,
            card=pattern.lengths.card)
        if isinstance(fields, Choices):
            if all(choice.value.name for choice in fields):
                # Only used namedtuples if absolutely every single tuple in the
                # extracted sample has names for every column; otherwise just
                # index by field number
                names = {
                    name: sorted(group, key=attrgetter('value.index'))
                    for name, group in groupby(
                        sorted(fields, key=attrgetter('value.name')),
                        key=attrgetter('value.name')
                    )
                }
                fields = tuple(
                    Choice(group[0].value.name,
                           any(field.optional for field in group))
                    for group in sorted(names.values(), key=lambda g: tuple(
                        field.value.index for field in g))
                )
            else:
                fields = tuple(
                    Choice(index, any(field.optional for field in group))
                    for index, group in groupby(
                        sorted(fields, key=attrgetter('value.index')),
                        key=attrgetter('value.index')
                    )
                )
            return pattern._replace(fields=fields, pattern=tuple(
                self._analyze(
                    it, path + (pattern, field),
                    card=pattern.lengths.card)
                for field in fields
            ))
        else:
            return pattern._replace(fields=(fields,), pattern=(
                self._analyze(
                    it, path + (pattern, fields),
                    card=pattern.lengths.card),
            ))

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
                yield from self._extract_dict(it, tail)
            elif isinstance(head, Tuple):
                yield from self._extract_tuple(it, tail)
            elif isinstance(head, List):
                for item in it:
                    yield from self._extract(item, tail)
            else:
                assert False

    def _extract_dict(self, it, path):
        """
        Subroutine of :meth:`_extract` for extracting either the key or value
        from the dicts in *it*.
        """
        if path:
            # values
            head, *tail = path
            if isinstance(head, (List, Dict)):
                assert False, "invalid key type"
            elif isinstance(head, Choice):
                try:
                    yield from self._extract(
                        it[head.value], tail)
                except KeyError:
                    assert head.optional, "mandatory key missing"
            elif isinstance(head, Tuple) and head.pattern is None:
                # Incomplete tuple pattern indicates we're extracting tuples
                # from the key(s) of the dict
                for key in it:
                    yield from self._extract(key, [head] + tail)
            else:
                for key, value in it.items():
                    if head.validate(key):
                        yield from self._extract(value, tail)
                    else:
                        warnings.warn(ValidationWarning(
                            "failed to validate {key} against {head!r}"
                            .format(key=key, head=head)))
        else:
            # keys
            yield from it

    def _extract_tuple(self, it, path):
        """
        Subroutine of :meth:`_extract` for extracting either the field
        descriptions tuples (index, name) or the values from the tuples in
        *it*.
        """
        if path:
            # values
            head, *tail = path
            if not isinstance(head, (Empty, Int, Str, Choice)):
                assert False, "invalid column index type"
            elif isinstance(head, Choice):
                if isinstance(head.value, int):
                    get_value = lambda: it[head.value]
                else:
                    get_value = lambda: getattr(it, head.value)
                try:
                    yield from self._extract(get_value(), tail)
                except (IndexError, AttributeError):
                    assert head.optional, "mandatory field missing"
            else:
                try:
                    field_it = zip(it._fields, it)
                except AttributeError:
                    field_it = enumerate(it)
                for field, value in field_it:
                    if head.validate(field):
                        yield from self._extract(value, tail)
                    else:
                        # XXX Can this ever get triggered?
                        warnings.warn(ValidationWarning(
                            "failed to validate field {field} against {head!r}"
                            .format(field=field, head=head)))
        else:
            # "fields" (tuple of index, name)
            try:
                yield from (
                    TupleField(index, name)
                    for index, name in enumerate(it._fields)
                )
            except AttributeError:
                yield from (TupleField(index) for index in range(len(it)))

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
        elif all(
                isinstance(item, tuple) and not isinstance(item, TupleField)
                for item in items
        ):
            return Tuple(items)
        elif all(isinstance(item, list) for item in items):
            # If this is a list of lists, all sub-lists are the same length and
            # non-empty, the outer list is longer than the sub-list length, and
            # the sub-list length is less than the field-threshold we are
            # probably dealing with a table-like input from a language that
            # doesn't support tuples (e.g. JS)
            if (
                    len(items) > len(items[0]) and
                    0 < len(items[0]) < threshold and
                    all(len(item) == len(items[0]) for item in items)
            ):
                return Tuple(items)
            else:
                return List(items)
        elif all(isinstance(item, dict) for item in items):
            return Dict(items)
        else:

            try:
                sample = Counter(items)
            except TypeError:
                return Value()
            else:
                max_card = max(sample.values())
                if len(sample) < threshold:
                    return Choices(
                        Choice(key, optional=count < parent_card)
                        for key, count in sample.items()
                    )
                elif all(isinstance(value, TupleField) for value in sample):
                    # If the number of tuple-fields exceeds the choice
                    # threshold, just treat the index (or name) as general data
                    if all(value.name for value in sample):
                        sample = Counter(value.name for value in sample)
                    else:
                        sample = Counter(value.index for value in sample)

                # The following ordering is important; note that bool's domain
                # is a subset of int's
                if all(isinstance(value, bool) for value in sample):
                    return Bool(sample)
                elif all(isinstance(value, int) for value in sample):
                    return self._match_possible_datetime(Int(sample))
                elif all(isinstance(value, (int, float)) for value in sample):
                    return self._match_possible_datetime(Float(sample))
                elif all(isinstance(value, datetime) for value in sample):
                    return DateTime(sample)
                elif all(isinstance(value, str) for value in sample):
                    if self.strip_whitespace:
                        stripped_sample = Counter()
                        for s, count in sample.items():
                            stripped_sample[s.strip()] += count
                        sample = stripped_sample
                    return self._match_str(sample)
                else:
                    return Value()

    def _match_str(self, items):
        """
        Given a :class:`~collections.Counter` of strings in *items*, find any
        common fixed-length patterns or string-encoded ints, floats, and a
        variety of date-time formats in a majority of the entries (no more
        than :attr:`bad_threshold` percent invalid conversions), provided the
        maximum string length is below :attr:`max_numeric_len`.
        """
        unique = max(items.values()) == 1
        total = sum(items.values())
        if '' in items:
            if items[''] / total > self.empty_threshold:
                return Str(items)
            del items['']
        bad_threshold = ceil(total * self.bad_threshold)
        if unique or bad_threshold == 0:
            sample = items
        else:
            min_coverage = total - bad_threshold
            coverage = 0
            sample = Counter()
            for item, count in items.most_common():
                sample[item] = count
                coverage += count
                if coverage >= min_coverage:
                    # We've excluded potentially bad values based on
                    # popularity
                    bad_threshold = 0
                    break
                elif count == 1:
                    # Too many unique values to determine which should be
                    # ignored by popularity; just use regular bad_threshold
                    sample = items
                    break

        lengths = ScalarStats.from_lengths(sample)
        if lengths.max <= self.max_numeric_len:
            result = self._match_numeric_str(sample, bad_threshold=bad_threshold)
            if result is not None:
                return self._match_possible_datetime(result)
        if lengths.min == lengths.max:
            return self._match_fixed_len_str(sample, bad_threshold=bad_threshold)
        # XXX Add is_base64 (and others?)
        if all(value.startswith(('http://', 'https://')) for value in sample):
            # XXX Refine this to parse URLs
            return URL(unique=unique)
        else:
            return Str(sample)

    def _match_fixed_len_str(self, items, *, bad_threshold=0):
        """
        Given a :class:`~collections.Counter` of strings all of the same length
        in *items*, discover any common fixed-length patterns that cover the
        entire sample.
        """
        # We're dealing with fixed length strings (we've already tested for
        # variable length date-times)
        for pattern in FIXED_DATETIME_PATTERNS:
            try:
                return DateTime.from_strings(items, pattern,
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
        return Str(items, pattern)

    def _match_numeric_str(self, items, *, bad_threshold=0):
        """
        Given a :class:`~collections.Counter` of strings in *items*, attempt a
        variety of numeric conversions on them to discover if they represent a
        numbers (or timestamps).
        """
        representations = (
            (partial(
                Bool.from_strings, bad_threshold=bad_threshold), BOOL_PATTERNS),
            (partial(
                Int.from_strings, bad_threshold=bad_threshold), INT_PATTERNS),
            (partial(
                Float.from_strings, bad_threshold=bad_threshold), ('f',)),
            (partial(
                DateTime.from_strings,
                bad_threshold=bad_threshold), VAR_DATETIME_PATTERNS),
        )
        for conversion, formats in representations:
            for fmt in formats:
                try:
                    return conversion(items, fmt)
                except ValueError:
                    pass
        return None

    def _match_possible_datetime(self, pattern):
        """
        Given an already matched numeric *pattern*, check whether the range
        of values are "likely" date-times based on whether they fall between
        :attr:`min_timestamp` and :attr:`max_timestamp`. If they are, return a
        numerically-wrapped :class:`DateTime` pattern instead. Otherwise,
        return the original *pattern*.
        """
        in_range = lambda n: self.min_timestamp <= n <= self.max_timestamp
        if (
                isinstance(pattern, (Int, Float)) and
                in_range(pattern.values.min) and
                in_range(pattern.values.max)):
            return DateTime.from_numbers(pattern)
        elif (
                isinstance(pattern, StrRepr) and (
                    (isinstance(pattern.inner, Int) and pattern.pattern == 'd') or
                    isinstance(pattern.inner, Float)
                ) and
                in_range(pattern.inner.values.min) and
                in_range(pattern.inner.values.max)):
            return DateTime.from_numbers(pattern)
        else:
            return pattern
