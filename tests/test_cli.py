import os
import json
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



def test_main(tmpdir, capsys):
    data = list(range(100))
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        json.dump(data, f)
    assert cli.main([filename]) == 0
    assert capsys.readouterr().out.strip() == str(List(
        sample=[data], content=[Int(Counter(data))]))


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
