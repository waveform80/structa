# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import io
import os
import sys
import json
import random
import datetime as dt
from fractions import Fraction

import pytest
from dateutil.relativedelta import relativedelta

from structa.types import *
from structa.ui import cli


def test_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(['-h'])
    assert exc_info.value.args[0] == 0  # return code 0
    captured = capsys.readouterr()
    assert captured.out.lstrip().startswith('usage: ')


def test_min_timestamp():
    assert cli.min_timestamp('2000-01-01') == dt.datetime(2000, 1, 1)
    assert cli.min_timestamp('10 years') == cli._start - relativedelta(years=10)


def test_max_timestamp():
    assert cli.max_timestamp('2050-01-01') == dt.datetime(2050, 1, 1)
    assert cli.max_timestamp('10 years') == cli._start + relativedelta(years=10)


def test_timestamps():
    assert cli.timestamps('unix') == (
        dt.timedelta(seconds=1), dt.datetime(1970, 1, 1))
    assert cli.timestamps('excel') == (
        dt.timedelta(days=1), dt.datetime(1899, 12, 30))
    assert cli.timestamps('2015-03-31 00:00:00') == (
        dt.timedelta(seconds=1), dt.datetime(2015, 3, 31))
    assert cli.timestamps('milliseconds since 1900-01-01') == (
        dt.timedelta(milliseconds=1), dt.datetime(1900, 1, 1))
    with pytest.raises(ValueError):
        cli.timestamps('')
    with pytest.raises(ValueError):
        cli.timestamps('years since 1970-01-01')


def test_num():
    assert cli.num('1') == 1
    assert cli.num('1/2') == Fraction(1, 2)
    assert cli.num('1%') == Fraction(1, 100)
    assert cli.num('1.0') == 1.0
    assert cli.num('1e0') == 1.0

    assert isinstance(cli.num('1'), int)
    assert isinstance(cli.num('1/2'), Fraction)
    assert isinstance(cli.num('1%'), Fraction)
    assert isinstance(cli.num('1.0'), float)
    assert isinstance(cli.num('1e0'), float)


def test_size():
    assert cli.size('1') == 1
    assert cli.size(' 100 ') == 100
    assert cli.size('2K') == 2048
    assert cli.size('1M') == 1048576


def test_file(tmpdir):
    assert cli.file('-') is sys.stdin.buffer
    data = list(range(100))
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        json.dump(data, f)
    with cli.file(filename) as f:
        assert isinstance(f, io.IOBase)


def test_main(tmpdir, capsys):
    data = list(range(100))
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        json.dump(data, f)
    assert cli.main([filename]) == 0
    assert capsys.readouterr().out.strip() == '[ int range=0..99 ]'


def test_main_manual_encoding(tmpdir, capsys):
    data = list(range(100))
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w', encoding='ascii') as f:
        json.dump(data, f)
    assert cli.main([filename, '--encoding', 'ascii']) == 0
    assert capsys.readouterr().out.strip() == '[ int range=0..99 ]'


def test_debug(tmpdir, capsys):
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        f.write('foo bar baz')
    os.environ['DEBUG'] = '0'
    assert cli.main([filename, '--format', 'json']) == 1
    assert capsys.readouterr().err.splitlines()[-1].strip() == 'Expecting value: line 1 column 1 (char 0)'
    os.environ['DEBUG'] = '1'
    with pytest.raises(Exception):
        cli.main([filename, '--format', 'json'])
