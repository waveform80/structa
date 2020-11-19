from math import log
from datetime import datetime
from textwrap import indent, shorten
from functools import partial
from collections import namedtuple, Counter
from collections.abc import Mapping

from .chars import Digit, AnyChar


class FrozenCounter(Mapping):
    def __init__(self, it):
        self._counter = Counter(it)
        self._hash = None

    @classmethod
    def from_counter(cls, counter):
        if isinstance(counter, Counter):
            self = cls(())
            self._counter = counter.copy()
            return self
        elif isinstance(counter, FrozenCounter):
            # It's frozen; no need to go recreating stuff
            return counter
        else:
            assert False

    def most_common(self, n=None):
        return self._counter.most_common(n)

    def elements(self):
        return self._counter.elements()

    def __iter__(self):
        return iter(self._counter)

    def __len__(self):
        return len(self._counter)

    def __getitem__(self, key):
        return self._counter[key]

    def __repr__(self):
        return "{self.__class__.__name__}({self._counter})".format(self=self)

    def __hash__(self):
        if self._hash is None:
            self._hash = hash((frozenset(self), frozenset(self.values())))
        return self._hash

    def __eq__(self, other):
        return self._counter == other

    def __ne__(self, other):
        return self._counter != other


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


def try_conversion(sample, conversion, threshold=0):
    """
    Given a :class:`~collections.Counter` *sample* of strings, call the
    specified *conversion* on each string returning the set of converted
    values.

    *conversion* must be a callable that accepts a single string parameter and
    returns the converted value. If the *conversion* fails it must raise a
    :exc:`ValueError` exception.

    If *threshold* is specified (defaults to 0), it defines the number of
    "bad" conversions (which result in :exc:`ValueError` being raised) that
    will be ignored. If *threshold* is exceeded, then :exc:`ValueError` will
    be raised (or rather passed through from the underlying *conversion*).
    """
    assert isinstance(sample, (Counter, FrozenCounter))
    assert sample
    result = Counter()
    if threshold:
        assert threshold > 0
        for item, count in sample.items():
            try:
                result[conversion(item)] += count
            except ValueError: # XXX and TypeError?
                threshold -= count
                if threshold < 0:
                    raise
        if result:
            return result
        else:
            # If threshold permitted us to get to this point but we managed to
            # convert absolutely nothing, that's not success!
            raise ValueError('zero successful conversions')
    else:
        for item, count in sample.items():
            result[conversion(item)] += count
        return result


class ContainerStats(namedtuple('_ContainerStats', (
        'card', 'min', 'max', 'median'))):
    """
    Stores the cardinality, minimum, maximum, and (high) median of the lengths
    of sampled containers (lists, dicts, etc.)
    """
    __slots__ = ()

    @classmethod
    def from_sample(cls, values):
        keys = sorted(len(value) for value in values)
        assert len(keys) > 0
        return super().__new__(
            cls, len(keys), keys[0], keys[-1], keys[len(keys) // 2])


class ScalarStats(namedtuple('_ScalarStats', (
        'sample', 'card', 'min', 'max', 'median'))):
    """
    Stores cardinality, minimum, maximum, and (high) median of a sampling of
    numeric values (or lengths of strings), along with top and bottom 10
    samples (including count) by popularity.
    """
    __slots__ = ()

    @classmethod
    def from_sample(cls, sample):
        if not isinstance(sample, FrozenCounter):
            assert isinstance(sample, Counter)
            sample = FrozenCounter.from_counter(sample)
        assert sample
        keys = sorted(sample)
        card = sum(sample.values())
        index = card // 2
        for median in keys:
            index -= sample[median]
            if index < 0:
                break
        return super().__new__(cls, FrozenCounter.from_counter(sample),
                               card, keys[0], keys[-1], median)

    @classmethod
    def from_lengths(cls, values):
        assert isinstance(values, (Counter, FrozenCounter))
        lengths = Counter()
        for item, count in values.items():
            lengths[len(item)] += count
        return cls.from_sample(lengths)

    @property
    def unique(self):
        """
        True if the maximum cardinality in the :attr:`sample` is 1.
        """
        for value, count in self.sample.most_common():
            return count == 1


class Dict(namedtuple('_Dict', ('lengths', 'fields', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, fields=None, pattern=None):
        return super().__new__(cls, ContainerStats.from_sample(sample),
                               fields, pattern)

    def __str__(self):
        if self.pattern is None:
            return '{}'
        else:
            elems = [
                '{key}: {value}'.format(key=key, value=value)
                for key, value in zip(self.fields, self.pattern)
            ]
            result = ', '.join(elems)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(elems)
                return '{{\n{result}\n}}'.format(result=indent(result, '    '))
            else:
                return '{{{result}}}'.format(result=result)

    def validate(self, value):
        # XXX Make validate a procedure which raises a validation exception;
        # TypeError or ValueError accordingly (bad type or just wrong range)
        return isinstance(value, dict)


class Tuple(namedtuple('_Tuple', ('lengths', 'fields', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, fields=None, pattern=None):
        return super().__new__(cls, ContainerStats.from_sample(sample),
                               fields, pattern)

    def __str__(self):
        if self.pattern is None:
            return '()'
        else:
            elems = [
                (
                    '{field.value}={value}'
                    if isinstance(field, Choice)
                    and isinstance(field.value, str) else
                    '{value}'
                ).format(field=field, value=value)
                for field, value in zip(self.fields, self.pattern)
            ]
            result = ', '.join(elems)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(elems)
                return '(\n{result}\n)'.format(result=indent(result, '    '))
            else:
                return '({result})'.format(result=result)

    def validate(self, value):
        return isinstance(value, tuple)


class TupleField(namedtuple('_TupleField', ('index', 'name'))):
    __slots__ = ()

    def __new__(cls, index, name=''):
        return super().__new__(cls, index, name)


class List(namedtuple('_List', ('lengths', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        return super().__new__(cls, ContainerStats.from_sample(sample),
                               pattern)

    def __str__(self):
        if self.pattern is None:
            return '[]'
        else:
            elems = [str(item) for item in self.pattern]
            result = ', '.join(elems)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(elems)
                return '[\n{result}\n]'.format(result=indent(result, '    '))
            else:
                return '[{result}]'.format(result=result)

    def validate(self, value):
        return isinstance(value, list)


class Str(namedtuple('_Str', ('values', 'lengths', 'pattern', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        values = ScalarStats.from_sample(sample)
        lengths = ScalarStats.from_lengths(sample)
        return super().__new__(cls, values, lengths, pattern, values.unique)

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
            self.lengths.min <= len(value) <= self.lengths.max
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


class StrRepr(namedtuple('_StrRepr', ('inner', 'pattern'))):
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


class NumRepr(namedtuple('_NumRepr', ('inner', 'pattern'))):
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


class Int(namedtuple('_Int', ('values', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample):
        values = ScalarStats.from_sample(sample)
        return super().__new__(cls, values, values.unique)

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        base = {
            'o': 8,
            'd': 10,
            'x': 16,
        }[pattern]
        return StrRepr(
            cls(try_conversion(
                iterable, partial(int, base=base), bad_threshold)),
            pattern=pattern)

    def __str__(self):
        return 'int range={min}..{max}'.format(
            min=format_int(self.values.min),
            max=format_int(self.values.max)
        )

    def validate(self, value):
        return (
            isinstance(value, int) and
            self.values.min <= value <= self.values.max
        )


class Float(namedtuple('_Float', ('values', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample):
        values = ScalarStats.from_sample(sample)
        return super().__new__(cls, values, values.unique)

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        return StrRepr(
            cls(try_conversion(iterable, float, bad_threshold)),
            pattern=pattern)

    def __str__(self):
        return 'float range={min:.1f}..{max:.1f}'.format(
            min=self.values.min, max=self.values.max)

    def validate(self, value):
        return (
            isinstance(value, float) and
            self.values.min <= value <= self.values.max
        )


class DateTime(namedtuple('_DateTime', ('values', 'unique'))):
    __slots__ = ()

    def __new__(cls, sample):
        values = ScalarStats.from_sample(sample)
        return super().__new__(cls, values, values.unique)

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        conv = lambda s: datetime.strptime(s, pattern)
        return StrRepr(
            cls(try_conversion(iterable, conv, bad_threshold)),
            pattern=pattern)

    @classmethod
    def from_numbers(cls, pattern):
        if isinstance(pattern, StrRepr):
            num_pattern = pattern.inner
        else:
            num_pattern = pattern
        result = NumRepr(
            super().__new__(cls, ScalarStats(
                FrozenCounter(
                    datetime.fromtimestamp(value)
                    for value in num_pattern.values.sample.elements()
                ),
                num_pattern.values.card,
                datetime.fromtimestamp(num_pattern.values.min),
                datetime.fromtimestamp(num_pattern.values.max),
                datetime.fromtimestamp(num_pattern.values.median),
            ), num_pattern.values.unique),
            pattern=int if isinstance(num_pattern, Int) else float)
        if isinstance(pattern, StrRepr):
            return pattern._replace(inner=result)
        else:
            return result

    def __str__(self):
        return 'datetime range={min}..{max}'.format(
            min=self.values.min.replace(microsecond=0),
            max=self.values.max.replace(microsecond=0))

    def validate(self, value):
        return (
            isinstance(value, datetime) and
            self.values.min <= value <= self.values.max
        )


class Bool(namedtuple('_Bool', ('values',))):
    __slots__ = ()

    def __new__(cls, sample):
        return super().__new__(cls, ScalarStats.from_sample(sample))

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


class URL(namedtuple('_URL', ('unique',))):
    __slots__ = ()

    def __new__(cls, unique=False):
        # XXX Analyze sample for common scheme/host/path-patterns
        return super().__new__(cls, unique)

    def __str__(self):
        return 'URL'

    def validate(self, value):
        # TODO use urlparse (or split?) and check lots more schemes
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


class Choice(namedtuple('_Choice', ('value', 'optional'))):
    __slots__ = ()

    def __str__(self):
        return repr(self.value) + ('*' if self.optional else '')

    def validate(self, value):
        return value == self.value


class Value:
    __slots__ = ()

    def __new__(cls):
        try:
            return _value
        except NameError:
            return super().__new__(cls)

    def __str__(self):
        return 'value'

    def __repr__(self):
        return 'Value()'

    def validate(self, value):
        return True


class Empty:
    __slots__ = ()

    def __new__(cls):
        try:
            return _empty
        except NameError:
            return super().__new__(cls)

    def __str__(self):
        return ''

    def __repr__(self):
        return 'Empty()'

    def validate(self, value):
        return False


_empty = Empty()
_value = Value()
