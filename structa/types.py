from copy import copy
from numbers import Real
from datetime import datetime
from textwrap import indent, shorten
from functools import partial, total_ordering
from collections.abc import Mapping

from .collections import Counter, FrozenCounter
from .conversions import try_conversion, parse_bool
from .format import format_int, format_repr
from .xml import ElementFactory, xml, merge_siblings


class MyElementFactory(ElementFactory):
    def _format(self, value):
        if isinstance(value, datetime):
            return '{0:%Y-%m-%d %H:%M:%S}'.format(value)
        elif isinstance(value, float):
            return '{0:.7g}'.format(value)
        elif isinstance(value, int):
            return format_int(value)
        elif isinstance(value, bool):
            return ('false', 'true')[value]
        else:
            return super()._format(value)

tag = MyElementFactory()


class Stats:
    """
    Stores cardinality, minimum, maximum, and (high) median of a sampling of
    numeric values (or lengths of strings or containers), along with the
    specified sample of values.
    """
    __slots__ = ('sample', 'card', 'min', 'q1', 'q2', 'q3', 'max', 'unique')

    def __init__(self, sample, card, min, q1, q2, q3, max):
        if not isinstance(sample, FrozenCounter):
            assert isinstance(sample, Counter)
            sample = FrozenCounter.from_counter(sample)
        self.sample = sample
        self.card = card
        self.min = min
        self.q1 = q1
        self.q2 = q2
        self.q3 = q3
        self.max = max
        for value, count in self.sample.most_common():
            self.unique = count == 1
            break

    def __repr__(self):
        return format_repr(self, sample='...')

    def __xml__(self):
        indexes = {i: '.' for i in range(10)}
        try:
            delta = self.max - self.min
        except TypeError:
            # Cannot calculate a 1d quartile graph for vectors like str; note
            # that we use subtraction for this test because simply testing if
            # min/max are numbers is not sufficient. Timestamps can be
            # subtracted (and, crucially, divided to produce a float) but do
            # not count as numbers in Python's number hierarchy (not sure why)
            graph = ''
        else:
            if delta:
                for n, q in enumerate((self.q1, self.q2, self.q3), start=1):
                    indexes[int(10 * (q - self.min) / delta)] = str(n)
                graph = ''.join(indexes[i] for i in range(10))
            else:
                graph = '..'
        content = [
            tag.summary(
                tag.min(self.min),
                tag.q1(self.q1),
                tag.q2(self.q2),
                tag.q3(self.q3),
                tag.max(self.max),
                merge_siblings(
                    tag.graph(
                        tag.lit(c) if c == '.' else tag.pat(c)
                        for c in graph
                    )
                ),
                unique=self.unique
            )
        ]
        if not self.unique:
            if len(self.sample) > 20:
                common = self.sample.most_common()
                content.append(
                    tag.sample(
                        [tag.value(value, count=count)
                         for value, count in common[:10]],
                        tag.more(),
                        [tag.value(value, count=count)
                         for value, count in common[-10:]],
                    )
                )
            else:
                content.append(
                    tag.sample(
                        tag.value(value, count=count)
                        for value, count in self.sample.most_common()
                    )
                )
        return tag.stats(content)

    def __eq__(self, other):
        if isinstance(other, Stats):
            return (
                self.sample == other.sample and
                self.card == other.card and
                self.min == other.min and
                self.q1 == other.q1 and
                self.q2 == other.q2 and
                self.q3 == other.q3 and
                self.max == other.max)
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Stats):
            return Stats.from_sample(self.sample + other.sample)
        return NotImplemented

    @classmethod
    def from_sample(cls, sample):
        assert isinstance(sample, (Counter, FrozenCounter)), \
                '{sample} is not Counter'.format(sample=sample)
        assert sample
        keys = sorted(sample)
        card = sum(sample.values())
        indexes = (0, card // 4, card // 2, 3 * card // 4)
        summary = []
        index = 0
        for key in keys:
            while index >= indexes[len(summary)]:
                summary.append(key)
                if len(summary) == len(indexes):
                    summary.append(keys[-1])
                    return cls(sample, card, *summary)
            index += sample[key]
        # If we reach here, the remaining quartiles are all max
        summary.extend([keys[-1]] * (5 - len(summary)))
        return cls(sample, card, *summary)

    @classmethod
    def from_lengths(cls, values):
        if isinstance(values, (Counter, FrozenCounter)):
            lengths = Counter()
            for item, count in values.items():
                lengths[len(item)] += count
        else:
            lengths = FrozenCounter(len(item) for item in values)
        return cls.from_sample(lengths)

    @property
    def median(self):
        return self.q2


class Type:
    __slots__ = ()

    def __repr__(self):
        return format_repr(self)

    def __xml__(self):
        return tag.type()

    def __eq__(self, other):
        # NOTE: Eventually we expect compare to grow options for tweaking the
        # comparison; the __eq__ method will simply call compare with defaults
        if isinstance(other, Type):
            return self.compare(other)
        return NotImplemented

    def compare(self, other):
        return (
            isinstance(self, other.__class__) or
            isinstance(other, self.__class__))


class Container(Type):
    __slots__ = ('lengths', 'content')

    def __init__(self, sample, content=None):
        super().__init__()
        self.lengths = Stats.from_lengths(sample)
        self.content = content

    def __repr__(self):
        return format_repr(self, lengths=None)

    def __xml__(self):
        return tag.container(
            tag.content(xml(field) for field in self.content),
            tag.lengths(iter(xml(self.lengths))),
        )

    def __add__(self, other):
        if self == other:
            result = copy(self)
            result.lengths = self.lengths + other.lengths
            result.content = [
                a + b for a, b in zip(self.content, other.content)
            ]
            return result
        return NotImplemented

    def with_content(self, content):
        result = copy(self)
        result.content = content
        return result

    def compare(self, other):
        # The Stats lengths attribute is ignored as it has no bearing on the
        # actual structure itself
        return (
            super().compare(other) and
            all(a.compare(b) for a, b in zip(self.content, other.content)))


class Dict(Container):
    __slots__ = ()

    def __str__(self):
        if self.content is None:
            return '{}'
        else:
            fields = [str(field) for field in self.content]
            result = ', '.join(fields)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(fields)
                return '{{\n{result}\n}}'.format(result=indent(result, '    '))
            else:
                return '{{{result}}}'.format(result=result)

    def __xml__(self):
        return tag.dict(iter(super().__xml__()))

    def validate(self, value):
        # XXX Make validate a procedure which raises a validation exception;
        # TypeError or ValueError accordingly (bad type or just wrong range)
        # XXX Also needs refining for keys present
        return isinstance(value, dict)


class DictField(Type):
    __slots__ = ('key', 'value')

    def __init__(self, key, value=None):
        super().__init__()
        self.key = key
        self.value = value

    def __str__(self):
        return '{self.key}: {self.value}'.format(self=self)

    def __xml__(self):
        return tag.field(xml(self.key), xml(self.value))

    def __add__(self, other):
        return DictField(self.key + other.key,
                         self.value + other.value)

    def compare(self, other):
        return (
            super().compare(other) and
            self.key.compare(other.key) and
            self.value is not None and
            other.value is not None and
            self.value.compare(other.value))


class Tuple(Container):
    __slots__ = ()

    def __str__(self):
        if self.content is None:
            return '()'
        else:
            fields = [str(field) for field in self.content]
            result = ', '.join(fields)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(fields)
                return '(\n{result}\n)'.format(result=indent(result, '    '))
            else:
                return '({result})'.format(result=result)

    def __xml__(self):
        return tag.tuple(iter(super().__xml__()))

    def validate(self, value):
        # XXX Make validate a procedure which raises a validation exception;
        # TypeError or ValueError accordingly (bad type or just wrong range)
        # XXX Also needs refining for fields present
        return isinstance(value, tuple)


class TupleField(Type):
    __slots__ = ('index', 'value')

    def __init__(self, index, value=None):
        super().__init__()
        self.index = index
        self.value = value

    def __str__(self):
        return str(self.value)

    def __xml__(self):
        return xml(self.value)

    def __repr__(self):
        return format_repr(self, index=None)

    def __add__(self, other):
        return TupleField(self.index + other.index,
                          self.value + other.value)

    def compare(self, other):
        return (
            super().compare(other) and
            self.index.compare(other.index) and
            self.value is not None and
            other.value is not None and
            self.value.compare(other.value))


class List(Container):
    __slots__ = ()

    def __str__(self):
        if self.content is None:
            return '[]'
        else:
            elems = [str(item) for item in self.content]
            result = ', '.join(elems)
            if '\n' in result or len(result) > 60:
                result = ',\n'.join(elems)
                return '[\n{result}\n]'.format(result=indent(result, '    '))
            else:
                return '[{result}]'.format(result=result)

    def __xml__(self):
        return tag.list(iter(super().__xml__()))

    def validate(self, value):
        return isinstance(value, list)


class sources_list(list):
    pass


class SourcesList(List):
    pass


class Scalar(Type):
    __slots__ = ('values',)

    def __init__(self, sample):
        super().__init__()
        self.values = Stats.from_sample(sample)

    def __xml__(self):
        return tag.scalar(tag.values(iter(xml(self.values))))

    def __add__(self, other):
        if self == other:
            if issubclass(self.__class__, other.__class__):
                result = copy(other)
            else:
                result = copy(self)
            result.values = self.values + other.values
            return result
        return NotImplemented

    def __repr__(self):
        return format_repr(self, values='...')


class Float(Scalar):
    __slots__ = ()

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        return StrRepr(
            cls(try_conversion(iterable, float, bad_threshold)),
            pattern=pattern)

    def __str__(self):
        return 'float range={min:.7g}..{max:.7g}'.format(
            min=self.values.min, max=self.values.max)

    def __xml__(self):
        return tag.float(iter(super().__xml__()))

    def validate(self, value):
        return (
            isinstance(value, float) and
            self.values.min <= value <= self.values.max
        )


class Int(Float):
    __slots__ = ()

    # NOTE: Int is a subclass of Float partly to provide a rough immitation of
    # Python's "numeric tower" (see the numbers module) in permitting an Int
    # pattern to compare equal to a Float pattern for the purposes of merging

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

    def __xml__(self):
        return tag.int(iter(super().__xml__()))

    def validate(self, value):
        return (
            isinstance(value, int) and
            self.values.min <= value <= self.values.max
        )


class Bool(Int):
    __slots__ = ()

    # NOTE: Bool is a subclass of Int; see note in Int for reasons

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        false, true = pattern.split('|', 1)
        return StrRepr(
            cls(
                try_conversion(
                    iterable, partial(parse_bool, false=false, true=true),
                    bad_threshold)
            ),
            pattern='{false}|{true}'.format(false=false, true=true)
        )

    def __str__(self):
        return 'bool'

    def __xml__(self):
        return tag.bool(iter(super().__xml__()))

    def validate(self, value):
        return (
            isinstance(value, bool) or
            (isinstance(value, int) and value in (0, 1))
        )


class DateTime(Scalar):
    __slots__ = ()

    # NOTE: There are no circumstances in Python where a datetime instance can
    # successfully compare equal to a float, in contrast to the fact that False
    # == 0 == 0.0, so DateTime simply derives from Scalar

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        conv = lambda s: datetime.strptime(s, pattern)
        return StrRepr(
            cls(try_conversion(iterable, conv, bad_threshold)),
            pattern=pattern)

    @classmethod
    def from_numbers(cls, pattern):
        if isinstance(pattern, StrRepr):
            num_pattern = pattern.content
        else:
            num_pattern = pattern
        dt_counter = Counter()
        for value, count in num_pattern.values.sample.items():
            dt_counter[datetime.fromtimestamp(value)] = count
        result = NumRepr(cls(dt_counter), pattern=num_pattern.__class__)
        if isinstance(pattern, StrRepr):
            return pattern.with_content(result)
        else:
            return result

    def __str__(self):
        return 'datetime range={min}..{max}'.format(
            min=self.values.min.replace(microsecond=0),
            max=self.values.max.replace(microsecond=0))

    def __xml__(self):
        return tag.datetime(iter(super().__xml__()))

    def validate(self, value):
        return (
            isinstance(value, datetime) and
            self.values.min <= value <= self.values.max
        )


class Str(Scalar):
    __slots__ = ('lengths', 'pattern')

    def __init__(self, sample, pattern=None):
        super().__init__(sample)
        self.lengths = Stats.from_lengths(sample)
        self.pattern = pattern

    def __repr__(self):
        return format_repr(self, lengths=None, values='...')

    def __str__(self):
        if self.pattern is None:
            return 'str'
        else:
            pattern = ''.join(str(c) for c in self.pattern)
            return 'str pattern={pattern}'.format(
                pattern=shorten(pattern, width=60, placeholder='...'))

    def __xml__(self):
        return tag.str(
            iter(super().__xml__()),
            tag.lengths(iter(xml(self.lengths))),
            merge_siblings(tag.pattern(xml(c) for c in self.pattern))
                if self.pattern else []
        )

    def __add__(self, other):
        if self == other:
            if (
                self.pattern is None or other.pattern is None or
                len(self.pattern) != len(other.pattern)
            ):
                new_pattern = None
            else:
                new_pattern = [
                    self_char | other_char
                    for self_char, other_char
                    in zip(self.pattern, other.pattern)
                ]
            result = copy(self)
            result.values = self.values + other.values
            result.lengths = self.lengths + other.lengths
            result.pattern = new_pattern
            return result
        return NotImplemented

    def validate(self, value):
        result = (
            isinstance(value, str) and
            self.lengths.min <= len(value) <= self.lengths.max
        )
        if result and self.pattern is not None:
            for c1, c2 in zip(value, self.pattern):
                if c1 not in c2:
                    return False
        return result


class Repr(Type):
    __slots__ = ('content', 'pattern')

    def __init__(self, content, pattern=None):
        super().__init__()
        self.content = content
        self.pattern = pattern

    def with_content(self, content):
        return self.__class__(content, self.pattern)

    def compare(self, other):
        # XXX Should we compare pattern here? Consider case of mistaken octal/
        # dec pattern when it's actually hex in the merge scenario?
        return super().compare(other) and self.content.compare(other.content)


class StrRepr(Repr):
    __slots__ = ()

    int_bases = {'o': 8, 'd': 10, 'x': 16}

    def __str__(self):
        return 'str of {self.content} pattern={self.pattern}'.format(self=self)

    def __xml__(self):
        return tag.strof(
            xml(self.content),
            tag.pattern(tag.pat(str(self.pattern)))
        )

    def __add__(self, other):
        if self == other:
            if isinstance(self.content, other.content.__class__):
                child, parent = self, other
            else:
                child, parent = other, self
            if (
                child.content.__class__ is Int and
                parent.content.__class__ is Int
            ):
                pattern = sorted(child.pattern + parent.pattern,
                                 key=self.int_bases.get)[-1]
            else:
                pattern = parent.pattern
            return parent.__class__(child.content + parent.content, pattern)
        return NotImplemented

    def compare(self, other):
        if super().compare(other):
            if isinstance(self.content, other.content.__class__):
                child, parent = self, other
            else:
                child, parent = other, self
            return {
                (Bool,     Bool):     lambda: child.pattern == parent.pattern,
                (Bool,     Int):      lambda: child.pattern == '0|1',
                (Bool,     Float):    lambda: child.pattern == '0|1',
                (Int,      Int):      lambda: True,
                (Int,      Float):    lambda: child.pattern != 'x',
                (Float,    Float):    lambda: True,
                (DateTime, DateTime): lambda: child.pattern == parent.pattern,
                (NumRepr,  NumRepr):  lambda: True,
            }[child.content.__class__, parent.content.__class__]()
        return False

    def validate(self, value):
        if not isinstance(value, str):
            return False
        try:
            content = self.content
            if isinstance(self.content, Bool):
                false, true = self.pattern.split('|', 1)
                value = parse_bool(value, false, true)
            elif isinstance(self.content, Int) or (
                isinstance(self.content, NumRepr) and
                self.content.pattern is Int
            ):
                value = int(value, base=self.int_bases[self.pattern])
            elif isinstance(self.content, Float) or (
                isinstance(self.content, NumRepr) and
                self.content.pattern is Float
            ):
                assert self.pattern == 'f'
                value = float(value)
            elif isinstance(self.content, DateTime):
                value = datetime.strptime(value, self.pattern)
            else:
                assert False
        except ValueError:
            return False
        else:
            return self.content.validate(value)


class NumRepr(Repr):
    __slots__ = ()

    def __str__(self):
        if self.pattern is Int:
            template = 'int of {self.content}'
        elif self.pattern is Float:
            template = 'float of {self.content}'
        else:
            assert False
        return template.format(self=self)

    def __xml__(self):
        if self.pattern is Int:
            return tag.intof(xml(self.content))
        elif self.pattern is Float:
            return tag.floatof(xml(self.content))
        else:
            assert False

    def __add__(self, other):
        if self == other:
            if self.pattern is Float or other.pattern is Float:
                pattern = Float
            else:
                pattern = Int
            return NumRepr(self.content + other.content, pattern)
        return NotImplemented

    def validate(self, value):
        if not isinstance(value, Real):
            return False
        try:
            if isinstance(self.content, DateTime):
                value = datetime.fromtimestamp(value)
            else:
                assert False
        except ValueError:
            return False
        else:
            return self.content.validate(value)


class URL(Str):
    __slots__ = ()

    def __str__(self):
        return 'URL'

    def __xml__(self):
        return tag.url(
            iter(super().__xml__()),
            pattern=None if self.pattern is None else
                    ''.join(str(c) for c in self.pattern)
        )

    def validate(self, value):
        # TODO use urlparse (or split?) and check lots more schemes
        return (
            super().validate(value) and
            value.startswith(('http://', 'https://'))
        )


class Fields(Type):
    __slots__ = ('values',)

    def __init__(self, values):
        self.values = frozenset(values)
        assert all(isinstance(value, Field) for value in self.values)

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __str__(self):
        choices = shorten(
            '|'.join(str(choice) for choice in self),
            width=60, placeholder='...')
        return '<{choices}>'.format(choices=choices)

    def validate(self, value):
        return any(choice.validate(value) for choice in self)


@total_ordering
class Field(Type):
    __slots__ = ('value', 'optional')

    def __init__(self, value, optional=False):
        super().__init__()
        self.value = value
        self.optional = optional

    def __str__(self):
        return repr(self.value) + ('*' if self.optional else '')

    def __xml__(self):
        return tag.key(repr(self.value), optional=self.optional)

    def __add__(self, other):
        if self == other:
            return Field(self.value, self.optional or other.optional)
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Field):
            return self.value < other.value
        return NotImplemented

    def __hash__(self):
        # We define a hash to permit Field to be present in a Fields
        # instance; note that this implies a Field is effectively immutable
        return hash((self.value,))

    def compare(self, other):
        # We deliberately exclude *optional* from consideration here; the
        # only time a Field is compared is during common sub-tree
        # elimination where a key might be mandatory in one sub-set but
        # optional in another
        return super().compare(other) and self.value == other.value

    def validate(self, value):
        return value == self.value


class Value(Type):
    __slots__ = ()

    def __new__(cls):
        # This is a singleton class; all instances are the same
        try:
            return _value
        except NameError:
            return super().__new__(cls)

    def __repr__(self):
        return 'Value()'

    def __str__(self):
        return 'value'

    def __xml__(self):
        return tag.value()

    def validate(self, value):
        return True


class Empty(Type):
    __slots__ = ()

    def __new__(cls):
        # This is a singleton class; all instances are the same
        try:
            return _empty
        except NameError:
            return super().__new__(cls)

    def __repr__(self):
        return 'Empty()'

    def __str__(self):
        return ''

    def __xml__(self):
        return tag.empty()

    def validate(self, value):
        return False


_empty = Empty()
_value = Value()
