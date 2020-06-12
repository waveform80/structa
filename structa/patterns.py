from math import log
from datetime import datetime
from collections import namedtuple
from textwrap import indent, shorten

from .chars import Digit, AnyChar


def format_int(i):
    """
    Reduce *i* by some appropriate power of 2 and suffix it with an appropriate
    Greek qualifier (K for kilo, M for mega, etc.)
    """
    suffixes = ('', 'K', 'M', 'G', 'T', 'P')
    try:
        index = min(len(suffixes) - 1, int(log(abs(i), 2) // 10))
    except ValueError:
        return '0'
    if not index:
        return str(i)
    else:
        return '{value:.1f}{suffix}'.format(
            value=(i / 2 ** (index * 10)),
            suffix=suffixes[index])


class Stats(namedtuple('Stats', ('card', 'min', 'max', 'median'))):
    """
    Return the minimum, maximum, and (rough) median of the integer
    *values* list.
    """
    def __new__(cls, values):
        values = sorted(values)
        return super().__new__(
            cls, len(values), values[0], values[-1], values[len(values) // 2])


class Dict(namedtuple('Dict', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        return super().__new__(cls, Stats(sample), pattern)

    def __str__(self):
        if self.pattern is None:
            return '{}'
        else:
            elems = ', '.join('{key}: {value}'.format(key=key, value=value)
                              for key, value in self.pattern.items())
            if '\n' in elems or len(elems) > 60:
                elems = ',\n'.join('{key}: {value}'.format(key=key, value=value)
                                   for key, value in self.pattern.items())
                return '{{\n{elems}\n}}'.format(elems=indent(elems, '   '))
            else:
                return '{{{elems}}}'.format(elems=elems)

    def validate(self, value):
        return isinstance(value, dict)


class List(namedtuple('List', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        return super().__new__(cls, Stats(sample), pattern)

    def __str__(self):
        if self.pattern is None:
            return '[]'
        else:
            elems = ', '.join(str(item) for item in self.pattern)
            if '\n' in elems or len(elems) > 60:
                elems = ',\n'.join(str(item) for item in self.pattern)
                return '[\n{elems}\n]'.format(elems=indent(elems, '   '))
            else:
                return '[{elems}]'.format(elems=elems)

    def validate(self, value):
        return isinstance(value, list)


class DateTime(namedtuple('DateTime', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        if pattern is float:
            sample = (datetime.fromtimestamp(float(value))
                      for value in sample)
        elif pattern is not None:
            sample = (datetime.strptime(value, pattern)
                      for value in sample)
        return super().__new__(cls, Stats(sample), pattern)

    def __str__(self):
        pattern = {
            None: ' ',
            float: ' %f',
        }.get(self.pattern, ' ' + repr(self.pattern))
        return '<datetime{pattern}{min}..{max}>'.format(
            pattern=pattern,
            min=self.stats.min.replace(microsecond=0),
            max=self.stats.max.replace(microsecond=0))

    def validate(self, value):
        if self.pattern is None:
            return isinstance(value, datetime)
        try:
            datetime.strptime(value, self.pattern)
        except ValueError:
            return False
        else:
            return True


class Str(namedtuple('Str', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        lengths = (len(value) for value in sample)
        return super().__new__(cls, Stats(lengths), pattern)

    def __str__(self):
        if self.pattern is None:
            return '<str>'
        else:
            pattern = ''.join(
                c if isinstance(c, str) else c.display
                for c in self.pattern)
            return '<str {pattern}>'.format(
                pattern=shorten(pattern, width=60, placeholder='...'))

    def validate(self, value):
        return (
            isinstance(value, str) and
            self.stats.min <= len(value) <= self.stats.max
        )


class Int(namedtuple('Int', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, base=None):
        if base is not None:
            sample = (int(value, base) for value in sample)
        return super().__new__(cls, Stats(sample), base)

    def __str__(self):
        pattern = {
            None: ' ',
            8:  ' oct-str ',
            10: ' dec-str ',
            16: ' hex-str ',
        }.get(self.pattern, ' ??? ')
        return '<int{pattern}{min}..{max}>'.format(
            pattern=pattern,
            min=format_int(self.stats.min),
            max=format_int(self.stats.max))

    def validate(self, value):
        return (
            isinstance(value, int) and
            self.stats.min <= value <= self.stats.max
        )


class Float(namedtuple('Float', ('stats', 'pattern'))):
    __slots__ = ()

    def __new__(cls, sample, pattern=None):
        if pattern is not None:
            sample = (float(value) for value in sample)
        return super().__new__(cls, Stats(sample), pattern)

    def __str__(self):
        return '<float {min:.1f}..{max:.1f}>'.format(
            min=self.stats.min, max=self.stats.max)


class Bool(namedtuple('Bool', ('card',))):
    __slots__ = ()

    def __str__(self):
        return '<bool>'

    def validate(self, value):
        return (
            isinstance(value, bool) or
            (isinstance(value, int) and value in (0, 1))
        )


class URL:
    __slots__ = ()

    def __str__(self):
        return '<URL>'

    def __repr__(self):
        return 'URL()'

    def validate(self, value):
        return value.startswith(('http://', 'https://'))


class Choices(set):
    def __str__(self):
        if len(self) == 1:
            for choice in self:
                return str(choice.value)
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
        return '<value>'

    def __repr__(self):
        return 'Value()'

    def __call__(self):
        return self

    def validate(self, value):
        return True


class Empty:
    __slots__ = ()

    def __str__(self):
        return ''

    def __repr__(self):
        return 'Empty()'

    def __call__(self):
        return self

    def validate(self, value):
        return len(value) == 0


# Singletons
Value = Value()
Empty = Empty()
