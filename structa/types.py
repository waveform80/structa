# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2018-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import math
from copy import copy
from numbers import Real
from datetime import datetime
from textwrap import indent, shorten
from functools import partial, total_ordering
from collections.abc import Mapping
from operator import attrgetter

from .collections import Counter, FrozenCounter
from .conversions import try_conversion, parse_bool
from .format import format_int, format_repr, format_sample
from .xml import ElementFactory, xml, merge_siblings


tag = ElementFactory()


class Stats:
    """
    Stores cardinality, minimum, maximum, and (high) median of a *sample* of
    numeric values (or lengths of strings or containers), along with the
    specified sample of values.

    Typically instances of this class are constructed via the
    :meth:`from_sample` or :meth:`from_lengths` class methods rather than
    directly. However, instances can also be added to other instances to
    generate statistics for the combined *sample* set. Instances may also be
    compared for equality.

    .. attribute:: card
        :type: int

        The number of items in the :attr:`sample` that the statistics were
        calculated from.

    .. attribute:: q1
        :type: int | float | str | datetime.datetime | ...

        The first (lower) quartile of the :attr:`sample`.

    .. attribute:: q2
        :type: int | float | str | datetime.datetime | ...

        The second quartile (aka the :attr:`median`) of the :attr:`sample`.

    .. attribute:: q3
        :type: int | float | str | datetime.datetime | ...

        The third (upper) quartile of the :attr:`sample`.

    .. attribute:: max
        :type: int | float | str | datetime.datetime | ...

        The largest value in the :attr:`sample`.

    .. attribute:: min
        :type: int | float | str | datetime.datetime | ...

        The smallest value in the :attr:`sample`.

    .. attribute:: sample
        :type: structa.collections.FrozenCounter

        The sample data that the statistics were calculated from. This is
        always an instance of :class:`~structa.collections.FrozenCounter`.
    """
    __slots__ = ('sample', 'card', 'min', 'q1', 'q2', 'q3', 'max', 'unique')

    def __init__(self, sample, card, min, q1, q2, q3, max):
        if not isinstance(sample, FrozenCounter):
            assert isinstance(sample, Counter)
            sample = FrozenCounter.from_counter(sample)
        assert min <= q1 <= q2 <= q3 <= max
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
        """
        Given an iterable of *sample* values, which must be of a homogeneous
        comparable type (e.g. :class:`int`, :class:`str`, :class:`float`),
        construct an instance after calculating the minimum, maximum, and
        quartile values of the *sample*.
        """
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
    def from_lengths(cls, sample):
        """
        Given an iterable of *sample* values, which must be of a homogeneous
        compound type (e.g. :class:`str`, :class:`tuple`), construct an
        instance after calculating the :func:`len` of each item of the
        *sample*, and then the minimum, maximum, and quartile values of the
        lengths.
        """
        if isinstance(sample, (Counter, FrozenCounter)):
            lengths = Counter()
            for item, count in sample.items():
                lengths[len(item)] += count
        else:
            lengths = FrozenCounter(len(item) for item in sample)
        return cls.from_sample(lengths)

    @property
    def median(self):
        """
        An alias for the second quartile, :attr:`q2`.
        """
        return self.q2


class Type:
    """
    The abstract base class of all types recognized by structa.

    This class ensures that instances are hashable (can be used as keys in
    dictionaries), have a reasonable :func:`repr` value for ease of use at the
    `REPL`_, can be passed to the :func:`~structa.xml.xml` function.

    However, the most important thing implemented by this base class is the
    equality test which can be used to test whether a given type is
    "compatible" with another type. The base test implemented at this level is
    that one type is compatible with another if one is a sub-class of the
    other.

    Hence, :class:`Str` is compatible with :class:`Str` as they are the same
    class (and hence one is, redundantly, a sub-class of the other). And
    :class:`Int` is compatible with :class:`Float` as it is a sub-class of the
    latter. However :class:`Int` is not compatbile with :class:`Str` as both
    descend from :class:`Scalar` and are siblings rather than parent-child.

    .. _REPL: https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop
    """
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

    @property
    def size(self):
        return 0


class Container(Type):
    """
    Abstract base of all types that can contain other types. Constructed with a
    *sample* of values, and an optional definition of *content*.

    This is the base class of :class:`List`, :class:`Tuple`, and :class:`Dict`.
    Note that it is *not* the base class of :class:`Str` as, although that is a
    compound type, it cannot *contain other types*; structa treats :class:`Str`
    as a scalar type.

    :class:`Container` extends :class:`Type` by permitting instances to be
    added to (compatible, by equality) instances, combining their
    :attr:`content` appropriately.

    .. attribute:: content
        :type: list[Type]

        A list of :class:`Type` descendents representing the content of
        this instance.

    .. attribute:: lengths
        :type: Stats

        The :class:`Stats` of the lengths of the :attr:`sample` values.

    .. attribute:: sample
        :type: [list] | [tuple] | [dict]

        The sample of values that this instance represents.
    """
    __slots__ = ('lengths', 'sample', 'content')

    def __init__(self, sample, content=None):
        super().__init__()
        self.sample = sample
        self.lengths = Stats.from_lengths(sample)
        self.content = content

    def __repr__(self):
        return format_repr(self, sample=None, lengths=None)

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
            return all(a == b for a, b in self._zip(other))
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
            result.sample = self.sample + other.sample
            result.lengths = self.lengths + other.lengths
            result.content = [a + b for a, b in self._zip(other)]
            return result
        return NotImplemented

    def _zip(self, other):
        return zip(self.content, other.content)

    def with_content(self, content):
        """
        Return a new copy of this container with the :attr:`content` replaced
        with *content*.
        """
        result = copy(self)
        result.content = content
        return result

    __hash__ = Type.__hash__

    @property
    def size(self):
        return sum(item.size for item in self.content) + 1


class Dict(Container):
    """
    Represents mappings (or dictionaries).

    This concrete refinement of :class:`Container` uses :class:`DictField`
    instances in its :attr:`~Container.content` list.

    In the case that a mapping is analyzed as a "record" mapping (of fields to
    values), the :attr:`~Container.content` list will contain one or more
    :class:`DictField` instances, for which the :attr:`~DictField.key`
    attribute(s) will be :class:`Field` instances.

    However, if the mapping is analyzed as a "table" mapping (of keys to
    records), the :attr:`~Container.content` list will contain a single
    :class:`DictField` instance mapping the key's type to the value structure.
    """
    __slots__ = ('similarity_threshold',)

    def __init__(self, sample, content=None, *, similarity_threshold=0.5):
        super().__init__(sample, content)
        self.similarity_threshold = similarity_threshold

    def __repr__(self):
        return format_repr(self, sample=None, lengths=None,
                           similarity_threshold=None)

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
        # See notes in Container.__add__
        if self.__eq__(other) is True:
            assert self.content, 'empty Dict.content during Dict.__add__'
            # Dict.__add__ has one special case. When one side of the addition
            # has Field keys, and the other side *doesn't*, but equality is
            # still there because, say, all the fields are strings and the
            # other side is a Str, then we need to sum all the keys together
            # rather than piecemeal, and mark the values as needing a re-match
            # at the analyzer level
            self_fields = isinstance(self.content[0].key, Field)
            other_fields = isinstance(other.content[0].key, Field)
            if self_fields != other_fields:
                result = copy(self)
                result.sample = self.sample + other.sample
                result.lengths = self.lengths + other.lengths
                if self_fields:
                    assert len(other.content) == 1
                    key = sum(
                        [f.key for f in self.content],
                        other.content[0].key)
                else:
                    assert len(self.content) == 1
                    key = sum(
                        [f.key for f in other.content],
                        self.content[0].key)
                value = Redo(
                    sum((list(f.value.sample) for f in self.content), []) +
                    sum((list(f.value.sample) for f in other.content), []))
                result.content = [DictField(key, value)]
            else:
                result = super().__add__(other)
                result.content = sorted(result.content, key=attrgetter('key'))
            return result
        return NotImplemented

    def _zip(self, other):
        # XXX What about other.similarity_threshold? It's not variable
        # currently but worth considering for future
        return zip_dict_fields(self.content, other.content,
                               similarity_threshold=self.similarity_threshold)

    def validate(self, value):
        """
        Validate that *value* (which must be a :class:`dict`) matches the
        analyzed mapping structure.

        :raises TypeError: if *value* is not a :class:`dict`
        """
        if not isinstance(value, dict):
            raise TypeError('{value!r} is not a dictionary'.format(value=value))
        # XXX Also needs refining for keys present/subordinate structures


class DictField(Type):
    """
    Represents a single mapping within a :class:`Dict`, from the :attr:`key` to
    its corresponding :attr:`value`. For example, a :class:`Field` of a record
    mapping to some other type, or a generic :class:`Str` mapping to an
    :class:`Int` value.

    .. attribute:: key
        :type: Type

        The :class:`Type` descendent representing a single key in the mapping.
        This is usually a :class:`Scalar` descendent, or a :class:`Field`.

    .. attribute:: value
        :type: Type

        The :class:`Type` descendent representing a value in the mapping.
    """
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

    @property
    def size(self):
        return self.key.size + self.value.size


class Tuple(Container):
    """
    Represents sequences of heterogeneous types (typically tuples).

    This concrete refinement of :class:`Container` uses :class:`TupleField`
    instances in its :attr:`~Container.content` list.

    Tuples are typically the result of an analysis of some homogeneous outer
    sequence (usually a :class:`List` though sometimes a :class:`Dict`) that
    contains heterogeneous sequences (the :class:`Tuple` instance).
    """
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
        """
        Validate that *value* (which must be a :class:`tuple`) matches the
        analyzed mapping structure.

        :raises TypeError: if *value* is not a :class:`tuple`
        :raises ValueError: if *value* is not within the length limits of the
                            sampled values
        """
        if not isinstance(value, tuple):
            raise TypeError('{value!r} is not a tuple'.format(value=value))
        if not self.lengths.min <= len(value) <= self.lengths.max:
            raise ValueError(
                '{value!r} is not between {self.lengths.min} and '
                '{self.lengths.max} elements in length'.format(
                    value=value, self=self))


class TupleField(Type):
    """
    Represents a single field within a :class:`Tuple`, with the :attr:`index`
    (an integer number) and its corresponding :attr:`value`.

    .. attribute:: index
        :type: int

        The index of the field within the tuple.

    .. attribute:: value
        :type: Type

        The :class:`Type` descendent representing a value in the tuple.
    """
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

    @property
    def size(self):
        return self.index.size + self.value.size


class List(Container):
    """
    Represents sequences of homogeneous types. This only ever has a single
    :class:`Type` descendent in its :attr:`~Container.content` list.
    """
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
            return all(a == b for a, b in zip(self.content, other.content))
        return NotImplemented

    def validate(self, value):
        """
        Validate that *value* (which must be a :class:`list`) matches the
        analyzed mapping structure.

        :raises TypeError: if *value* is not a :class:`list`
        """
        if not isinstance(value, list):
            raise TypeError('{value!r} is not a list'.format(value=value))


class sources_list(list):
    pass


class SourcesList(List):
    pass


class Scalar(Type):
    """
    Abstract base of all types that cannot contain other types. Constructed
    with a *sample* of values.

    This is the base class of :class:`Float` (from which :class:`Int` and then
    :class:`Bool` descend), :class:`Str`, and :class:`DateTime`.

    .. attribute:: values
        :type: Stats

        The :class:`Stats` of the :attr:`sample` values.
    """
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

    @property
    def sample(self):
        """
        A sequence of the sample values that the instance was constructed from
        (this will not be the original sequence, but one derived from that).
        """
        return self.values.sample.elements()

    @property
    def size(self):
        return 1


class Float(Scalar):
    """
    Represents scalar floating-point values in datasets. Constructed with a
    *sample* of values.
    """
    __slots__ = ()

    @classmethod
    def from_strings(cls, sample, pattern, bad_threshold=0):
        """
        Class method for constructing an instance wrapped in a :class:`StrRepr`
        to indicate a string representation of a set of floating-point values.
        Constructed with an *sample* of strings, a *pattern* (which currently
        must simply be "f"), and a *bad_threshold* of values which are
        permitted to fail conversion.
        """
        return StrRepr(
            cls(try_conversion(sample, float, bad_threshold)),
            pattern=pattern)

    def __str__(self):
        return 'float range={min:.7g}..{max:.7g}'.format(
            min=self.values.min, max=self.values.max)

    def __xml__(self):
        return tag.float(iter(super().__xml__()))

    def validate(self, value):
        """
        Validate that *value* (which must be a :class:`float`) lies within the
        range of sampled values.

        :raises TypeError: if *value* is not a :class:`float`
        :raises ValueError: if *value* is outside the range of sampled values
        """
        if not isinstance(value, float):
            raise TypeError('{value!r} is not a float'.format(value=value))
        if not self.values.min <= value <= self.values.max:
            raise ValueError(
                '{value!r} is not between {self.values.min!r} and '
                '{self.values.max!r}'.format(self=self, value=value))


class Int(Float):
    """
    Represents scalar integer values in datasets. Constructed with a *sample*
    of values.
    """
    __slots__ = ()

    # NOTE: Int is a subclass of Float partly to provide a rough immitation of
    # Python's "numeric tower" (see the numbers module) in permitting an Int
    # pattern to compare equal to a Float pattern for the purposes of merging

    @classmethod
    def from_strings(cls, sample, pattern, bad_threshold=0):
        """
        Class method for constructing an instance wrapped in a :class:`StrRepr`
        to indicate a string representation of a set of integer values.
        Constructed with an *sample* of strings, a *pattern* (which may be "d",
        "o", or "x" to represent the base used in the string representation),
        and a *bad_threshold* of values which are permitted to fail conversion.
        """
        base = {
            'o': 8,
            'd': 10,
            'x': 16,
        }[pattern]
        return StrRepr(
            cls(try_conversion(
                sample, partial(int, base=base), bad_threshold)),
            pattern=pattern)

    def __str__(self):
        return 'int range={min}..{max}'.format(
            min=format_int(self.values.min),
            max=format_int(self.values.max)
        )

    def __xml__(self):
        return tag.int(iter(super().__xml__()))

    def validate(self, value):
        """
        Validate that *value* (which must be an :class:`int`) lies within the
        range of sampled values.

        :raises TypeError: if *value* is not a :class:`int`
        :raises ValueError: if *value* is outside the range of sampled values
        """
        if not isinstance(value, int):
            raise TypeError('{value!r} is not an int'.format(value=value))
        if not self.values.min <= value <= self.values.max:
            raise ValueError(
                '{value!r} is not between {self.values.min!r} and '
                '{self.values.max!r}'.format(self=self, value=value))


class Bool(Int):
    """
    Represents scalar boolean values in datasets. Constructed with a *sample*
    of values.
    """
    __slots__ = ()

    # NOTE: Bool is a subclass of Int; see note in Int for reasons

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        """
        Class method for constructing an instance wrapped in a :class:`StrRepr`
        to indicate a string representation of a set of booleans. Constructed
        with an *sample* of strings, a *pattern* (which is a string of the form
        "false|true", i.e. the expected string representations of the
        :data:`False` and :data:`True` values separated by a bar), and a
        *bad_threshold* of values which are permitted to fail conversion.
        """
        # XXX Urgh ... shouldn't this be a tuple? That would keep the
        # prototype the same; but is there a reason a pattern has to be a str?
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
        """
        Validate that *value* is an :class:`int` (with the value 0 or 1), or a
        :class:`bool`. Raises :exc:`TypeError` or :exc:`ValueError` in the
        event that *value* fails to validate.

        :raises TypeError: if *value* is not a :class:`bool` or :class:`int`
        :raises ValueError: if *value* is an :class:`int` that is not 0 or 1
        """
        if isinstance(value, bool):
            pass
        elif isinstance(value, int):
            if not value in (0, 1):
                raise ValueError('{value!r} is not 0 or 1'.format(value=value))
        else:
            raise TypeError(
                '{value!r} is not a bool or int'.format(value=value))


class DateTime(Scalar):
    """
    Represents scalar timestamps (a date, and a time) in datasets. Constructed
    with a *sample* of values.
    """
    __slots__ = ()

    # NOTE: There are no circumstances in Python where a datetime instance can
    # successfully compare equal to a float, in contrast to the fact that False
    # == 0 == 0.0, so DateTime simply derives from Scalar

    @classmethod
    def from_strings(cls, iterable, pattern, bad_threshold=0):
        """
        Class method for constructing an instance wrapped in a :class:`StrRepr`
        to indicate a string representation of a set of timestamps.

        Constructed with an *sample* of strings, a *pattern* (which must be
        compatible with :meth:`datetime.datetime.strptime`), and a
        *bad_threshold* of values which are permitted to fail conversion.
        """
        conv = lambda s: datetime.strptime(s, pattern)
        return StrRepr(
            cls(try_conversion(iterable, conv, bad_threshold)),
            pattern=pattern)

    @classmethod
    def from_numbers(cls, pattern):
        """
        Class method for constructing an instance wrapped in a :class:`NumRepr`
        to indicate a numeric representation of a set of timestamps (e.g. day
        offset from the UNIX epoch).

        Constructed with an *sample* of number, a *pattern* (which can be a
        :class:`StrRepr` instance if the numbers are themselves represented as
        strings, otherwise must be the :class:`Int` or :class:`Float` instance
        representing the numbers), and a *bad_threshold* of values which are
        permitted to fail conversion.
        """
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
        """
        Validate that *value* (which must be a :class:`~datetime.datetime`)
        lies within the range of sampled values.

        :raises TypeError: if *value* is not a :class:`datetime.datetime`
        :raises ValueError: if *value* is outside the range of sampled values
        """
        if not isinstance(value, datetime):
            raise TypeError('{value!r} is not a datetime'.format(value=value))
        if not self.values.min <= value <= self.values.max:
            raise ValueError(
                '{value:%Y-%m-%d %H:%M:%S} is not between '
                '{self.values.min:%Y-%m-%d %H:%M:%S} and '
                '{self.values.max:%Y-%m-%d %H:%M:%S}'.format(
                    self=self, value=value))


class Str(Scalar):
    """
    Represents string values in datasets. Constructed with a *sample* of
    values, and an optional *pattern* (a sequence of
    :class:`~structa.chars.CharClass` instances indicating which characters are
    valid at which position in fixed-length strings).

    .. attribute:: lengths
        :type: Stats

        The :class:`Stats` of the lengths of the :attr:`sample` values.

    .. attribute:: pattern
        :type: [structa.chars.CharClass]

        :data:`None` if the string is variable length or has no discernable
        pattern to its values. Otherwise a sequence of
        :class:`~structa.chars.CharClass` instances indicating the valid
        characters at each position of the string.
    """
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
        # See notes in Container.__add__
        if self.__eq__(other) is True:
            if (
                self.pattern is None or other.pattern is None or
                len(self.pattern) != len(other.pattern)
            ):
                # XXX We can do better here
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
        """
        Validate that *value* (which must be a :class:`str`) lies within the
        range of sampled values and, if :attr:`pattern` is not :data:`None`,
        that it matches the pattern stored there.

        :raises TypeError: if *value* is not a :class:`str`
        :raises ValueError: if *value* is outside the range of sampled values
                            or deviates from the given :attr:`pattern`
        """
        if not isinstance(value, str):
            raise TypeError('{value!r} is not a str'.format(value=value))
        if not self.values.min <= value <= self.values.max:
            raise ValueError(
                '{value!r} is not between {self.values.min!r} and '
                '{self.values.max!r}'.format(self=self, value=value))
        if self.pattern is not None:
            for c1, c2 in zip(value, self.pattern):
                if c1 not in c2:
                    pattern = ''.join(str(c) for c in self.pattern)
                    raise ValueError(
                        '{value!r} does not match {pattern}'.format(
                            value=value,
                            pattern=shorten(pattern, width=60,
                                            placeholder='...')))


class Repr(Type):
    """
    Abstract base class for representations (string, numeric) of other types.
    Parent of :class:`StrRepr` and :class:`NumRepr`.

    .. attribute:: content
        :type: Type

        The :class:`Type` that this instance is a representation of. For
        example, a string representation of integer numbers would be
        represented by a :class:`StrRepr` instance with :attr:`content` being a
        :class:`Int` instance.

    .. attribute:: pattern
        :type: str | Type | None

        Particulars of the representation. For example, in the case of
        string representations of integers, this is a string indicating the
        base ("o", "d", "x"). In the case of a numeric representation of a
        datetime, this is the :class:`Type` (:class:`Int` or :class:`Float`)
        of the values.
    """
    __slots__ = ('content', 'pattern')

    def __init__(self, content, pattern=None):
        super().__init__()
        self.content = content
        # XXX pattern is horribly confusing, type-wise. Should we refine this?
        # Perhaps it should always be a Type descendent (but then how do we
        # encode base for str-repr-of-int, etc.)
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

    @property
    def size(self):
        return 1


class StrRepr(Repr):
    """
    A string representation of an inner type. Typically used to wrap
    :class:`Int`, :class:`Float`, :class:`Bool`, or :class:`DateTime`. Descends
    from :class:`Repr`.
    """
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
        # XXX What about string rep of bool 'x' == string rep of bool 'y' where
        # actual value is string x|y?
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
            raise TypeError('{value!r} is not a str'.format(value=value))
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
            assert False, (
                'validating str-repr of {self.content!r}'.format(self=self))
        self.content.validate(value)


class NumRepr(Repr):
    """
    A numeric representation of an inner type. Typically used to wrap
    :class:`DateTime`. Descends from :class:`Repr`.
    """
    __slots__ = ()

    def __str__(self):
        if self.pattern is Int:
            template = 'int of {self.content}'
        elif self.pattern is Float:
            template = 'float of {self.content}'
        else:
            assert False, 'str(num-repr) of {self.content!r}'.format(self=self)
        return template.format(self=self)

    def __xml__(self):
        if self.pattern is Int:
            return tag.intof(xml(self.content))
        elif self.pattern is Float:
            return tag.floatof(xml(self.content))
        else:
            assert False, 'xml(num-repr) of {self.content!r}'.format(self=self)

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
            raise TypeError('{value!r} is not a number'.format(value=value))
        if isinstance(self.content, DateTime):
            value = datetime.fromtimestamp(value)
        else:
            assert False, (
                'validating num-repr of {self.content!r}'.format(self=self))
        self.content.validate(value)


class URL(Str):
    """
    A specialization of :class:`Str` for representing URLs. Currently does
    little more than trivial validation of the scheme.
    """
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
        """
        Validate that *value* starts with "http://" or "https://"

        :raises ValueError: if *value* does not start with a valid scheme
        """
        super().validate(value)
        # TODO use urlparse (or split?) and check lots more schemes
        if not value.startswith(('http://', 'https://')):
            raise ValueError('{value!r} is not a URL'.format(value=value))


class Fields(Type):
    """
    Internally used to represent all possible fields of a mapping during the
    first phase of analysis. Should never appear in analysis reuslts, however.
    """
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
        for choice in self:
            try:
                choice.validate(value)
            except (TypeError, ValueError) as exc:
                last_exc = exc
            else:
                return
        raise last_exc


class Field(Type):
    """
    Represents a single key in a :class:`DictField` mapping. This is used by
    the analyzer when it decides a mapping represents a "record" (a mapping of
    fields to values) rather than a "table" (a mapping of keys to records).

    Constructed with the *value* of the key, the *count* of mappings that the
    key appears in, and a flag indicating if the key is *optional* (defaults to
    :data:`False` for mandatory).

    .. attribute:: value
        :type: str | int | float | tuple | ...

        The value of the key.

    .. attribute:: count
        :type: int

        The number of mappings that the key belongs to.

    .. attribute:: optional
        :type: bool

        If :data:`True`, the key may be ommitted from certain mappings in the
        data. If :data:`False` (the default), the key always appears in the
        owning mapping.
    """
    __slots__ = ('value', 'count', 'optional')

    def __init__(self, value, count, optional=False):
        # XXX Field values must (by definition) be immutable; we should enforce
        # this. hash()->TypeError is probably a reasonable proxy for this
        super().__init__()
        assert not isinstance(value, (Dict, List))
        self.value = value
        self.count = count
        self.optional = optional

    def __str__(self):
        return repr(self.value) + ('*' if self.optional else '')

    def __xml__(self):
        return tag.key(repr(self.value), optional=self.optional)

    __hash__ = Type.__hash__

    def __eq__(self, other):
        if isinstance(other, Field):
            # We deliberately exclude *optional* from consideration here; the
            # only time a Field is compared is during common sub-tree
            # elimination where a key might be mandatory in one sub-set but
            # optional in another
            return (
                super().__eq__(other) is True and
                self.value == other.value)
        elif isinstance(other, Type):
            # When comparing a Field against another Type we're only interested
            # in whether the field is mergeable against that type. For example,
            # the cast where one mapping has fewer than field_threshold entries
            # and is treated as a record, while a sibling mapping has more than
            # field_threshold entries and is treated as a table (keyed by str).
            # In this case the Field entries must be successfully comparable to
            # Str
            try:
                other.validate(self.value)
            except (TypeError, ValueError) as exc:
                return False
            else:
                return True
        return NotImplemented

    def __add__(self, other):
        # See notes in Container.__add__
        if self.__eq__(other) is True:
            if isinstance(other, Field):
                return Field(self.value, self.count + other.count,
                             self.optional or other.optional)
            elif isinstance(other, Scalar):
                # In the case (discussed in Field.__eq__ above) where we're
                # being merged with (say) a Str instance, the result is simply
                # a new Str instance with the combined samples
                result = copy(other)
                sample = FrozenCounter({self.value: self.count})
                result.values = other.values + Stats.from_sample(sample)
                return result
            elif isinstance(other, Tuple):
                result = copy(other)
                sample = FrozenCounter({len(self.value): self.count})
                result.lengths = other.lengths + Stats.from_sample(sample)
                return result
        return NotImplemented

    __radd__ = __add__

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
        """
        Validates that *value* matches the expected key value.

        :raises ValueError: if *value* does not match the expected value
        """
        if not value == self.value:
            raise ValueError(
                '{value!r} does not equal {self.value!r}'.format(
                    self=self, value=value))

    @property
    def size(self):
        return 1


class Value(Type):
    """
    A descendent of :class:`Type` that represents any arbitrary type at all.
    This is used when the analyzer comes across a container of a multitude of
    (incompatible) types, e.g. a list of both strings and integers.

    It compares equal to all other types, and when added to other types, the
    result is a new :class:`Value` instance.
    """
    __slots__ = ('sample',)

    def __init__(self, sample):
        self.sample = sample

    __hash__ = Type.__hash__

    def __eq__(self, other):
        if isinstance(other, Type):
            return True
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Type):
            result = copy(self)
            result.sample = list(self.sample) + list(other.sample)
            return result
        return NotImplemented

    __radd__ = __add__

    def __repr__(self):
        return 'Value()'

    def __str__(self):
        return 'value'

    def __xml__(self):
        return tag.value()

    def validate(self, value):
        """
        Trivial validation; always passes, never raises an exception.
        """
        pass

    @property
    def size(self):
        return 1


class Redo(Value):
    """
    Internally used by the analyzer during the merge phase to indicate a
    set of values that need to be re-analyzed post-merge.
    """
    __slots__ = ()

    def __repr__(self):
        return 'Redo({})'.format(self.sample)

    def __str__(self):
        assert False, 'str of Redo'

    def __xml__(self):
        assert False, 'xml of Redo'


class Empty(Type):
    """
    A descendent of :class:`Type` that represents a container with no content.
    For example, if the analyzer comes across a field which always contains
    an empty list, it would be represented as a :class:`List` instance where
    :attr:`List.content` was a sequence containing an :class:`Empty` instance.

    It compares equal to all other types, and when added to other types, the
    result is the other type. This allows the merge phase to combine empty
    lists with a list of integers found at the same level, for example.
    """
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
            return other
        return NotImplemented

    __radd__ = __add__

    def __repr__(self):
        return 'Empty()'

    def __str__(self):
        return ''

    def __xml__(self):
        return tag.empty()

    @property
    def sample(self):
        return []

    def validate(self, value):
        """
        Trivial validation; always passes.

        .. note::

            This counter-intuitive behaviour is because the :class:`Empty`
            value indicates a lack of type-information rather than a definitely
            empty container (after all, there's usually little sense in having
            a container field which will always be empty in most hierarchical
            structures).

            The way this differs from :class:`Value` is in the additive action.
        """
        pass


_empty = Empty()


def zip_tuple_fields(it1, it2):
    indexes1 = {item.index: item for item in it1}
    indexes2 = {item.index: item for item in it2}
    common_indexes = indexes1.keys() & indexes2.keys()
    for index in common_indexes:
        yield indexes1[index], indexes2[index]
    for index in indexes1.keys() - indexes2.keys():
        yield indexes1[index], TupleField(_empty, _empty)
    for index in indexes2.keys() - indexes1.keys():
        yield TupleField(_empty, _empty), indexes2[index]


def zip_dict_fields(it1, it2, *, similarity_threshold=1):
    fields1 = {item.key: item for item in it1}
    fields2 = {item.key: item for item in it2}
    all_fields1 = all(isinstance(key, Field) for key in fields1)
    all_fields2 = all(isinstance(key, Field) for key in fields2)
    if all_fields1 and all_fields2:
        common_keys = fields1.keys() & fields2.keys()
        minimum_common = similarity_threshold * min(len(fields1), len(fields2))
        if len(common_keys) >= math.ceil(minimum_common):
            for key in common_keys:
                yield fields1[key], fields2[key]
            for key in fields1.keys() - fields2.keys():
                yield fields1[key], DictField(_empty, _empty)
            for key in fields2.keys() - fields1.keys():
                yield DictField(_empty, _empty), fields2[key]
        else:
            for field1 in fields1.values():
                yield field1, None
            for field2 in fields2.values():
                yield None, field2
    elif all_fields1 and not all_fields2:
        assert len(fields2) == 1
        for key_type in fields2:
            for key in fields1:
                yield fields1[key], fields2[key_type]
    elif not all_fields1 and all_fields2:
        assert len(fields1) == 1
        for key_type in fields1:
            for key in fields2:
                yield fields1[key_type], fields2[key]
    else: # if not all_fields1 and not all_fields2:
        assert len(fields1) == len(fields2) == 1
        yield it1[0], it2[0]
