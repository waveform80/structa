from math import log
from copy import copy
from datetime import datetime
from textwrap import indent, shorten
from functools import partial, total_ordering
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


def render_repr(self, **override):
    args = (
        arg
        for cls in self.__class__.mro() if cls is not object
        for arg in cls.__slots__
    )
    return '{self.__class__.__name__}({args})'.format(
        self=self, args=', '.join(
            '{arg}={value}'.format(
                arg=arg, value=override.get(arg, repr(getattr(self, arg))))
            for arg in args
            if arg not in override
            or override[arg] is not None))


# NOTE: Once oldstable is 3.7, would be nice to change all these to dataclasses
# or possibly typing.NamedTuple instances?


class ContainerStats:
    """
    Stores the cardinality, minimum, maximum, and (high) median of the lengths
    of sampled containers (lists, dicts, etc.)
    """
    __slots__ = ('card', 'min', 'max', 'median')

    def __init__(self, card, min, max, median):
        super().__init__()
        self.card = card
        self.min = min
        self.max = max
        self.median = median

    def __eq__(self, other):
        if isinstance(other, ContainerStats):
            return (
                self.card == other.card and
                self.min == other.min and
                self.max == other.max and
                self.median == other.median)
        return NotImplemented

    def __repr__(self):
        return render_repr(self)

    @classmethod
    def from_sample(cls, values):
        keys = sorted(len(value) for value in values)
        assert len(keys) > 0
        return cls(
            len(keys), keys[0], keys[-1], keys[len(keys) // 2])


class ScalarStats(ContainerStats):
    """
    Stores cardinality, minimum, maximum, and (high) median of a sampling of
    numeric values (or lengths of strings), along with top and bottom 10
    samples (including count) by popularity.
    """
    __slots__ = ('sample',)

    def __init__(self, sample, card, min, max, median):
        if not isinstance(sample, FrozenCounter):
            assert isinstance(sample, Counter)
            sample = FrozenCounter.from_counter(sample)
        super().__init__(card, min, max, median)
        self.sample = sample

    def __repr__(self):
        return render_repr(self, sample='...')

    def __eq__(self, other):
        if isinstance(other, ScalarStats):
            return (
                self.sample == other.sample and
                self.card == other.card and
                self.min == other.min and
                self.max == other.max and
                self.median == other.median)
        return NotImplemented

    @classmethod
    def from_sample(cls, sample):
        assert isinstance(sample, (Counter, FrozenCounter))
        assert sample
        keys = sorted(sample)
        card = sum(sample.values())
        index = card // 2
        for median in keys:
            index -= sample[median]
            if index < 0:
                break
        return cls(sample, card, keys[0], keys[-1], median)

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


class Pattern:
    __slots__ = ()

    def __repr__(self):
        return render_repr(self)

    def __eq__(self, other):
        # NOTE: Eventually we expect compare to grow options for tweaking the
        # comparison; the __eq__ method will simply call compare with defaults
        if isinstance(other, Pattern):
            return self.compare(other)
        return NotImplemented

    def compare(self, other):
        # We compare __class__ precisely because a Dict cannot match a Tuple,
        # etc.
        return self.__class__ is other.__class__


class Container(Pattern):
    __slots__ = ('lengths', 'pattern')

    def __init__(self, sample, pattern=None):
        super().__init__()
        self.lengths = ContainerStats.from_sample(sample)
        self.pattern = pattern

    def __repr__(self):
        return render_repr(self, lengths=None)

    def with_pattern(self, pattern):
        result = copy(self)
        result.pattern = pattern
        return result

    def compare(self, other):
        # The ContainerStats lengths attribute is ignored as it has no bearing
        # on the actual structure itself
        return (
            super().compare(other) and
            all(a.compare(b) for a, b in zip(self.pattern, other.pattern)))


class Dict(Container):
    __slots__ = ()

    def __str__(self):
        if self.pattern is None:
            return '{}'
        else:
            fields = [str(field) for field in self.pattern]
            result = ', '.join(fields)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(fields)
                return '{{\n{result}\n}}'.format(result=indent(result, '    '))
            else:
                return '{{{result}}}'.format(result=result)

    def validate(self, value):
        # XXX Make validate a procedure which raises a validation exception;
        # TypeError or ValueError accordingly (bad type or just wrong range)
        # XXX Also needs refining for keys present
        return isinstance(value, dict)


class DictField(Pattern):
    __slots__ = ('key', 'pattern')

    def __init__(self, key, pattern=None):
        super().__init__()
        self.key = key
        self.pattern = pattern

    def __str__(self):
        return '{self.key}: {self.pattern}'.format(self=self)

    def compare(self, other):
        return (
            super().compare(other) and
            self.key.compare(other.key) and
            self.pattern.compare(other.pattern))


class Tuple(Container):
    __slots__ = ()

    def __str__(self):
        if self.pattern is None:
            return '()'
        else:
            fields = [str(field) for field in self.pattern]
            result = ', '.join(fields)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(fields)
                return '(\n{result}\n)'.format(result=indent(result, '    '))
            else:
                return '({result})'.format(result=result)

    def validate(self, value):
        # XXX Make validate a procedure which raises a validation exception;
        # TypeError or ValueError accordingly (bad type or just wrong range)
        # XXX Also needs refining for fields present
        return isinstance(value, tuple)


class TupleField(Pattern):
    __slots__ = ('index', 'pattern')

    def __init__(self, index, pattern=None):
        super().__init__()
        self.index = index
        self.pattern = pattern

    def __str__(self):
        return str(self.pattern)

    def __repr__(self):
        return render_repr(self, index=None)

    def compare(self, other):
        return (
            super().compare(other) and
            self.index.compare(other.index) and
            self.pattern.compare(other.pattern))


class List(Container):
    __slots__ = ()

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


class Scalar(Pattern):
    __slots__ = ('values', 'unique')

    def __init__(self, sample):
        super().__init__()
        self.values = ScalarStats.from_sample(sample)
        self.unique = self.values.unique

    def __repr__(self):
        return render_repr(self, values='...')


class Bool(Scalar):
    __slots__ = ()

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


class Int(Scalar):
    __slots__ = ()

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


class Float(Scalar):
    __slots__ = ()

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


class DateTime(Scalar):
    __slots__ = ()

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
        dt_counter = Counter()
        for value, count in num_pattern.values.sample.items():
            dt_counter[datetime.fromtimestamp(value)] = count
        result = NumRepr(
            cls(dt_counter),
            pattern=int if isinstance(num_pattern, Int) else float)
        if isinstance(pattern, StrRepr):
            return pattern.with_inner(result)
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


class Str(Scalar):
    __slots__ = ('lengths', 'pattern')

    def __init__(self, sample, pattern=None):
        super().__init__(sample)
        self.lengths = ScalarStats.from_lengths(sample)
        self.pattern = pattern

    def compare(self, other):
        return super().compare(other) and self.pattern == other.pattern

    def __repr__(self):
        return render_repr(self, lengths=None, values='...')

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
                elif isinstance(c2, Digit):
                    if c1 in c2.chars:
                        continue
                    else:
                        return False
        return result


class Repr(Pattern):
    __slots__ = ('inner', 'pattern')

    def __init__(self, inner, pattern=None):
        super().__init__()
        self.inner = inner
        self.pattern = pattern

    def with_inner(self, inner):
        return self.__class__(inner, self.pattern)

    def compare(self, other):
        return (
            isinstance(other, Repr) and
            self.inner.compare(other.inner) and
            self.pattern == other.pattern)


class StrRepr(Repr):
    __slots__ = ()

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


class NumRepr(Repr):
    __slots__ = ()

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


class URL(Str):
    __slots__ = ()

    def __str__(self):
        return 'URL'

    def validate(self, value):
        # TODO use urlparse (or split?) and check lots more schemes
        return (
            super().validate(value) and
            value.startswith(('http://', 'https://'))
        )


class Choices(set):
    def __str__(self):
        if len(self) == 1:
            return str(next(iter(self)).value)
        else:
            choices = shorten(
                ', '.join(str(choice.value) for choice in self),
                width=60, placeholder='...')
            return '{{{choices}}}'.format(choices=choices)

    def validate(self, value):
        return any(choice.validate(value) for choice in self)


@total_ordering
class Choice(Pattern):
    __slots__ = ('value', 'optional')

    def __init__(self, value, optional=False):
        super().__init__()
        self.value = value
        self.optional = optional

    def compare(self, other):
        # We deliberately exclude *optional* from consideration here; the
        # only time a Choice is compared is during common sub-tree
        # elimination where a key might be mandatory in one sub-set but
        # optional in another
        return super().compare(other) and self.value == other.value

    def __lt__(self, other):
        if isinstance(other, Choice):
            return self.value < other.value
        return NotImplemented

    def __hash__(self):
        # We define a hash to permit Choice to be present in a Choices
        # instance; note that this implies a Choice is effectively immutable
        return hash((self.value,))

    def __str__(self):
        return repr(self.value) + ('*' if self.optional else '')

    def validate(self, value):
        return value == self.value


class Value(Pattern):
    __slots__ = ()

    def __new__(cls):
        # This is a singleton class; all instances are the same
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


class Empty(Pattern):
    __slots__ = ()

    def __new__(cls):
        # This is a singleton class; all instances are the same
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
