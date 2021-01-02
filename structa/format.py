from math import log
from itertools import tee
from datetime import datetime


def pairwise(iterable):
    """
    Taken from the recipe in the documentation for :mod:`itertools`.
    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def format_chars(chars, range_sep='-', list_sep=''):
    """
    Given a set of *chars*, returns a compressed string representation
    of all values in the set. For example:

        >>> char_ranges({'a', 'b'})
        'ab'
        >>> char_ranges({'a', 'b', 'c'})
        'a-c'
        >>> char_ranges({'a', 'b', 'c', 'd', 'h'})
        'a-dh'
        >>> char_ranges({'a', 'b', 'c', 'd', 'h', 'i'})
        'a-dh-i'

    *range_sep* and *list_sep* can be optionally specified to customize the
    strings used to separate ranges and lists of ranges respectively.
    """
    # TODO Handle special case of solo range_sep at end and escaping of
    # control chars
    if len(chars) == 0:
        return ''
    elif len(chars) == 1:
        return '{0}'.format(*chars)
    elif len(chars) == 2:
        return '{0}{sep}{1}'.format(*sorted(chars), sep=list_sep)
    else:
        ranges = []
        start = None
        for i, j in pairwise(sorted(chars)):
            if start is None:
                start = i
            if j > chr(ord(i) + 1):
                ranges.append((start, i))
                start = j
        if j == chr(ord(i) + 1):
            ranges.append((start, j))
        else:
            ranges.append((j, j))
        return list_sep.join(
            ('{start}{sep}{finish}' if finish > start else '{start}').format(
                start=start, finish=finish, sep=range_sep)
            for start, finish in ranges
        )


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


def format_repr(self, **override):
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


def format_sample(value):
    try:
        return {
            datetime: lambda: '{0:%Y-%m-%d %H:%M:%S}'.format(value),
            float:    lambda: '{0:.7g}'.format(value),
            int:      lambda: format_int(value),
            bool:     lambda: ('false', 'true')[value],
            str:      lambda: '"{}"'.format(value.replace('"', '""')),
        }[type(value)]()
    except KeyError:
        raise ValueError('invalid type for value {!r}'.format(value))
