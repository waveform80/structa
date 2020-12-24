import warnings
from math import ceil
from datetime import datetime, timedelta
from fractions import Fraction
from collections import Counter, namedtuple
from itertools import groupby

from dateutil.relativedelta import relativedelta

from .conversions import try_conversion
from .chars import (
    CharClass,
    any_char,
    oct_digit,
    dec_digit,
    hex_digit,
    ident_first,
    ident_char,
)
from .types import (
    Stats,
    Container,
    Scalar,
    Bool,
    Field,
    Fields,
    DateTime,
    Dict,
    DictField,
    Float,
    Int,
    List,
    Tuple,
    TupleField,
    Str,
    URL,
    Empty,
    Value,
    StrRepr,
    SourcesList,
    sources_list,
)


BOOL_PATTERNS = (
    '0|1',
    'f|t',
    'n|y',
    'false|true',
    'no|yes',
    'off|on',
    '|x',
)
INT_PATTERNS = ('o', 'd', 'x')  # Order matters for these
FIXED_DATETIME_PATTERNS = {
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%a, %d %b %Y %H:%M:%S',
    '%a, %d %b %Y %H:%M:%S %Z',
}
VAR_DATETIME_PATTERNS = {
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%S.%f%z',
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%dT%H:%M%z',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S.%f%z',
    '%Y-%m-%d %H:%M:%S%z',
    '%Y-%m-%d %H:%M%z',
}


DIGIT_BASES = {
    16: hex_digit,
    10: dec_digit,
    8:  oct_digit,
}
DIGITS = set(DIGIT_BASES.values())


class ValidationWarning(Warning):
    """
    Warning raised when a value fails to validate against the computed pattern
    or schema.
    """


def flatten(it):
    try:
        for key, value in it.items():
            yield from flatten(key)
            yield from flatten(value)
    except AttributeError:
        try:
            if not isinstance(it, (str, bytes)):
                for key in it:
                    yield from flatten(key)
        except TypeError:
            pass
    yield it


class Analyzer:
    def __init__(self, *, bad_threshold=Fraction(2, 100),
                 empty_threshold=Fraction(98, 100), field_threshold=20,
                 max_numeric_len=30, strip_whitespace=False,
                 min_timestamp=None, max_timestamp=None, progress=None):
        self.bad_threshold = bad_threshold
        self.empty_threshold = empty_threshold
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
        self._progress = progress

    def measure(self, data):
        """
        Given some value *data* (typically an iterable or mapping), construct
        an object necessary for tracking the progress of the :meth:`analyze`
        and :meth:`merge` methods. If this is not called prior to these
        methods, the :attr:`progress` attribute will simply return :data:`None`
        during their run.

        As measurement is itself a potentially lengthy process,
        :attr:`progress` will be reported as a function of the top-level items
        within *data* during the run of this method. The value returned can be
        passed as the optional *progress* argument of :meth:`analyze` and
        :meth:`merge`.
        """
        # For the purposes of providing some progress reporting during
        # measurement of all the ids in *it*, we take the ids of all top
        # level items in *it*
        if self._progress is None:
            return
        try:
            if isinstance(data, sources_list):
                top = {id(item) for source in data for item in source}
            else:
                top = {id(item) for item in data}
        except TypeError:
            # The top-level item is not iterable ... this is going to be
            # quick :)
            top = {id(data)}
        self._progress.reset(total=len(top))
        start = datetime.now()
        count = 0
        for item in flatten(data):
            count += 1
            try:
                top.remove(id(item))
            except KeyError:
                pass
            else:
                self._progress.update()
        self._progress.reset(total=count)

    def analyze(self, data):
        """
        Given some value *data* (typically an iterable or mapping), return a
        description of its structure.
        """
        if self._progress is not None:
            self._progress.reset()
        return self._analyze(data, ())

    def merge(self, struct):
        """
        Given some *struct* (as returned by :meth:`analyze`), merge common
        sub-structures within it, returning the top level structure.
        """
        if self._progress is not None:
            self._progress.reset()
        return self._merge(struct)

    def _merge(self, path):
        """
        Merge common sub-structures into a single structure. For example, if a
        :class:`Dict` maps several :class:`Field` instances to other mappings
        which are all the same, then they can be collapsed to a single scalar
        which maps to the singular structure.
        """
        if isinstance(path, Container):
            if self._progress is not None:
                self._progress.update(path.lengths.card)
            if isinstance(path, Dict):
                # Only Dicts containing containers are merged; Dicts (directly)
                # containing scalars, and Tuples are left alone as containers
                # of distinct columns / fields
                if (
                    len(path.content) > 1 and
                    isinstance(path.content[0].key, Field) and
                    isinstance(path.content[0].value, Container) and
                    all(
                        item.value == path.content[0].value
                        for item in path.content[1:]
                    )
                ):
                    keys = self._match(
                        (
                            item.key.value
                            for item in path.content
                            for i in range(item.key.count)
                        ),
                        (path,), threshold=0)
                    return path.with_content([
                        DictField(self._merge(keys), self._merge(sum(
                            (p.value for p in path.content[1:]),
                            path.content[0].value
                        )))
                    ])
                return path.with_content([
                    DictField(self._merge(field.key), self._merge(field.value))
                    for field in path.content
                ])
            else:
                return path.with_content([
                    self._merge(item)
                    for item in path.content
                ])
        else:
            if self._progress is not None:
                if isinstance(path, Field):
                    self._progress.update(path.count)
                elif isinstance(path, Scalar):
                    self._progress.update(path.values.card)
            return path

    def _analyze(self, it, path, *, threshold=None, card=1):
        """
        Recursively analyze the structure of *it* at the nodes described by
        *path*. The parent cardinality is tracked in *card* (for the purposes
        of determining optional choices).
        """
        pattern = self._match(self._extract(it, path), path,
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
            return pattern.with_content([item_pattern])
        else:
            return pattern

    def _analyze_dict(self, it, path, pattern):
        """
        Subroutine of :meth:`_analyze` to handle the specific case of analyzing
        the key pattern of a :class:`Dict`, followed by the values pattern.
        """
        fields = self._analyze(
            it, path + (pattern,),
            threshold=self.field_threshold,
            card=pattern.lengths.card)
        if isinstance(fields, Fields):
            return pattern.with_content([
                DictField(field, self._analyze(
                    it, path + (pattern, field),
                    card=pattern.lengths.card))
                for field in sorted(fields)
            ])
        else:
            return pattern.with_content([
                DictField(fields, self._analyze(
                    it, path + (pattern, fields),
                    card=pattern.lengths.card))
            ])

    def _analyze_tuple(self, it, path, pattern):
        """
        Subroutine of :meth:`_analyze` to handle the specific case of analyzing
        the index pattern of a :class:`Tuple`, followed by the values pattern.
        """
        # Tuples are expected to be heterogeneous, so we attempt to treat
        # them as a tuple of item patterns
        # XXX Should this still be separate to _analyze_dict? Perhaps given the
        # future table-analysis plans...
        fields = self._analyze(
            it, path + (pattern,),
            threshold=self.field_threshold,
            card=pattern.lengths.card)
        if isinstance(fields, Fields):
            return pattern.with_content([
                TupleField(field, self._analyze(
                    it, path + (pattern, field),
                    card=pattern.lengths.card))
                for field in sorted(fields)
            ])
        else:
            return pattern.with_content([
                TupleField(fields, self._analyze(
                    it, path + (pattern, fields),
                    card=pattern.lengths.card))
            ])

    def _extract(self, it, path):
        """
        Extract all entries from *it* (a potentially nested iterable which is
        the top-level object passed to :meth:`analyze`), at the level dictated
        by *path*, a sequence of pattern-matching objects.
        """
        if not path:
            if self._progress is not None:
                self._progress.update()
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
            elif isinstance(head, Field):
                try:
                    yield from self._extract(it[head.value], tail)
                except KeyError:
                    assert head.optional, "mandatory key missing"
            elif isinstance(head, Tuple) and head.content is None:
                # Incomplete tuple content indicates we're extracting tuples
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
            if self._progress is not None:
                for item in it:
                    self._progress.update()
                    yield item
            else:
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
            if not isinstance(head, (Empty, Int, Field)):
                assert False, "invalid column index type"
            elif isinstance(head, Field):
                try:
                    yield from self._extract(it[head.value], tail)
                except IndexError:
                    assert head.optional, "mandatory field missing"
            else:
                for field, value in enumerate(it):
                    if head.validate(field):
                        yield from self._extract(value, tail)
                    else:
                        # XXX Can this ever get triggered?
                        warnings.warn(ValidationWarning(
                            "failed to validate field {field} against {head!r}"
                            .format(field=field, head=head)))
        else:
            yield from range(len(it))

    def _match(self, items, path, *, threshold=None, parent_card=None):
        """
        Find a pattern which matches all (or most) of *items*, an iterable of
        objects found at a particular layer of the hierarchy.
        """
        if threshold is None:
            threshold = self.field_threshold
        items = list(items)
        if not items:
            return Empty()
        elif all(isinstance(item, sources_list) for item in items):
            return SourcesList(items)
        elif all(isinstance(item, tuple) for item in items):
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
                # If we're attempting to match the "keys" of a dict or tuple
                # then apply the field threshold to split (and analyze)
                # sub-structures. If there are commonalities in the sub-structs
                # we'll re-merge them later
                if path and isinstance(path[-1], (Dict, Tuple)):
                    if len(sample) < threshold:
                        return Fields(
                            Field(key, count, optional=count < parent_card)
                            for key, count in sample.items()
                        )

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
        total = sum(items.values())
        if '' in items:
            if items[''] / total > self.empty_threshold:
                return Str(items)
            del items['']
        bad_threshold = ceil(total * self.bad_threshold)

        lengths = Stats.from_lengths(items)
        if lengths.max <= self.max_numeric_len:
            result = self._match_numeric_str(items, bad_threshold=bad_threshold)
            if result is not None:
                return self._match_possible_datetime(result)
        if lengths.min == lengths.max:
            return self._match_fixed_len_str(items, bad_threshold=bad_threshold)
        # XXX Add is_base64 (and others?)
        if all(value.startswith(('http://', 'https://')) for value in items):
            # XXX Refine this to parse URLs
            return URL(items)
        else:
            return Str(items)

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
            chars = CharClass(chars)
            if len(chars) > 1 and chars <= hex_digit:
                pattern.append('digit')
                if chars <= oct_digit:
                    base = max(base, 8)
                elif chars <= dec_digit:
                    base = max(base, 10)
                else:
                    base = max(base, 16)
            else:
                pattern.append(chars)
        try:
            digit = DIGIT_BASES[base]
        except KeyError:
            pass
        else:
            pattern = [digit if char == 'digit' else char for char in pattern]
        if (
            pattern[0] <= ident_first and
            all(c <= ident_char for c in pattern[1:])
        ):
            pattern = [
                pattern[0] if len(pattern[0]) == 1 else ident_first
            ] + [
                char if len(char) == 1 or char in DIGITS else ident_char
                for char in pattern[1:]
            ]
        else:
            pattern = [
                char if len(char) == 1 or char in DIGITS else any_char
                for char in pattern
            ]
        return Str(items, pattern)

    def _match_numeric_str(self, items, *, bad_threshold=0):
        """
        Given a :class:`~collections.Counter` of strings in *items*, attempt a
        variety of numeric conversions on them to discover if they represent a
        numbers (or timestamps).
        """
        representations = (
            (Bool.from_strings,     BOOL_PATTERNS),
            (Int.from_strings,      INT_PATTERNS),
            (Float.from_strings,    ('f',)),
            (DateTime.from_strings, VAR_DATETIME_PATTERNS),
        )
        for conversion, formats in representations:
            for fmt in formats:
                try:
                    return conversion(items, fmt, bad_threshold=bad_threshold)
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
                    (
                        isinstance(pattern.content, Int) and
                        pattern.pattern == 'd'
                    ) or
                    isinstance(pattern.content, Float)
                ) and
                in_range(pattern.content.values.min) and
                in_range(pattern.content.values.max)):
            return DateTime.from_numbers(pattern)
        else:
            return pattern
