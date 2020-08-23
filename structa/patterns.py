from math import log
from datetime import datetime
from textwrap import indent, shorten
from functools import partial
from collections import namedtuple, Counter

from .chars import Digit, AnyChar


def format_int(i):
    """
    Reduce *i* by some appropriate power of 1000 and suffix it with an
    appropriate Greek qualifier (K for kilo, M for mega, etc.)
    """
    suffixes = ('', 'K', 'M', 'G', 'T', 'P')
    try:
        index = min(len(suffixes) - 1, int(log(abs(i), 1000)))
    except ValueError:
        return '0'
    if not index:
        return str(i)
    else:
        return '{value:.1f}{suffix}'.format(
            value=(i / 1000 ** index),
            suffix=suffixes[index])


def to_bool(s, false='0', true='1'):
    """
    Convert the string *s* (stripped and lower-cased) to a bool, if it matches
    either the *false* string (defaults to '0') or *true* (defaults to '1').
    If it matches neither, raises a :exc:`ValueError`.
    """
    try:
        return {
            false: False,
            true:  True,
        }[s.strip().lower()]
    except KeyError:
        raise ValueError('not a valid bool {!r}'.format(s))


def try_conversion(iterable, conversion, threshold=0):
    """
    Given an *iterable* of strings, call the specified *conversion* on each
    string returning the set of converted values.

    *conversion* must be a callable that accepts a single string parameter and
    returns the converted value. If the *conversion* fails it must raise a
    :exc:`ValueError` exception.

    If *threshold* is specified (defaults to 0), it defines the number of
    "bad" conversions (which result in :exc:`ValueError` being raised) that
    will be ignored. If *threshold* is exceeded, then :exc:`ValueError` will
    be raised (or rather passed through from the underlying *conversion*).
    """
    if not threshold:
        return {conversion(element) for element in iterable}
    assert threshold > 0
    sample = set()
    for element in iterable:
        try:
            sample.add(conversion(element))
        except ValueError: # XXX and TypeError?
            if not threshold:
                raise
            threshold -= 1
    return sample


class Stats(namedtuple('Stats', ('card', 'min', 'max', 'median'))):
    """
    Return the cardinality, minimum, maximum, and (high) median of the integer
    *values* list.
    """
    @classmethod
    def from_sample(cls, values):
        # XXX Add most/least selective/popular? Might make things simpler as
        # this would mandate converting values to a Counter anyway
        keys = sorted(values)
        assert len(keys) > 0
        if isinstance(values, Counter):
            length = sum(values.values())
            index = length // 2
            for key in keys:
                index -= values[key]
                if index < 0:
                    break
            median = key
            return super().__new__(cls, length, keys[0], keys[-1], median)
        else:
            return super().__new__(
                cls, len(keys), keys[0], keys[-1], keys[len(keys) // 2])

    @classmethod
    def from_lengths(cls, values):
        if isinstance(values, Counter):
            lengths = Counter()
            for item, count in values.items():
                lengths[len(item)] += count
        else:
            lengths = (len(value) for value in values)
        return cls.from_sample(lengths)


class Dict(namedtuple('Dict', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        return super().__new__(cls, Stats.from_lengths(sample), pattern)

    def __str__(self):
        if self.pattern is None:
            return '{}'
        else:
            elems = ', '.join('{key}: {value}'.format(key=key, value=value)
                              for key, value in self.pattern.items())
            if '\n' in elems or len(elems) > 60:
                elems = ',\n'.join('{key}: {value}'.format(key=key, value=value)
                                   for key, value in self.pattern.items())
                return '{{\n{elems}\n}}'.format(elems=indent(elems, '    '))
            else:
                return '{{{elems}}}'.format(elems=elems)

    def validate(self, value):
        # XXX Make validate a procedure which raises a validation exception;
        # TypeError or ValueError accordingly (bad type or just wrong range)
        return isinstance(value, dict)


class List(namedtuple('List', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        return super().__new__(cls, Stats.from_lengths(sample), pattern)

    def __str__(self):
        if self.pattern is None:
            return '[]'
        else:
            elems = ', '.join(str(item) for item in self.pattern)
            if '\n' in elems or len(elems) > 60:
                elems = ',\n'.join(str(item) for item in self.pattern)
                return '[\n{elems}\n]'.format(elems=indent(elems, '    '))
            else:
                return '[{elems}]'.format(elems=elems)

    def validate(self, value):
        return isinstance(value, list)


class Str(namedtuple('Str', ('stats', 'pattern', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None, unique=False):
        return super().__new__(cls, Stats.from_lengths(sample), pattern, unique)

    def __str__(self):
        if self.pattern is None:
            return 'str'
        else:
            pattern = ''.join(
                c if isinstance(c, str) else c.display
                for c in self.pattern)
            return 'str pattern={pattern}'.format(
                pattern=shorten(pattern, width=60, placeholder='...'))

    def validate(self, value):
        result = (
            isinstance(value, str) and
            self.stats.min <= len(value) <= self.stats.max
        )
        if result and self.pattern is not None:
            for c1, c2 in zip(value, self.pattern):
                if isinstance(c2, str):
                    if c1 == c2:
                        continue
                    else:
                        return False
                elif issubclass(c2, Digit):
                    if c1 in c2.chars:
                        continue
                    else:
                        return False
        return result


class StrRepr(namedtuple('StrRepr', ('inner', 'pattern'))):
    __slots__ = ()

    def __new__(cls, inner, pattern=None):
        return super().__new__(cls, inner, pattern)

    def __str__(self):
        return 'str of {self.inner} format={self.pattern}'.format(self=self)

    def validate(self, value):
        if not isinstance(value, str):
            return False
        try:
            if isinstance(self.inner, Int):
                bases = {'o': 8, 'd': 10, 'x': 16}
                value = int(value, base=bases[self.pattern])
            elif isinstance(self.inner, NumRepr) and self.inner.pattern is int:
                assert self.pattern == 'd'
                value = int(value)
            elif isinstance(self.inner, Float):
                assert self.pattern == 'f'
                value = float(value)
            elif isinstance(self.inner, NumRepr) and self.inner.pattern is float:
                assert self.pattern == 'f'
                value = float(value)
            elif isinstance(self.inner, DateTime):
                value = datetime.strptime(value, self.pattern)
            elif isinstance(self.inner, Bool):
                false, true = self.pattern.split('|', 1)
                value = to_bool(value, false, true)
            else:
                assert False
        except ValueError:
            return False
        else:
            return self.inner.validate(value)


class NumRepr(namedtuple('NumRepr', ('inner', 'pattern'))):
    __slots__ = ()

    def __new__(cls, inner, pattern=None):
        return super().__new__(cls, inner, pattern)

    def __str__(self):
        if self.pattern is int:
            template = 'int of {self.inner}'
        elif self.pattern is float:
            template = 'float of {self.inner}'
        else:
            assert False
        return template.format(self=self)

    def validate(self, value):
        if not isinstance(value, self.pattern):
            return False
        try:
            if isinstance(self.inner, DateTime):
                value = datetime.fromtimestamp(value)
            else:
                assert False
        except ValueError:
            return False
        else:
            return self.inner.validate(value)


class Int(namedtuple('Int', ('stats', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample, unique=False):
        return super().__new__(cls, Stats.from_sample(sample), unique)

    @classmethod
    def from_strings(cls, iterable, pattern, unique=False, bad_threshold=0):
        base = {
            'o': 8,
            'd': 10,
            'x': 16,
        }[pattern]
        return StrRepr(
            cls(
                try_conversion(
                    iterable, partial(int, base=base), bad_threshold),
                unique=unique
            ),
            pattern=pattern)

    def __str__(self):
        return 'int range={min}..{max}'.format(
            min=format_int(self.stats.min),
            max=format_int(self.stats.max)
        )

    def validate(self, value):
        return (
            isinstance(value, int) and
            self.stats.min <= value <= self.stats.max
        )


class Float(namedtuple('Float', ('stats', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample, unique=False):
        return super().__new__(cls, Stats.from_sample(sample), unique)

    @classmethod
    def from_strings(cls, iterable, pattern, unique=False, bad_threshold=0):
        return StrRepr(
            cls(
                try_conversion(iterable, float, bad_threshold),
                unique=unique
            ),
            pattern=pattern)

    def __str__(self):
        return 'float range={min:.1f}..{max:.1f}'.format(
            min=self.stats.min, max=self.stats.max)

    def validate(self, value):
        return (
            isinstance(value, float) and
            self.stats.min <= value <= self.stats.max
        )


class DateTime(namedtuple('DateTime', ('stats', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample, unique=False):
        return super().__new__(cls, Stats.from_sample(sample), unique)

    @classmethod
    def from_strings(cls, iterable, pattern, unique=False, bad_threshold=0):
        conv = lambda s: datetime.strptime(s, pattern)
        return StrRepr(
            cls(
                try_conversion(iterable, conv, bad_threshold),
                unique=unique),
            pattern=pattern)

    @classmethod
    def from_numbers(cls, pattern):
        if isinstance(pattern, StrRepr):
            num_pattern = pattern.inner
        else:
            num_pattern = pattern
        result = NumRepr(
            super().__new__(cls, Stats(
                num_pattern.stats.card,
                datetime.fromtimestamp(num_pattern.stats.min),
                datetime.fromtimestamp(num_pattern.stats.max),
                datetime.fromtimestamp(num_pattern.stats.median),
            ), num_pattern.unique),
            pattern=int if isinstance(num_pattern, Int) else float)
        if isinstance(pattern, StrRepr):
            return pattern._replace(inner=result)
        else:
            return result

    def __str__(self):
        return 'datetime range={min}..{max}'.format(
            min=self.stats.min.replace(microsecond=0),
            max=self.stats.max.replace(microsecond=0))

    def validate(self, value):
        return (
            isinstance(value, datetime) and
            self.stats.min <= value <= self.stats.max
        )


class Bool(namedtuple('Bool', ('stats',))):
    __slots__ = ()

    def __new__(cls, sample):
        return super().__new__(cls, Stats.from_sample(sample))

    def __str__(self):
        return 'bool'

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        false, true = pattern.split('|', 1)
        return StrRepr(
            cls(
                try_conversion(
                    iterable, partial(to_bool, false=false, true=true),
                    bad_threshold)
            ),
            pattern='{false}|{true}'.format(false=false, true=true)
        )

    def validate(self, value):
        return (
            isinstance(value, bool) or
            (isinstance(value, int) and value in (0, 1))
        )


class URL(namedtuple('URL', ('unique',))):
    __slots__ = ()

    def __new__(cls, unique=False):
        # XXX Analyze sample for common scheme/host/path-patterns
        return super().__new__(cls, unique)

    def __str__(self):
        return 'URL'

    def validate(self, value):
        # XXX Update
        return (
            isinstance(value, str) and
            value.startswith(('http://', 'https://'))
        )


class Choices(set):
    def __str__(self):
        if len(self) == 1:
            return str(next(iter(self)).value)
        else:
            choices = shorten(
                '|'.join(str(choice.value) for choice in self),
                width=60, placeholder='...')
            return '{{{choices}}}'.format(choices=choices)

    def validate(self, value):
        return any(choice.validate(value) for choice in self)


class Choice(namedtuple('Choice', ('value', 'optional'))):
    __slots__ = ()

    def __str__(self):
        return repr(self.value) + ('*' if self.optional else '')

    def validate(self, value):
        return value == self.value


class Value:
    __slots__ = ()

    def __str__(self):
        return 'value'

    def __call__(self):
        return self

    def validate(self, value):
        return True


class Empty:
    __slots__ = ()

    def __str__(self):
        return ''

    def __call__(self):
        return self

    def validate(self, value):
        return False


# Singletons
Value = Value()
Empty = Empty()
