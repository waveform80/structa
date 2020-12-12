import datetime as dt
from collections import namedtuple, Counter

import pytest

from structa.chars import *
from structa.types import *


def test_stats():
    s = Stats.from_sample(Counter(range(10)))
    assert s == Stats(Counter(range(10)), 10, 0, 2, 5, 7, 9)
    assert s != []
    assert repr(s) == 'Stats(sample=..., card=10, min=0, q1=2, q2=5, q3=7, max=9)'
    assert Stats.from_sample(Counter(range(1000))) == Stats(
        Counter(range(1000)), 1000, 0, 250, 500, 750, 999)
    with pytest.raises(AssertionError):
        Stats.from_sample([])
    c = Stats.from_lengths([[], [1], [1, 2, 3]])
    assert c == Stats(Counter((0, 1, 3)), 3, 0, 0, 1, 3, 3)
    assert c != []
    assert repr(c) == 'Stats(sample=..., card=3, min=0, q1=0, q2=1, q3=3, max=3)'


def test_stats_merge():
    s1 = Stats.from_sample(Counter(range(10)))
    s2 = Stats.from_sample(Counter(range(20)))
    s3 = s1 + s2
    assert s3 == Stats.from_sample(Counter(list(range(10)) + list(range(20))))
    with pytest.raises(TypeError):
        s1 + []


def test_pattern():
    assert Type() != None


def test_dict():
    data = [
        {},
        {'a': 1},
        {'a': 1, 'b': 2},
    ]
    pattern = Dict(data)
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 2
    assert pattern.content is None
    assert str(pattern) == '{}'
    assert repr(pattern) == 'Dict(content=None)'
    assert pattern.validate({})
    assert not pattern.validate('foo')


def test_dict_with_pattern():
    data = [
        {},
        {'a': 1},
        {'a': 1, 'b': 2},
    ]
    pattern = Dict(data, content=[
        DictField(
            Str(FrozenCounter(('a', 'a', 'b')), pattern=[any_char]),
            Int(FrozenCounter((1, 1, 2)))
        )])
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 2
    assert str(pattern) == '{str pattern=.: int range=1..2}'
    assert repr(pattern) == (
        'Dict(content=[DictField(key=Str(pattern=[AnyChar()], values=..., '
        'unique=False), value=Int(values=..., unique=False))])')


def test_dict_with_long_pattern():
    data = [
        {'num': 1, 'label': 'foo', 'active': 't'},
        {'num': 2, 'label': 'bar', 'active': 't'},
        {'num': 3, 'label': 'baz'},
        {'num': 4, 'label': 'quux', 'active': 'f'},
    ]
    pattern = Dict(data, content=[
        DictField(
            Field('active', optional=True),
            StrRepr(Bool(Counter({False, True})), pattern="f|t")),
        DictField(
            Field('label', optional=False),
            Str(Counter({'foo', 'bar', 'baz', 'quux'}), pattern=None)),
        DictField(Field('num', optional=False), Int(Counter({1, 2, 3, 4}))),
    ])
    assert pattern.lengths.min == 2
    assert pattern.lengths.max == 3
    assert str(pattern) == """\
{
    'active'*: str of bool pattern=f|t,
    'label': str,
    'num': int range=1..4
}"""
    assert repr(pattern) == (
        "Dict(content=["
        "DictField(key=Field(value='active', optional=True), "
        "value=StrRepr(content=Bool(values=..., unique=True), pattern='f|t')), "
        "DictField(key=Field(value='label', optional=False), "
        "value=Str(pattern=None, values=..., unique=True)), "
        "DictField(key=Field(value='num', optional=False), "
        "value=Int(values=..., unique=True))])")
    assert pattern + pattern == pattern
    with pytest.raises(TypeError):
        pattern + 100


def test_tuple():
    data = [
        (),
        (1,),
        (1, 2, 3),
    ]
    pattern = Tuple(data)
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 3
    assert str(pattern) == '()'
    assert repr(pattern) == 'Tuple(content=None)'
    assert pattern.validate(())
    assert not pattern.validate('foo')


def test_tuple_with_pattern():
    data = [
        ('foo', 1),
        ('bar', 2),
        ('baz', 3),
    ]
    pattern = Tuple(data, content=[
        TupleField(
            Field(0, optional=False),
            Str(Counter(['foo', 'bar', 'baz']),
                pattern=[any_char, any_char, any_char])),
        TupleField(Field(1, optional=False), Int(Counter([1, 2, 3]))),
    ])
    assert pattern.lengths.min == 2
    assert pattern.lengths.max == 2
    assert str(pattern) == '(str pattern=..., int range=1..3)'
    assert repr(pattern) == (
        "Tuple(content=["
        "TupleField(value=Str(pattern=[AnyChar(), AnyChar(), AnyChar()], values=..., unique=True)), "
        "TupleField(value=Int(values=..., unique=True))])")


def test_tuple_with_long_pattern():
    book = namedtuple('book', ('author', 'title', 'published'))
    data = [
        book('J. R. R. Tolkien', 'The Fellowship of the Ring', '1954-07-29'),
        book('J. R. R. Tolkien', 'The Two Towers', '1954-11-11'),
        book('J. R. R. Tolkien', 'The Return of the King', '1955-10-20'),
    ]
    pattern = List([data], content=[Tuple(data, content=[
        TupleField(
            Field(0, optional=False),
            Str(Counter(t[0] for t in data), pattern=[CharClass(c) for c in 'J. R. R. Tolkien'])),
        TupleField(
            Field(1, optional=False),
            Str(Counter(t[1] for t in data), pattern=None)),
        TupleField(
            Field(2, optional=False),
            StrRepr(
                 DateTime(Counter(dt.datetime.strptime(t[2], '%Y-%m-%d') for t in data)),
                 pattern='%Y-%m-%d'
            ))
    ])])
    assert pattern.lengths.min == pattern.lengths.max == 3
    assert str(pattern) == """\
[
    (
        str pattern=J. R. R. Tolkien,
        str,
        str of datetime range=1954-07-29 00:00:00..1955-10-20 00:00:00 pattern=%Y-%m-%d
    )
]"""
    assert repr(pattern) == (
        "List(content=[Tuple(content=["
        "TupleField(value=Str(pattern=[" +
        ', '.join('CharClass({!r})'.format(c) for c in 'J. R. R. Tolkien') +
        "], values=..., unique=False)), "
        "TupleField(value=Str(pattern=None, values=..., unique=True)), "
        "TupleField(value=StrRepr(content=DateTime(values=..., unique=True), "
        "pattern='%Y-%m-%d'))"
        "])])"
    )
    assert pattern + pattern == pattern


def test_list():
    data = [
        [],
        [1],
        [1, 2, 3],
    ]
    pattern = List(data)
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 3
    assert pattern.content is None
    assert str(pattern) == '[]'
    assert pattern.validate([])
    assert not pattern.validate('foo')


def test_list_with_pattern():
    data = [
        [1, 2],
        [1, 2, 3],
        [1, 2, 3, 4],
    ]
    pattern = List(data, content=[Int(Counter(j for i in data for j in i))])
    assert pattern.lengths.min == 2
    assert pattern.lengths.max == 4
    assert pattern.content is not None
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
    pattern = List(data, content=[Dict(
        data[0], content=[
            DictField(
                Field('active', optional=True),
                StrRepr(Bool(Counter({False, True})), pattern="f|t")),
            DictField(
                Field('label', optional=False),
                Str(Counter({'foo', 'bar', 'baz', 'quux'}), pattern=None)),
            DictField(
                Field('num', optional=False), Int(Counter({1, 2, 3, 4}))),
        ])])
    assert pattern.lengths.min == pattern.lengths.max == 4
    assert str(pattern) == """\
[
    {
        'active'*: str of bool pattern=f|t,
        'label': str,
        'num': int range=1..4
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
    assert pattern + pattern == pattern
    with pytest.raises(TypeError):
        pattern + 100


def test_fixed_str():
    data = ['0x{:04x}'.format(n) for n in range(32)]
    pattern = Str(Counter(data), pattern=[
        CharClass('0'), CharClass('x'), CharClass('0'), CharClass('0'),
        hex_digit, hex_digit])
    assert pattern.lengths.min == pattern.lengths.max == 6
    assert pattern.unique
    assert str(pattern) == 'str pattern=0x00[0-9A-Fa-f][0-9A-Fa-f]'
    assert pattern.validate('0x0012')
    assert not pattern.validate('0xff')
    assert not pattern.validate('foobar')
    assert not pattern.validate('0x00fg')


def test_str_repr():
    pattern = StrRepr(Int(Counter({1, 2, 3, 4})), pattern='d')
    assert str(pattern) == 'str of int range=1..4 pattern=d'
    assert pattern.validate('1')
    assert not pattern.validate(1)
    assert not pattern.validate('a')


def test_num_repr():
    pattern = NumRepr(DateTime(Counter((
        dt.datetime.utcfromtimestamp(0),
        dt.datetime.utcfromtimestamp(1),
        dt.datetime.utcfromtimestamp(86400),
    ))), pattern=Int)
    assert str(pattern) == 'int of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'
    pattern = NumRepr(DateTime(Counter((
        dt.datetime.utcfromtimestamp(0.0),
        dt.datetime.utcfromtimestamp(1.0),
        dt.datetime.utcfromtimestamp(86400.0),
    ))), pattern=Float)
    assert str(pattern) == 'float of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'


def test_int():
    data = {1, 2, 3, 1000}
    pattern = Int.from_strings(Counter(str(i) for i in data), 'd', True)
    assert pattern == StrRepr(Int(Counter(data)), pattern='d')
    assert pattern.validate('5')
    assert not pattern.validate(1)
    assert not pattern.validate('2000')
    assert str(pattern) == 'str of int range=1..1.0K pattern=d'
    assert pattern + pattern == pattern
    with pytest.raises(TypeError):
        pattern + 100


def test_float():
    data = {0.0, 1.0, 1000.0}
    pattern = Float.from_strings(Counter(str(f) for f in data), 'f', True)
    assert pattern == StrRepr(Float(Counter(data)), pattern='f')
    assert pattern.validate('1.0')
    assert not pattern.validate(1.0)
    assert not pattern.validate('2000.0')
    assert str(pattern) == 'str of float range=0.0..1000.0 pattern=f'
    assert pattern + pattern == pattern
    with pytest.raises(TypeError):
        pattern + 100


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
    assert str(pattern) == 'str of datetime range=1970-01-01 00:00:00..1970-02-01 00:00:00 pattern=%Y-%m-%d %H:%M:%S'


def test_datetime_numrepr():
    data = {
        dt.datetime.fromtimestamp(0),
        dt.datetime.fromtimestamp(1),
        dt.datetime.fromtimestamp(86400),
        dt.datetime.fromtimestamp(100000),
    }
    numbers = Int(Counter(d.timestamp() for d in data))
    pattern = DateTime.from_numbers(numbers)
    assert pattern == NumRepr(DateTime(Counter(data)), pattern=Int)
    assert pattern.validate(1000)
    assert not pattern.validate('1000')
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
    assert pattern == StrRepr(NumRepr(DateTime(Counter(data)), pattern=Int), pattern='d')
    assert pattern.validate('1000')
    assert not pattern.validate('1000000000000')
    assert not pattern.validate('foo')

    numbers = StrRepr(Float(Counter(d.timestamp() for d in data)), pattern='f')
    pattern = DateTime.from_numbers(numbers)
    assert pattern == StrRepr(NumRepr(DateTime(Counter(data)), pattern=Float), pattern='f')
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
    assert pattern + pattern == pattern
    with pytest.raises(TypeError):
        pattern + 100


def test_scalar_add():
    data = {1, 2, 3, 1000}
    int_pattern = Int(Counter(data))
    bool_pattern = Bool(Counter((0, 1)))
    assert int_pattern + bool_pattern == int_pattern
    with pytest.raises(TypeError):
        data = ['foo', 'bar', 'baz', 'quux']
        str_pattern = Str(Counter(data))
        int_pattern + str_pattern


def test_strrepr_add():
    bool_pattern = Bool.from_strings(Counter(('0', '1')), '0|1')
    data = {1, 2, 3, 1000}
    int_pattern = Int.from_strings(Counter(str(i) for i in data), 'd', True)
    assert int_pattern + bool_pattern == int_pattern
    data = {1, 2, 3, 1000}
    oct_pattern = Int.from_strings(Counter(oct(i) for i in data), 'o', True)
    hex_pattern = Int.from_strings(Counter(hex(i) for i in data), 'x', True)
    assert oct_pattern + hex_pattern == hex_pattern
    str_pattern = Str(Counter(('0', '1')))
    assert bool_pattern != str_pattern


def test_numrepr_add():
    data = {
        dt.datetime.fromtimestamp(0),
        dt.datetime.fromtimestamp(1),
        dt.datetime.fromtimestamp(86400),
        dt.datetime.fromtimestamp(100000),
    }
    numbers = Int(Counter(d.timestamp() for d in data))
    int_pattern = DateTime.from_numbers(numbers)
    assert int_pattern + int_pattern == int_pattern
    numbers = Float(Counter(d.timestamp() for d in data))
    float_pattern = DateTime.from_numbers(numbers)
    assert int_pattern + float_pattern == float_pattern
    with pytest.raises(TypeError):
        str_pattern = Str(Counter(('0', '1')))
        int_pattern + str_pattern


def test_url():
    data = [
        'http://localhost',
        'https://structa.readthedocs.io/',
    ]
    pattern = URL(Counter(data))
    assert str(pattern) == 'URL'
    assert pattern.validate('https://www.google.com/')
    assert not pattern.validate('foo')
    assert not pattern.validate(100)


def test_fields():
    data = {'url'}
    pattern = Fields({Field(s, False) for s in data})
    assert str(pattern) == "<'url'>"
    assert pattern.validate('url')
    assert not pattern.validate('foo')

    data = {'url', 'count', 'active'}
    pattern = Fields({Field(s, False) for s in data})
    assert set(s.strip("'") for s in str(pattern).strip('<>').split('|')) == data
    assert pattern.validate('url')
    assert not pattern.validate('foo')
    assert not pattern.validate(1)

    f1 = Field('url', False)
    f2 = Field('url', False)
    f3 = Field('count', False)
    assert f1 == f2
    assert f1 + f2 == f1
    assert f2 != f3
    assert f3 < f2
    assert f2 > f3
    with pytest.raises(TypeError):
        f2 + f3
    with pytest.raises(TypeError):
        f2 > 'abc'


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
