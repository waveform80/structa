# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

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


def test_format_sample():
    assert format_sample(1) == '1'
    assert format_sample(-1) == '-1'
    assert format_sample(1000000) == '1.0M'
    assert format_sample(1.0) == '1'
    assert format_sample(0.1) == '0.1'
    assert format_sample(1000000.0) == '1000000'
    assert format_sample(10000000.0) == '1e+07'
    assert format_sample(True) == 'true'
    assert format_sample(False) == 'false'
    assert format_sample(None) == 'null'
    assert format_sample('foo') == '"foo"'
    assert format_sample('"foo"') == '"""foo"""'
    assert format_sample(dt.datetime(2000, 1, 1)) == '2000-01-01 00:00:00'
    with pytest.raises(ValueError):
        format_sample([])


def test_format_timestamp_numrepr():
    assert format_timestamp_numrepr(0, 1) == 'seconds since 1970-01-01'
    assert format_timestamp_numrepr(86400, 86400) == 'days since 1970-01-02'
    assert format_timestamp_numrepr(60, 1) == 'seconds since 1970-01-01T00:01:00'
    assert format_timestamp_numrepr(0, 2) == 'seconds since 1970-01-01 / 2'
    assert format_timestamp_numrepr(0, 0.5) == 'seconds since 1970-01-01 * 2'
