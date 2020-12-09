import datetime as dt
from collections import namedtuple, Counter

import pytest

from structa.chars import CharClass
from structa.format import *


def test_format_chars():
    assert format_chars(set()) == ''
    assert format_chars({'a'}) == 'a'
    assert format_chars(CharClass('ab')) == 'ab'
    assert format_chars(CharClass('abcd')) == 'a-d'
    assert format_chars(CharClass('abchij')) == 'a-ch-j'
    assert format_chars(CharClass('abcdh')) == 'a-dh'


def test_format_int():
    assert format_int(0) == '0'
    assert format_int(1) == '1'
    assert format_int(999) == '999'
    assert format_int(-999) == '-999'
    assert format_int(1000) == '1.0K'
    assert format_int(-1000) == '-1.0K'
    assert format_int(999900) == '999.9K'
    assert format_int(1000000) == '1.0M'


def test_format_repr():
    class A:
        __slots__ = ('foo', 'bar')
        def __init__(self, foo, bar=2):
            self.foo = foo
            self.bar = bar
        def __repr__(self):
            return format_repr(self)

    assert repr(A(1)) == 'A(foo=1, bar=2)'
