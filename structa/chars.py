# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import sys

from .format import format_chars
from .xml import ElementFactory


tag = ElementFactory()


def char_range(start, stop):
    """
    Returns a :class:`CharClass` containing all the characters from *start* to
    *stop* inclusive (in unicode codepoint order). For example::

        >>> char_range('a', 'c')
        CharClass('abc')
        >>> char_range('0', '9')
        CharClass('0123456789')

    :param str start: The inclusive start point of the range
    :param str stop: The inclusive stop point of the range
    """
    return CharClass({chr(i) for i in range(ord(start), ord(stop) + 1)})


class CharClass(frozenset):
    """
    A descendent of :class:`frozenset` intended to represent a character class
    in a regular expression. Can be instantiated from any iterable of single
    characters (including a :class:`str`).

    All operations of :class:`frozenset` are supported, but return instances of
    :class:`CharClass` instead (and thus, are only valid for operations which
    result in sets containing individual character values). For example::

        >>> abc = CharClass('abc')
        >>> abc
        CharClass('abc')
        >>> ghi = CharClass('ghi')
        >>> abc == ghi
        False
        >>> abc < ghi
        False
        >>> abc | ghi
        CharClass('abcghi')
        >>> abc < abc | ghi
        True
    """
    def __new__(cls, chars):
        if isinstance(chars, CharClass):
            return chars
        elif isinstance(chars, str):
            chars = frozenset(chars)
        elif (
            isinstance(chars, (tuple, list)) and
            all(isinstance(c, str) and len(c) == 1 for c in chars)
        ):
            chars = frozenset(chars)
        elif (
            isinstance(chars, (set, frozenset)) and
            all(isinstance(c, str) and len(c) == 1 for c in chars)
        ):
            pass
        else:
            raise ValueError('CharClass must be a string or a set of chars')
        if len(chars) == sys.maxunicode + 1:
            return AnyChar()
        else:
            return super().__new__(cls, chars)

    def __repr__(self):
        return '{self.__class__.__name__}({chars!r})'.format(
            self=self, chars=''.join(sorted(self)))

    def __str__(self):
        if len(self) == 0:
            return '∅'
        elif len(self) == 1:
            return format_chars(self)
        else:
            try:
                return {
                    oct_digit:   'o',
                    dec_digit:   'd',
                    hex_digit:   'x',
                    ident_first: 'I',
                    ident_char:  'i',
                }[self]
            except KeyError:
                return '[{ranges}]'.format(ranges=format_chars(self))

    def __xml__(self):
        if len(self) == 0:
            return tag.pat()
        elif len(self) == 1:
            return tag.lit(format_chars(self))
        else:
            try:
                return tag.pat({
                    oct_digit:   'o',
                    dec_digit:   'd',
                    hex_digit:   'x',
                    ident_first: 'I',
                    ident_char:  'i',
                }[self])
            except KeyError:
                return tag.pat('[{ranges}]'.format(ranges=format_chars(self)))

    def __and__(self, other):
        result = super().__and__(other)
        if result is NotImplemented:
            return result
        else:
            return self.__class__(result)

    def __or__(self, other):
        result = super().__or__(other)
        if result is NotImplemented:
            return result
        else:
            return self.__class__(result)

    def __xor__(self, other):
        result = super().__xor__(other)
        if result is NotImplemented:
            return result
        else:
            return self.__class__(result)

    def __sub__(self, other):
        result = super().__sub__(other)
        if result is NotImplemented:
            return result
        else:
            return self.__class__(result)

    def union(self, *others):
        return self.__class__(super().union(*others))

    def intersection(self, *others):
        return self.__class__(super().intersection(*others))

    def difference(self, *others):
        return self.__class__(super().difference(*others))

    def symmetric_difference(self, *others):
        return self.__class__(super().symmetric_difference(*others))


class AnyChar:
    """
    A singleton class (all instances are the same) which represents any
    possible character. This is comparable with, and compatible in operations
    with, instances of :class:`CharClass`. For instance::

        >>> abc = CharClass('abc')
        >>> any_ = AnyChar()
        >>> any_
        AnyChar()
        >>> abc < any_
        True
        >>> abc > any_
        False
        >>> abc | any_
        AnyChar()
    """
    _hash = None

    def __new__(cls):
        # Singleton instance
        try:
            return any_char
        except NameError:
            return super().__new__(cls)

    def __repr__(self):
        return 'AnyChar()'

    def __str__(self):
        return '.'

    def __xml__(self):
        return tag.pat('.')

    def __iter__(self):
        for i in range(sys.maxunicode + 1):
            yield chr(i)

    def __len__(self):
        return sys.maxunicode + 1

    def __contains__(self, value):
        return isinstance(value, str) and len(value) == 1

    def __hash__(self):
        if AnyChar._hash is None:
            AnyChar._hash = hash(frozenset(chr(i) for i in range(len(self))))
        return AnyChar._hash

    def __eq__(self, other):
        if isinstance(other, AnyChar):
            return True
        elif isinstance(other, CharClass):
            # Can never be True as CharClass constructor returns AnyChar if
            # length of frozenset of chars is maxunicode + 1
            return False
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, AnyChar):
            return False
        elif isinstance(other, CharClass):
            # See note in __eq__ above
            return True
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, AnyChar):
            return False
        elif isinstance(other, CharClass):
            return len(self) < len(other)
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, AnyChar):
            return False
        elif isinstance(other, CharClass):
            return len(self) > len(other)
        else:
            return NotImplemented

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

    def __and__(self, other):
        if isinstance(other, AnyChar):
            return self
        elif isinstance(other, CharClass):
            return other
        else:
            return NotImplemented

    __rand__ = __and__

    def __or__(self, other):
        if isinstance(other, (AnyChar, CharClass)):
            return self
        else:
            return NotImplemented

    __ror__ = __or__

    def __sub__(self, other):
        if isinstance(other, AnyChar):
            return CharClass(set())
        elif isinstance(other, CharClass):
            raise ValueError('silly subtraction')
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, (AnyChar, CharClass)):
            return CharClass(set())
        else:
            return NotImplemented


oct_digit = CharClass('01234567')
dec_digit = CharClass('0123456789')
hex_digit = dec_digit | CharClass('abcdefABCDEF')
ident_first = char_range('A', 'Z') | char_range('a', 'z') | {'_'}
ident_char = ident_first | dec_digit
any_char = AnyChar()
