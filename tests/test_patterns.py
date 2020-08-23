import datetime as dt

import pytest

from structa.chars import *
from structa.patterns import *


def test_format_int():
    assert format_int(0) == '0'
    assert format_int(1) == '1'
    assert format_int(999) == '999'
    assert format_int(-999) == '-999'
    assert format_int(1000) == '1.0K'
    assert format_int(-1000) == '-1.0K'
    assert format_int(999900) == '999.9K'
    assert format_int(1000000) == '1.0M'


def test_to_bool():
    assert to_bool('0') is False
    assert to_bool('1') is True
    assert to_bool('true', false='false', true='true') is True
    assert to_bool('f', false='f', true='t') is False
    with pytest.raises(ValueError):
        to_bool('')
    with pytest.raises(ValueError):
        to_bool('f')


def test_try_conversion():
    data = range(10)
    str_data = [str(n) for n in data]
    assert try_conversion(str_data, int) == set(data)
    assert try_conversion(str_data + [''], int, threshold=1) == set(data)
    with pytest.raises(ValueError):
        try_conversion(str_data + [''] * 4, int, threshold=2)


def test_stats():
    assert Stats.from_sample(range(10)) == Stats(10, 0, 9, 5)
    assert Stats.from_sample(range(1000)) == Stats(1000, 0, 999, 500)
    with pytest.raises(AssertionError):
        Stats.from_sample([])


def test_dict():
    data = [
        {},
        {'a': 1},
        {'a': 1, 'b': 2},
    ]
    pattern = Dict(data)
    assert pattern.stats.min == 0
    assert pattern.stats.max == 2
    assert pattern.pattern is None
    assert str(pattern) == '{}'
    assert pattern.validate({})
    assert not pattern.validate('foo')


def test_dict_with_pattern():
    data = [
        {},
        {'a': 1},
        {'a': 1, 'b': 2},
    ]
    pattern = Dict(data, pattern={
        Str({'a', 'b'}, pattern=(AnyChar,)): Int({1, 2})
    })
    assert pattern.stats.min == 0
    assert pattern.stats.max == 2
    assert pattern.pattern is not None
    assert str(pattern) == '{str pattern=.: int range=1..2}'


def test_dict_with_long_pattern():
    data = [
        {'num': 1, 'label': 'foo', 'active': 't'},
        {'num': 2, 'label': 'bar', 'active': 't'},
        {'num': 3, 'label': 'baz'},
        {'num': 4, 'label': 'quux', 'active': 'f'},
    ]
    pattern = Dict(data, pattern={
        Choice('num', optional=False): Int({1, 2, 3, 4}),
        Choice('label', optional=False): Str({'foo', 'bar', 'baz', 'quux'}, pattern=None),
        Choice('active', optional=True): StrRepr(Bool({False, True}), pattern="'f'|'t'"),
    })
    assert pattern.stats.min == 2
    assert pattern.stats.max == 3
    assert pattern.pattern is not None
    assert str(pattern) == """\
{
    'num': int range=1..4,
    'label': str,
    'active'*: str of bool format='f'|'t'
}"""


def test_list():
    data = [
        [],
        [1],
        [1, 2, 3],
    ]
    pattern = List(data)
    assert pattern.stats.min == 0
    assert pattern.stats.max == 3
    assert pattern.pattern is None
    assert str(pattern) == '[]'
    assert pattern.validate([])
    assert not pattern.validate('foo')


def test_list_with_pattern():
    data = [
        [1, 2],
        [1, 2, 3],
        [1, 2, 3, 4],
    ]
    pattern = List(data, pattern=[Int({1, 2, 3, 4})])
    assert pattern.stats.min == 2
    assert pattern.stats.max == 4
    assert pattern.pattern is not None
    assert str(pattern) == '[int range=1..4]'


def test_list_with_long_pattern():
    data = [
        [
            {'num': 1, 'label': 'foo', 'active': 't'},
            {'num': 2, 'label': 'bar', 'active': 't'},
            {'num': 3, 'label': 'baz'},
            {'num': 4, 'label': 'quux', 'active': 'f'},
        ]
    ]
    pattern = List(data, pattern=[
        Dict(data[0], pattern={
            Choice('num', optional=False): Int({1, 2, 3, 4}),
            Choice('label', optional=False): Str({'foo', 'bar', 'baz', 'quux'}, pattern=None),
            Choice('active', optional=True): StrRepr(Bool({False, True}), pattern="f|t"),
        })
    ])
    assert pattern.stats.min == pattern.stats.max == 4
    assert pattern.pattern is not None
    assert str(pattern) == """\
[
    {
        'num': int range=1..4,
        'label': str,
        'active'*: str of bool format=f|t
    }
]"""


def test_str():
    data = ['foo', 'bar', 'baz', 'quux']
    pattern = Str(data, unique=True)
    assert pattern.stats.min == 3
    assert pattern.stats.max == 4
    assert pattern.pattern is None
    assert pattern.unique
    assert str(pattern) == 'str'
    assert pattern.validate('blah')
    assert not pattern.validate('')


def test_fixed_str():
    data = ['0x{:04x}'.format(n) for n in range(32)]
    pattern = Str(data, pattern = ('0', 'x', '0', '0', HexDigit, HexDigit), unique=True)
    assert pattern.stats.min == pattern.stats.max == 6
    assert pattern.unique
    assert str(pattern) == 'str pattern=0x00XX'
    assert pattern.validate('0x0012')
    assert not pattern.validate('0xff')
    assert not pattern.validate('foobar')
    assert not pattern.validate('0x00fg')


def test_str_repr():
    pattern = StrRepr(Int({1, 2, 3, 4}), pattern='d')
    assert str(pattern) == 'str of int range=1..4 format=d'
    assert pattern.validate('1')
    assert not pattern.validate(1)
    assert not pattern.validate('a')


def test_num_repr():
    pattern = NumRepr(DateTime({
        dt.datetime.utcfromtimestamp(0),
        dt.datetime.utcfromtimestamp(1),
        dt.datetime.utcfromtimestamp(86400),
    }), pattern=int)
    assert str(pattern) == 'int of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'
    pattern = NumRepr(DateTime({
        dt.datetime.utcfromtimestamp(0.0),
        dt.datetime.utcfromtimestamp(1.0),
        dt.datetime.utcfromtimestamp(86400.0),
    }), pattern=float)
    assert str(pattern) == 'float of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'


def test_int():
    data = {1, 2, 3, 1000}
    pattern = Int.from_strings([str(i) for i in data], 'd', True)
    assert pattern == StrRepr(Int(data, unique=True), pattern='d')
    assert pattern.validate('5')
    assert not pattern.validate(1)
    assert not pattern.validate('2000')
    assert str(pattern) == 'str of int range=1..1.0K format=d'


def test_float():
    data = {0.0, 1.0, 1000.0}
    pattern = Float.from_strings([str(f) for f in data], 'f', True)
    assert pattern == StrRepr(Float(data, unique=True), pattern='f')
    assert pattern.validate('1.0')
    assert not pattern.validate(1.0)
    assert not pattern.validate('2000.0')
    assert str(pattern) == 'str of float range=0.0..1000.0 format=f'


def test_datetime():
    iso_fmt = '%Y-%m-%d %H:%M:%S'
    data = {
        dt.datetime.strptime('1970-01-01 00:00:00', iso_fmt),
        dt.datetime.strptime('1970-01-01 00:00:01', iso_fmt),
        dt.datetime.strptime('1970-01-02 00:00:00', iso_fmt),
        dt.datetime.strptime('1970-02-01 00:00:00', iso_fmt),
    }
    pattern = DateTime.from_strings(
        [d.strftime(iso_fmt) for d in data], iso_fmt, True)
    assert pattern == StrRepr(DateTime(data, unique=True), pattern=iso_fmt)
    assert pattern.validate('1970-01-01 00:30:00')
    assert not pattern.validate(86400)
    assert not pattern.validate('1980-01-01 00:00:00')
    assert str(pattern) == 'str of datetime range=1970-01-01 00:00:00..1970-02-01 00:00:00 format=%Y-%m-%d %H:%M:%S'


def test_datetime_numrepr():
    iso_fmt = '%Y-%m-%d %H:%M:%S'
    data = {
        dt.datetime.fromtimestamp(0),
        dt.datetime.fromtimestamp(1),
        dt.datetime.fromtimestamp(86400),
        dt.datetime.fromtimestamp(100000),
    }
    numbers = Int({d.timestamp() for d in data}, unique=True)
    pattern = DateTime.from_numbers(numbers)
    assert pattern == NumRepr(DateTime(data, unique=True), pattern=int)
    assert pattern.validate(1000)
    assert not pattern.validate(1000.0)
    assert not pattern.validate(1000000000000)
    assert not pattern.validate(1200000)


def test_datetime_strrepr_numrepr():
    data = {
        dt.datetime.fromtimestamp(0),
        dt.datetime.fromtimestamp(1),
        dt.datetime.fromtimestamp(86400),
        dt.datetime.fromtimestamp(100000),
    }
    numbers = StrRepr(Int({d.timestamp() for d in data}, unique=True), pattern='d')
    pattern = DateTime.from_numbers(numbers)
    assert pattern == StrRepr(NumRepr(DateTime(data, unique=True), pattern=int), pattern='d')
    assert pattern.validate('1000')
    assert not pattern.validate('1000000000000')
    assert not pattern.validate('foo')

    numbers = StrRepr(Float({d.timestamp() for d in data}, unique=True), pattern='f')
    pattern = DateTime.from_numbers(numbers)
    assert pattern == StrRepr(NumRepr(DateTime(data, unique=True), pattern=float), pattern='f')
    assert pattern.validate('1000')
    assert pattern.validate('1000.0')
    assert not pattern.validate('1e12')
    assert not pattern.validate('foo')


def test_bool():
    pattern = Bool.from_strings({'f', 't'}, 'f|t')
    assert pattern == StrRepr(Bool({False, True}), pattern='f|t')
    assert pattern.validate('t')
    assert not pattern.validate('true')
    assert not pattern.validate(True)


def test_url():
    data = [
        'http://localhost',
        'https://structa.readthedocs.io/',
    ]
    pattern = URL(True)
    assert str(pattern) == 'URL'
    assert pattern.validate('https://www.google.com/')
    assert not pattern.validate('foo')
    assert not pattern.validate(100)


def test_choices():
    data = {'url'}
    pattern = Choices({Choice(s, False) for s in data})
    assert str(pattern) == 'url'
    assert pattern.validate('url')
    assert not pattern.validate('foo')

    data = {'url', 'count', 'active'}
    pattern = Choices({Choice(s, False) for s in data})
    assert set(str(pattern).strip('{}').split('|')) == data
    assert pattern.validate('url')
    assert not pattern.validate('foo')
    assert not pattern.validate(1)


def test_value():
    pattern = Value()
    assert str(pattern) == 'value'
    assert pattern.validate(None)
    assert pattern.validate(1)
    assert pattern.validate('foo')


def test_empty():
    pattern = Empty()
    assert str(pattern) == ''
    assert not pattern.validate(None)
    assert not pattern.validate(1)
    assert not pattern.validate('foo')
