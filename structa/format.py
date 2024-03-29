# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2023 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

from math import log
from itertools import tee
from datetime import datetime, timedelta


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
            f'{start}{range_sep}{finish}' if finish > start else f'{start}'
            for start, finish in ranges
        )


def format_int(i):
    """
    Reduce *i* by some appropriate power of 1000 and suffix it with an
    appropriate Greek qualifier (K for kilo, M for mega, etc). For example::

        >>> format_int(0)
        '0'
        >>> format_int(10)
        '10'
        >>> format_int(1000)
        '1.0K'
        >>> format_int(1600)
        '1.6K'
        >>> format_int(2**32)
        '4.3G'
    """
    suffixes = ('', 'K', 'M', 'G', 'T', 'P')
    try:
        index = min(len(suffixes) - 1, int(log(abs(i), 1000)))
    except ValueError:
        return '0'
    if not index:
        return str(i)
    else:
        return f'{i / 1000 ** index:.1f}{suffixes[index]}'


def format_repr(self, **override):
    """
    Returns a :func:`repr` style string for *self* in the form
    ``class(name=value, name=value, ...)``.

    .. note::

        At present, this function does *not* handle recursive structures
        unlike :func:`reprlib.recursive_repr`.
    """
    args = (
        arg
        for cls in self.__class__.mro() if cls is not object
        for arg in cls.__slots__
    )
    args_str = ', '.join(
        f'{arg}={override.get(arg, repr(getattr(self, arg)))}'
        for arg in args
        if arg not in override
        or override[arg] is not None
    )
    return f'{self.__class__.__name__}({args_str})'


def format_sample(value):
    """
    Format a scalar value for output. The *value* can be a :class:`str`,
    :class:`int`, :class:`float`, :class:`bool`, :class:`~datetime.datetime`,
    or :data:`None`.

    The result is a :class:`str` containing a "nicely" formatted representation
    of the value. For example::

        >>> format_sample(1.0)
        '1'
        >>> format_sample(1.5)
        '1.5'
        >>> format_sample(200000000000)
        '200.0G'
        >>> format_sample(200000000000.0)
        '2e+11'
        >>> format_sample(None)
        'null'
        >>> format_sample(False)
        'false'
        >>> format_sample('foo')
        '"foo"'
        >>> format_sample(datetime.now())
        '2021-08-16 14:05:04'
    """
    try:
        return {
            datetime:   lambda: f'{value:%Y-%m-%d %H:%M:%S}',
            float:      lambda: f'{value:.7g}',
            int:        lambda: format_int(value),
            bool:       lambda: ('false', 'true')[value],
            str:        lambda: '"{}"'.format(value.replace('"', '""')),
            type(None): lambda: 'null',
        }[type(value)]()
    except KeyError:
        raise ValueError(f'invalid type for value {value!r}')


def format_timestamp_numrepr(offset, scale):
    delta = timedelta(seconds=scale)
    simple = {
        timedelta(**{name: 1}): name
        for name in (
            'microseconds',
            'milliseconds',
            'seconds',
            'minutes',
            'hours',
            'days',
            'weeks',
        )
    }
    if offset % 86400:
        epoch = datetime.utcfromtimestamp(offset).isoformat()
    else:
        epoch = datetime.utcfromtimestamp(offset).date().isoformat()
    try:
        return f'{simple[delta]} since {epoch}'
    except KeyError:
        return (
            f'seconds since {epoch} {("*", "/")[scale >= 1]} '
            f'{scale if scale >= 1 else 1 / scale:g}')
