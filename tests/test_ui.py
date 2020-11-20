import os
import csv
import json
import datetime as dt
from fractions import Fraction
from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta

from structa.analyzer import ValidationWarning
from structa.patterns import *
from structa import ui


@pytest.fixture
def table(request):
    return [
        ['Name', 'Nationality'],
        ['Johann Gottfried Hübert', 'German'],
        ['Francis Bacon', 'British'],
        ['August Sallé', 'French'],
        ['Adam Bøving', 'Danish'],
        ['Justus Henning Böhmer', 'German'],
        ['Émilie du Châtelet', 'French'],
        ['Mihály Csokonai Vitéz', 'Hungarian'],
        ['Carl von Linné', 'Swedish'],
        ['François Marie Arouet', 'French'],
        # The following rows cannot be encoded in latin-1
        ['Zdenek Bouček', 'Czech'],
        ['Ruđer Josip Bošković', 'Croatian'],
        ['Hugo Kołłątaj', 'Polish'],
    ]


def test_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        ui.main(['-h'])
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


def test_encoding(tmpdir, table):
    progress = mock.Mock()
    filename = str(tmpdir.join('latin-1.csv'))
    with open(filename, 'w', encoding='latin-1') as f:
        writer = csv.writer(f)
        for row in table[:-3]:
            writer.writerow(row)
    with pytest.warns(ValidationWarning):
        assert ui.load_data(ui.get_config([filename]), progress) == table[1:-3]
    assert ui.load_data(ui.get_config([filename, '-e', 'latin-1']), progress) == table[1:-3]
    with pytest.raises(UnicodeError):
        ui.load_data(ui.get_config([filename, '-e', 'utf-8']), progress)

    filename = str(tmpdir.join('utf-8.csv'))
    with open(filename, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow(row)
    assert ui.load_data(ui.get_config([filename]), progress) == table[1:]


#def test_csv_format(tmpdir, table):
#    filename = str(tmpdir.join('commas.csv'))
#    with open(filename, 'w', encoding='utf-8') as f:
#        writer = csv.writer(f)
#        for row in table:
#            writer.writerow(row)
#    assert ui.main([filename]) == 0
#    assert ui


def test_main(tmpdir, capsys):
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
