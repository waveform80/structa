# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2018-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

from copy import copy
from numbers import Real
from datetime import datetime
from textwrap import indent, shorten
from functools import partial, total_ordering
from collections.abc import Mapping
from operator import attrgetter

from .collections import Counter, FrozenCounter
from .conversions import some, try_conversion, parse_bool
from .format import format_int, format_repr, format_sample
from .xml import ElementFactory, xml, merge_siblings


tag = ElementFactory()


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
        content = [self._xml_summary()]
        if not self.unique:
            content.append(self._xml_sample())
        return tag.stats(content)

    def _xml_summary(self):
        indexes = {i: '.' for i in range(10)}
        try:
            delta = self.max - self.min
        except TypeError:
            # Cannot calculate a 1d quartile graph for vectors like str; note
            # that we use subtraction for this test because simply testing if
            # min/max are numbers is not sufficient. Timestamps can be
            # subtracted (likewise durations which can furthermore be divided
            # to produce a float), but do not count as numbers in Python's
            # number hierarchy
            graph = ''
        else:
            if delta:
                for n, q in enumerate((self.q1, self.q2, self.q3), start=1):
                    indexes[int(9 * (q - self.min) / delta)] = str(n)
                graph = ''.join(indexes[i] for i in range(10))
            else:
                graph = ''
        return tag.summary(
            tag.min(format_sample(self.min)) if len(self.sample) > 1 else [],
            tag.q1(format_sample(self.q1)) if len(self.sample) > 4 else [],
            tag.q2(format_sample(self.q2)) if len(self.sample) > 2 else [],
            tag.q3(format_sample(self.q3)) if len(self.sample) > 4 else [],
            tag.max(format_sample(self.max)),
            merge_siblings(
                tag.graph(
                    tag.fill(c) if c == '.' else tag.lit(c)
                    for c in graph
                )
            ) if graph else [],
            values=format_int(len(self.sample)),
            count=format_int(self.card),
            unique=self.unique
        )

    def _xml_sample(self):
        if len(self.sample) > 6:
            common = self.sample.most_common()
            return tag.sample(
                [
                    tag.value(format_sample(value),
                              count=format_int(count))
                    for value, count in common[:3]
                ],
                tag.more(),
                [
                    tag.value(format_sample(value),
                              count=format_int(count))
                    for value, count in common[-3:]
                ],
            )
        else:
            return tag.sample(
                tag.value(format_sample(value),
                          count=format_int(count))
                for value, count in self.sample.most_common()
            )

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
        if not isinstance(sample, (Counter, FrozenCounter)):
            sample = FrozenCounter(sample)
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

    def __hash__(self):
        # Hashes have to be equal for items that compare equal but can be equal
        # or different for unequal items. We don't have anything else we can
        # really use here so, just use the type itself.
        #
        # Yes, this is horribly inefficient for hashing but we have some rather
        # complex comparison cases to handle like Value() and Empty() comparing
        # equal to just about everything, plus hashing isn't terribly important
        # for most of the analysis (just a minor part of the merge operation at
        # the end)
        return hash(Type)

    def __eq__(self, other):
        if isinstance(other, Type):
            # This rather strange construction is deliberate; we must *not*
            # return False in the event that the test fails. This permits the
            # equality machinery to try the version other == self test which,
            # in the case of the Value and Empty types can match any other
            # Type.
            #
            # Descendents calling the super-class' implementation should check
            # for "is True" rather relying upon an implicit truth test as
            # bool(NotImplemented) is True
            if isinstance(self, other.__class__):
                return True
            elif isinstance(other, self.__class__):
                return True
        return NotImplemented


class Container(Type):
    __slots__ = ('lengths', 'content', '_similarity_threshold')

    def __init__(self, sample, content=None, similarity_threshold=0.5):
        super().__init__()
        self.lengths = Stats.from_lengths(sample)
        self.content = content
        self._similarity_threshold = similarity_threshold

    @property
    def similarity_threshold(self):
        return self._similarity_threshold

    @similarity_threshold.setter
    def similarity_threshold(self, value):
        # FIXME this propagation should be done externally to permit fine
        # grained control of this property should users require it
        self._similarity_threshold = value
        for item in self.content:
            if isinstance(item, (TupleField, DictField)):
                item = item.value
            if isinstance(item, Container):
                item.similarity_threshold = value

    def __repr__(self):
        return format_repr(self, lengths=None, _similarity_threshold=None)

    def __xml__(self):
        return tag.container(
            tag.content(xml(field) for field in self.content)
                if self.content is not None else [],
            tag.lengths(xml(self.lengths)),
        )

    def __eq__(self, other):
        # The Stats lengths attribute is ignored as it has no bearing on the
        # actual structure itself
        if super().__eq__(other) is True:
            return some(
                (a == b for a, b in self._zip(other)),
                min(len(self.content), len(other.content)) *
                1 - self.similarity_threshold)
        return NotImplemented

    def __add__(self, other):
        # The odd construct of calling self.__eq__(other) instead of testing
        # self == other is deliberate. It ensures that, in the case we're
        # comparing with something like Empty / Value (where our equality test
        # returns NotImplemented), the radd machinery is invoked so when self +
        # other fails, other + self is called and (for example) Empty.__radd__
        # is used instead
        if self.__eq__(other) is True:
            result = copy(self)
            result.lengths = self.lengths + other.lengths
            result.content = [a + b for a, b in self._zip(other)]
            return result
        return NotImplemented

    def _zip(self, other):
        return zip(self.content, other.content)

    def with_content(self, content):
        result = copy(self)
        result.content = content
        return result

    __hash__ = Type.__hash__


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

    def __add__(self, other):
        result = super().__add__(other)
        if isinstance(result, Dict):
            # XXX Is this strictly necessary?
            # FIXME this won't work with all possible keys
            result.content = sorted(result.content, key=attrgetter('key'))
        return result

    def _zip(self, other):
        return zip_dict_fields(self.content, other.content)

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

    __hash__ = Type.__hash__

    def __eq__(self, other):
        if isinstance(other, DictField):
            return (
                super().__eq__(other) is True and
                self.key == other.key and
                self.value is not None and
                other.value is not None and
                self.value == other.value)
        return NotImplemented


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

    def _zip(self, other):
        return zip_tuple_fields(self.content, other.content)

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

    __hash__ = Type.__hash__

    def __eq__(self, other):
        if isinstance(other, TupleField):
            return (
                super().__eq__(other) is True and
                self.index == other.index and
                self.value is not None and
                other.value is not None and
                self.value == other.value)
        return NotImplemented


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

    def __eq__(self, other):
        # The Stats lengths attribute is ignored as it has no bearing on the
        # actual structure itself
        if super().__eq__(other) is True:
            return some(
                (a == b for a, b in
                 zip(self.content, other.content)),
                min(len(self.content), len(other.content)) *
                1 - self.similarity_threshold)
        return NotImplemented

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
        # See notes in Container.__add__
        if self.__eq__(other) is True:
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

    def __eq__(self, other):
        # XXX Should we compare pattern here? Consider case of mistaken octal/
        # dec pattern when it's actually hex in the merge scenario?
        if isinstance(other, Repr):
            return (
                super().__eq__(other) is True and
                self.content == other.content)
        return NotImplemented

    __hash__ = Type.__hash__

    @property
    def values(self):
        return self.content.values


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

    __hash__ = Repr.__hash__

    def __eq__(self, other):
        if not isinstance(other, StrRepr):
            return NotImplemented
        if super().__eq__(other) is not True:
            return False
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


class Field(Type):
    __slots__ = ('value', 'count', 'optional')

    def __init__(self, value, count, optional=False):
        super().__init__()
        assert not isinstance(value, (Dict, List))
        self.value = value
        self.count = count
        self.optional = optional

    def __str__(self):
        return repr(self.value) + ('*' if self.optional else '')

    def __xml__(self):
        return tag.key(repr(self.value), optional=self.optional)

    def __add__(self, other):
        if self == other:
            return Field(self.value, self.count + other.count,
                         self.optional or other.optional)
        return NotImplemented

    __hash__ = Type.__hash__

    def __eq__(self, other):
        # We deliberately exclude *optional* from consideration here; the
        # only time a Field is compared is during common sub-tree
        # elimination where a key might be mandatory in one sub-set but
        # optional in another
        if isinstance(other, Field):
            return (
                super().__eq__(other) is True and
                self.value == other.value)
        return NotImplemented

    def __lt__(self, other):
        # XXX This is largely a fudge. The only reason it is included is to
        # permit Dict to sort multiple DictField entries containing Field keys
        # partly for display purposes, and partly to ease certain comparisons.
        # Because of this it needs to be able to deal with sorting incompatible
        # types like str and int. This is done arbitrarily by string coversion.
        if isinstance(other, Field):
            try:
                return self.value < other.value
            except TypeError:
                return str(self.value) < str(other.value)
        return NotImplemented

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

    __hash__ = Type.__hash__

    def __eq__(self, other):
        if isinstance(other, Type):
            return True
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Type):
            return self
        return NotImplemented

    __radd__ = __add__

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

    __hash__ = Type.__hash__

    def __eq__(self, other):
        if isinstance(other, Type):
            return True
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Field):
            if not other.optional:
                other = copy(other)
                other.optional = True
            return other
        if isinstance(other, Type):
            # XXX Handle changing Field.optional to True
            return other
        return NotImplemented

    __radd__ = __add__

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


def zip_tuple_fields(it1, it2):
    # FIXME what about the empty cases?
    if it1[0].index is not _empty and it2[0].index is not _empty:
        yield from zip(it1, it2)


def zip_dict_fields(it1, it2):
    if it1[0].key is _empty or it2[0].key is _empty:
        pass
    elif it1[0].key is _value:
        for item in it2:
            yield it1[0], item
    elif it2[0].key is _value:
        for item in it1:
            yield item, it2[0]
    else:
        fields1 = {item.key: item for item in it1}
        fields2 = {item.key: item for item in it2}
        all_fields1 = all(isinstance(key, Field) for key in fields1)
        all_fields2 = all(isinstance(key, Field) for key in fields2)
        if all_fields1 == all_fields2:
            for key in fields1.keys() & fields2.keys():
                yield fields1[key], fields2[key]
            for key in fields1.keys() - fields2.keys():
                field2 = DictField(Field(key.value, count=0, optional=True),
                                   _empty)
                yield fields1[key], field2
            for key in fields2.keys() - fields1.keys():
                field1 = DictField(Field(key.value, count=0, optional=True),
                                   _empty)
                yield field1, fields2[key]
        elif all_fields1:
            remaining = fields1.copy()
            for key_type in fields2:
                for key in fields1:
                    if key_type.validate(key.value):
                        yield fields1[key], fields2[key_type]
                        del remaining[key]
            for field1 in remaining.values():
                field2 = DictField(
                    Field(field1.key.value, count=0, optional=True), _empty)
                yield field1, field2
        elif all_fields2:
            remaining = fields2.copy()
            for key_type in fields1:
                for key in fields2:
                    if key_type.validate(key.value):
                        yield fields1[key_type], fields2[key]
                        del remaining[key]
            for field2 in remaining.values():
                field1 = DictField(
                    Field(field2.key.value, count=0, optional=True), _empty)
                yield field1, field2
        else:
            assert False
