import datetime as dt
from collections import namedtuple, Counter

import pytest

from structa.chars import *
from structa.patterns import *


def test_frozen_counter():
    c = Counter((1, 2, 3) * 100 + (4, 5) * 50)
    f = FrozenCounter(c)
    assert c == f
    c[6] = 1
    assert c != f
    d = {f: 1}
    assert d[f] == 1
    with pytest.raises(AssertionError):
        FrozenCounter.from_counter({})


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
    str_data = Counter(str(n) for n in data)
    assert try_conversion(str_data, int) == Counter(data)
    str_data[''] = 1
    assert try_conversion(str_data, int, threshold=1) == Counter(data)
    with pytest.raises(ValueError):
        str_data[''] = 4
        try_conversion(str_data, int, threshold=2)


def test_stats():
    assert ScalarStats.from_sample(Counter(range(10))) == ScalarStats(
        Counter(range(10)), 10, 0, 9, 5)
    assert ScalarStats.from_sample(Counter(range(1000))) == ScalarStats(
        Counter(range(1000)), 1000, 0, 999, 500)
    with pytest.raises(AssertionError):
        ScalarStats.from_sample([])


def test_dict():
    data = [
        {},
        {'a': 1},
        {'a': 1, 'b': 2},
    ]
    pattern = Dict(data)
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 2
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
    defs = {
        Str(Counter({'a', 'b'}), pattern=(AnyChar,)): Int(Counter({1, 2})),
    }
    pattern = Dict(data, fields=defs.keys(), pattern=tuple(defs.values()))
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 2
    assert pattern.fields is not None
    assert pattern.pattern is not None
    assert str(pattern) == '{str pattern=.: int range=1..2}'


def test_dict_with_long_pattern():
    data = [
        {'num': 1, 'label': 'foo', 'active': 't'},
        {'num': 2, 'label': 'bar', 'active': 't'},
        {'num': 3, 'label': 'baz'},
        {'num': 4, 'label': 'quux', 'active': 'f'},
    ]
    defs = {
        Choice('num', optional=False): Int(Counter({1, 2, 3, 4})),
        Choice('label', optional=False): Str(Counter({'foo', 'bar', 'baz', 'quux'}), pattern=None),
        Choice('active', optional=True): StrRepr(Bool(Counter({False, True})), pattern="'f'|'t'"),
    }
    pattern = Dict(data, fields=defs.keys(), pattern=tuple(defs.values()))
    assert pattern.lengths.min == 2
    assert pattern.lengths.max == 3
    assert pattern.pattern is not None
    assert str(pattern) == """\
{
    'num': int range=1..4,
    'label': str,
    'active'*: str of bool format='f'|'t'
}"""


def test_tuple():
    data = [
        (),
        (1,),
        (1, 2, 3),
    ]
    pattern = Tuple(data)
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 3
    assert pattern.fields is None
    assert pattern.pattern is None
    assert str(pattern) == '()'
    assert pattern.validate(())
    assert not pattern.validate('foo')


def test_tuple_with_pattern():
    data = [
        ('foo', 1),
        ('bar', 2),
        ('baz', 3),
    ]
    defs = {
        Choice(0, False): Str(Counter(['foo', 'bar', 'baz']),
                              pattern=(AnyChar, AnyChar, AnyChar)),
        Choice(1, False): Int(Counter([1, 2, 3])),
    }
    pattern = Tuple(
        data,
        fields=tuple(defs.keys()),
        pattern=tuple(defs.values())
    )
    assert pattern.lengths.min == 2
    assert pattern.lengths.max == 2
    assert pattern.fields is not None
    assert pattern.pattern is not None
    assert str(pattern) == '(str pattern=..., int range=1..3)'


def test_tuple_with_long_pattern():
    book = namedtuple('book', ('author', 'title', 'published'))
    data = [
        book('J. R. R. Tolkien', 'The Fellowship of the Ring', '1954-07-29'),
        book('J. R. R. Tolkien', 'The Two Towers', '1954-11-11'),
        book('J. R. R. Tolkien', 'The Return of the King', '1955-10-20'),
    ]
    defs = {
        Choice('author', False): Str(Counter(t[0] for t in data), pattern=tuple('J. R. R. Tolkien')),
        Choice('title', False): Str(Counter(t[1] for t in data), pattern=None),
        Choice('published', False): StrRepr(
            DateTime(Counter(dt.datetime.strptime(t[2], '%Y-%m-%d') for t in data)),
            pattern='%Y-%m-%d'
        )
    }
    pattern = List([data], pattern=[
        Tuple(data, fields=tuple(defs.keys()), pattern=tuple(defs.values()))
    ])
    assert pattern.lengths.min == pattern.lengths.max == 3
    assert pattern.pattern[0].fields is not None
    assert pattern.pattern[0].pattern is not None
    assert str(pattern) == """\
[
    (
        author=str pattern=J. R. R. Tolkien,
        title=str,
        published=str of datetime range=1954-07-29 00:00:00..1955-10-20 00:00:00 format=%Y-%m-%d
    )
]"""


def test_list():
    data = [
        [],
        [1],
        [1, 2, 3],
    ]
    pattern = List(data)
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 3
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
    pattern = List(data, pattern=[Int(Counter(j for i in data for j in i))])
    assert pattern.lengths.min == 2
    assert pattern.lengths.max == 4
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
    defs = {
        Choice('num', optional=False): Int(Counter({1, 2, 3, 4})),
        Choice('label', optional=False): Str(Counter({'foo', 'bar', 'baz', 'quux'}), pattern=None),
        Choice('active', optional=True): StrRepr(Bool(Counter({False, True})), pattern="f|t"),
    }
    pattern = List(data, pattern=[
        Dict(data[0], fields=defs.keys(), pattern=tuple(defs.values()))
    ])
    assert pattern.lengths.min == pattern.lengths.max == 4
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
    pattern = Str(Counter(data))
    assert pattern.lengths.min == 3
    assert pattern.lengths.max == 4
    assert pattern.pattern is None
    assert pattern.unique
    assert str(pattern) == 'str'
    assert pattern.validate('blah')
    assert not pattern.validate('')


def test_fixed_str():
    data = ['0x{:04x}'.format(n) for n in range(32)]
    pattern = Str(Counter(data), pattern = ('0', 'x', '0', '0', HexDigit, HexDigit))
    assert pattern.lengths.min == pattern.lengths.max == 6
    assert pattern.unique
    assert str(pattern) == 'str pattern=0x00XX'
    assert pattern.validate('0x0012')
    assert not pattern.validate('0xff')
    assert not pattern.validate('foobar')
    assert not pattern.validate('0x00fg')


def test_str_repr():
    pattern = StrRepr(Int(Counter({1, 2, 3, 4})), pattern='d')
    assert str(pattern) == 'str of int range=1..4 format=d'
    assert pattern.validate('1')
    assert not pattern.validate(1)
    assert not pattern.validate('a')


def test_num_repr():
    pattern = NumRepr(DateTime(Counter((
        dt.datetime.utcfromtimestamp(0),
        dt.datetime.utcfromtimestamp(1),
        dt.datetime.utcfromtimestamp(86400),
    ))), pattern=int)
    assert str(pattern) == 'int of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'
    pattern = NumRepr(DateTime(Counter((
        dt.datetime.utcfromtimestamp(0.0),
        dt.datetime.utcfromtimestamp(1.0),
        dt.datetime.utcfromtimestamp(86400.0),
    ))), pattern=float)
    assert str(pattern) == 'float of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'


def test_int():
    data = {1, 2, 3, 1000}
    pattern = Int.from_strings(Counter(str(i) for i in data), 'd', True)
    assert pattern == StrRepr(Int(Counter(data)), pattern='d')
    assert pattern.validate('5')
    assert not pattern.validate(1)
    assert not pattern.validate('2000')
    assert str(pattern) == 'str of int range=1..1.0K format=d'


def test_float():
    data = {0.0, 1.0, 1000.0}
    pattern = Float.from_strings(Counter(str(f) for f in data), 'f', True)
    assert pattern == StrRepr(Float(Counter(data)), pattern='f')
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
        Counter(d.strftime(iso_fmt) for d in data), iso_fmt)
    assert pattern == StrRepr(DateTime(Counter(data)), pattern=iso_fmt)
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
    numbers = Int(Counter(d.timestamp() for d in data))
    pattern = DateTime.from_numbers(numbers)
    assert pattern == NumRepr(DateTime(Counter(data)), pattern=int)
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
    numbers = StrRepr(Int(Counter(d.timestamp() for d in data)), pattern='d')
    pattern = DateTime.from_numbers(numbers)
    assert pattern == StrRepr(NumRepr(DateTime(Counter(data)), pattern=int), pattern='d')
    assert pattern.validate('1000')
    assert not pattern.validate('1000000000000')
    assert not pattern.validate('foo')

    numbers = StrRepr(Float(Counter(d.timestamp() for d in data)), pattern='f')
    pattern = DateTime.from_numbers(numbers)
    assert pattern == StrRepr(NumRepr(DateTime(Counter(data)), pattern=float), pattern='f')
    assert pattern.validate('1000')
    assert pattern.validate('1000.0')
    assert not pattern.validate('1e12')
    assert not pattern.validate('foo')


def test_bool():
    pattern = Bool.from_strings(Counter(('f', 't')), 'f|t')
    assert pattern == StrRepr(Bool(Counter((False, True))), pattern='f|t')
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
    assert repr(pattern) == 'Value()'
    assert pattern.validate(None)
    assert pattern.validate(1)
    assert pattern.validate('foo')
    assert Value() == Value()
    assert Value() != Empty()


def test_empty():
    pattern = Empty()
    assert str(pattern) == ''
    assert repr(pattern) == 'Empty()'
    assert not pattern.validate(None)
    assert not pattern.validate(1)
    assert not pattern.validate('foo')
    assert Empty() == Empty()
    assert Empty() != Value()
