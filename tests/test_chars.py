# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

from unittest import mock

import pytest
from lxml.etree import tostring

from structa.chars import *
from structa.xml import xml


def test_char_class_init():
    assert CharClass('abc') == \
        CharClass(['a', 'b', 'c']) == \
        CharClass(('a', 'b', 'c')) == \
        CharClass({'a', 'b', 'c'})
    cc = CharClass('abc')
    assert CharClass(cc) is cc
    with pytest.raises(ValueError):
        CharClass(10)
    with pytest.raises(ValueError):
        CharClass(['abc', 'def', 'a', 'b', 'c'])


def test_char_class_repr():
    assert repr(CharClass('abc')) == "CharClass('abc')"
    assert str(CharClass('')) == '∅'
    assert str(CharClass('f')) == 'f'
    assert str(CharClass('abcd')) == '[a-d]'


def test_char_class_xml():
    assert tostring(xml(CharClass(''))) == b'<pat/>'
    assert tostring(xml(CharClass('a'))) == b'<lit>a</lit>'
    assert tostring(xml(CharClass('abcd'))) == b'<pat>[a-d]</pat>'
    assert tostring(xml(CharClass('0123456789'))) == b'<pat>d</pat>'


def test_char_class_intersection():
    c1 = CharClass('bcdef')
    c2 = CharClass('abcd')
    r = CharClass('bcd')
    assert c1 & c2 == r
    assert c1.intersection(c2) == r
    with pytest.raises(TypeError):
        c1 & 100


def test_char_class_union():
    c1 = CharClass('bcdef')
    c2 = CharClass('abcd')
    r = CharClass('abcdef')
    assert c1 | c2 == r
    assert c1.union(c2) == r
    with pytest.raises(TypeError):
        c1 | 100


def test_char_class_sym_diff():
    c1 = CharClass('bcdef')
    c2 = CharClass('abcd')
    r = CharClass('aef')
    assert c1 ^ c2 == r
    assert c1.symmetric_difference(c2) == r
    with pytest.raises(TypeError):
        c1 ^ 100


def test_char_class_sub():
    c1 = CharClass('bcdef')
    c2 = CharClass('abcd')
    r = CharClass('ef')
    assert c1 - c2 == r
    assert c1.difference(c2) == r
    with pytest.raises(TypeError):
        c1 - 100


def test_any_char_init():
    assert any_char is AnyChar()
    assert AnyChar() is AnyChar()
    with mock.patch('sys.maxunicode', 255):
        assert CharClass(''.join(chr(i) for i in range(256))) is any_char


def test_any_char_hash():
    with mock.patch('sys.maxunicode', 255):
        all_chars = CharClass(''.join(chr(i) for i in range(256)))
        d = {AnyChar(): 'foo'}
        d[all_chars] = 'bar'
        assert len(d) == 1
        assert d[AnyChar()] == 'bar'


def test_any_char_repr():
    assert repr(AnyChar()) == 'AnyChar()'
    assert str(AnyChar()) == '.'


def test_any_char_xml():
    assert tostring(xml(AnyChar())) == b'<pat>.</pat>'


def test_any_char_iter():
    with mock.patch('sys.maxunicode', 255):
        assert len(AnyChar()) == 256
        assert set(AnyChar()) == set(chr(i) for i in range(256))


def test_any_char_equality():
    assert AnyChar() == AnyChar()
    assert not (AnyChar() == CharClass('abcd'))
    assert not (AnyChar() != AnyChar())
    assert AnyChar() != CharClass('abcd')
    assert not (AnyChar() == 100)
    assert AnyChar() != 100


def test_any_char_inequalities():
    assert not AnyChar() < AnyChar()
    assert AnyChar() <= AnyChar()
    assert not AnyChar() > AnyChar()
    assert AnyChar() >= AnyChar()
    assert CharClass('abcd') < AnyChar()
    assert not AnyChar() < CharClass('abcd')
    with pytest.raises(TypeError):
        AnyChar() > 100
    with pytest.raises(TypeError):
        AnyChar() < 100


def test_any_char_intersection():
    assert AnyChar() & CharClass('abcd') == CharClass('abcd')
    assert AnyChar() & AnyChar() == AnyChar()
    with pytest.raises(TypeError):
        AnyChar() & 100


def test_any_char_union():
    assert AnyChar() | AnyChar() == AnyChar()
    assert AnyChar() | CharClass('abcd') == AnyChar()
    with pytest.raises(TypeError):
        AnyChar() | 100


def test_any_char_difference():
    assert AnyChar() - AnyChar() == CharClass('')
    assert CharClass('abcd') - AnyChar() == CharClass('')
    with pytest.raises(ValueError):
        AnyChar() - CharClass('abcd')
    with pytest.raises(TypeError):
        AnyChar() - 100
    with pytest.raises(TypeError):
        100 - AnyChar()
