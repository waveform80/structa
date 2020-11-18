import os
import json
import datetime as dt
from fractions import Fraction
from unittest import mock

import pytest

from dateutil.relativedelta import relativedelta
from structa.patterns import *
from structa import ui


def test_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        ui.cli_main(['-h'])
    assert exc_info.value.args[0] == 0  # return code 0
    captured = capsys.readouterr()
    assert captured.out.lstrip().startswith('usage: ')


def test_min_timestamp():
    assert ui.min_timestamp('2000-01-01') == dt.datetime(2000, 1, 1)
    assert ui.min_timestamp('10 years') == ui._start - relativedelta(years=10)


def test_max_timestamp():
    assert ui.max_timestamp('2050-01-01') == dt.datetime(2050, 1, 1)
    assert ui.max_timestamp('10 years') == ui._start + relativedelta(years=10)


def test_num():
    assert ui.num('1') == 1
    assert ui.num('1/2') == Fraction(1, 2)
    assert ui.num('1%') == Fraction(1, 100)
    assert ui.num('1.0') == 1.0
    assert ui.num('1e0') == 1.0

    assert isinstance(ui.num('1'), int)
    assert isinstance(ui.num('1/2'), Fraction)
    assert isinstance(ui.num('1%'), Fraction)
    assert isinstance(ui.num('1.0'), float)
    assert isinstance(ui.num('1e0'), float)


def test_analyze(tmpdir, capsys):
    data = list(range(100))
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        json.dump(data, f)
    assert ui.main([filename]) == 0
    assert capsys.readouterr().out.strip() == str(List(
        sample=[data], pattern=[Int(Counter(data))]))


def test_debug(tmpdir, capsys):
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        f.write('foo bar baz')
    os.environ['DEBUG'] = '0'
    assert ui.main([filename, '--format', 'json']) == 1
    assert capsys.readouterr().err.splitlines()[-1].strip() == 'Expecting value: line 1 column 1 (char 0)'
    os.environ['DEBUG'] = '1'
    with pytest.raises(Exception):
        ui.main([filename, '--format', 'json'])
