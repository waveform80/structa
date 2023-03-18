# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import datetime as dt

import pytest

from dateutil.relativedelta import relativedelta
from structa.conversions import *


def test_try_conversion():
    data = range(10)
    str_data = Counter(str(n) for n in data)
    assert try_conversion(str_data, int) == Counter(data)
    str_data[''] = 1
    assert try_conversion(str_data, int, threshold=1) == Counter(data)
    with pytest.raises(ValueError):
        str_data[''] = 4
        try_conversion(str_data, int, threshold=2)
    with pytest.raises(ValueError):
        all_bad = Counter('' for n in range(4))
        try_conversion(all_bad, int, threshold=5)


def test_parse_bool():
    assert parse_bool('0') is False
    assert parse_bool('1') is True
    assert parse_bool('true', false='false', true='true') is True
    assert parse_bool('f', false='f', true='t') is False
    with pytest.raises(ValueError):
        parse_bool('')
    with pytest.raises(ValueError):
        parse_bool('f')


def test_parse_duration():
    assert parse_duration('') == relativedelta(seconds=0)
    assert parse_duration('1 week') == relativedelta(days=7)
    assert parse_duration('1h') == relativedelta(hours=1)
    assert parse_duration('1hrs, 5mins') == relativedelta(hours=1, minutes=5)
    assert parse_duration('60 seconds') == relativedelta(minutes=1)
    assert parse_duration('1s-50ms') == relativedelta(seconds=1, microseconds=-50000)
    with pytest.raises(ValueError):
        parse_duration('foo')


def test_parse_duration_or_timestamp():
    assert parse_duration_or_timestamp('') == relativedelta(seconds=0)
    assert parse_duration_or_timestamp('1 hour 30 minutes') == relativedelta(hours=1, minutes=30)
    assert parse_duration_or_timestamp('-1yr') == relativedelta(years=-1)
    assert parse_duration_or_timestamp('01:30:00') == dt.datetime.today().replace(
        hour=1, minute=30, second=0, microsecond=0)
    assert parse_duration_or_timestamp('2000-01-01 00:00:00') == dt.datetime(2000, 1, 1, 0, 0, 0)
