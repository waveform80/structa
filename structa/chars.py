import re
import sys

from .format import format_chars


def char_range(start, stop):
    return CharClass({chr(i) for i in range(ord(start), ord(stop) + 1)})


class CharClass(frozenset):
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
            return '[{ranges}]'.format(ranges=format_chars(self))

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

    def __iter__(self):
        for i in range(sys.maxunicode + 1):
            yield chr(i)

    def __len__(self):
        return sys.maxunicode + 1

    def __contains__(self, value):
        return isinstance(value, str) and len(value) == 1

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
