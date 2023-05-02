# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
import datetime as dt
from collections import namedtuple, Counter

import pytest
from lxml.etree import fromstring, tostring, iselement

from structa.chars import *
from structa.types import *
from structa.xml import xml


def compare_etree(elem1, elem2):
    return (
        elem1.tag == elem2.tag and
        (elem1.text or '') == (elem2.text or '') and
        (elem1.tail or '') == (elem2.tail or '') and
        elem1.attrib == elem2.attrib and
        len(elem1) == len(elem2) and
        all(
            compare_etree(child1, child2)
            for child1, child2 in zip(elem1, elem2)
        )
    )


def test_stats():
    s = Stats.from_sample(Counter(range(10)))
    assert s == Stats(Counter(range(10)), 10, 0, 2, 5, 7, 9)
    assert s.median == s.q2
    assert s != []
    assert repr(s) == 'Stats(sample=..., card=10, min=0, q1=2, q2=5, q3=7, max=9, unique=True)'
    assert Stats.from_sample(Counter(range(1000))) == Stats(
        Counter(range(1000)), 1000, 0, 250, 500, 750, 999)
    with pytest.raises(AssertionError):
        Stats.from_sample([])
    c = Stats.from_lengths([[], [1], [1, 2, 3]])
    assert c == Stats(Counter((0, 1, 3)), 3, 0, 0, 1, 3, 3)
    assert c != []
    assert repr(c) == 'Stats(sample=..., card=3, min=0, q1=0, q2=1, q3=3, max=3, unique=True)'


def test_stats_xml():
    s1 = Stats.from_sample(Counter(range(10)))
    x1 = xml(s1)
    x2 = fromstring(
        '<stats>'
            '<summary values="10" count="10" unique="unique">'
                '<min>0</min><q1>2</q1><q2>5</q2><q3>7</q3><max>9</max>'
                '<graph>'
                    '<fill>..</fill>'
                    '<lit>1</lit>'
                    '<fill>..</fill>'
                    '<lit>2</lit>'
                    '<fill>.</fill>'
                    '<lit>3</lit>'
                    '<fill>..</fill>'
                '</graph>'
            '</summary>'
        '</stats>'
    )
    assert compare_etree(x1, x2)


def test_stats_merge():
    s1 = Stats.from_sample(Counter(range(10)))
    s2 = Stats.from_sample(Counter(range(20)))
    s3 = s1 + s2
    assert s3 == Stats.from_sample(Counter(list(range(10)) + list(range(20))))
    with pytest.raises(TypeError):
        s1 + []


def test_pattern():
    assert Type() != None
    assert tostring(xml(Type())) == b'<type/>'


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
    assert xml(pattern).tag == 'dict'
    pattern.validate({})
    with pytest.raises(TypeError):
        pattern.validate('foo')


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
    assert pattern.size == 3
    assert pattern.lengths.min == 0
    assert pattern.lengths.max == 2
    assert str(pattern) == '{str pattern=.: int range=1..2}'
    assert repr(pattern) == (
        'Dict(content=[DictField(key=Str(pattern=[AnyChar()], values=...), '
        'value=Int(values=...))])')
    assert iselement(xml(pattern).find('content'))
    assert iselement(xml(pattern).find('content').find('field'))
    assert iselement(xml(pattern).find('content').find('field').find('str'))


def test_dict_with_long_pattern():
    data = [
        {'num': 1, 'label': 'foo', 'active': 't'},
        {'num': 2, 'label': 'bar', 'active': 't'},
        {'num': 3, 'label': 'baz'},
        {'num': 4, 'label': 'quux', 'active': 'f'},
    ]
    pattern = Dict(data, content=[
        DictField(
            Field('active', count=3, optional=True),
            StrRepr(Bool(Counter({False, True})), pattern="f|t")),
        DictField(
            Field('label', count=4, optional=False),
            Str(Counter({'foo', 'bar', 'baz', 'quux'}), pattern=None)),
        DictField(
            Field('num', count=4, optional=False),
            Int(Counter({1, 2, 3, 4}))),
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
        "DictField(key=Field(value='active', count=3, optional=True), value=StrRepr(content=Bool(values=...), pattern='f|t')), "
        "DictField(key=Field(value='label', count=4, optional=False), value=Str(pattern=None, values=...)), "
        "DictField(key=Field(value='num', count=4, optional=False), value=Int(values=...))])")
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Int(Counter((1, 2, 3)))
    with pytest.raises(TypeError):
        pattern + 100


def test_dict_similar_matches():
    data = [
        {'num': 1, 'label': 'foo'},
        {'num': 2, 'label': 'bar'},
        {'num': 3, 'label': 'baz'},
        {'num': 4, 'label': 'quux'},
    ]
    pattern_a = Dict(data, content=[
        DictField(
            Field('label', count=4, optional=False),
            Str([d['label'] for d in data], pattern=None)),
        DictField(
            Field('num', count=4, optional=False),
            Int([d['num'] for d in data])),
    ], similarity_threshold=0.5)
    data = [
        {'num': 1, 'label': 'foo', 'active': True},
        {'num': 2, 'label': 'bar', 'active': True},
        {'num': 3, 'label': 'baz', 'active': False},
        {'num': 4, 'label': 'quux', 'active': False},
    ]
    pattern_b = Dict(data, content=[
        DictField(
            Field('active', count=3, optional=False),
            Bool([d['active'] for d in data])),
        DictField(
            Field('label', count=4, optional=False),
            Str([d['label'] for d in data], pattern=None)),
        DictField(
            Field('num', count=4, optional=False),
            Int([d['num'] for d in data])),
    ], similarity_threshold=0.5)
    assert pattern_a == pattern_b
    assert pattern_b == pattern_a
    result = pattern_a + pattern_b
    assert result.content[0].key.optional
    result = pattern_b + pattern_a
    assert result.content[0].key.optional


def test_dict_disimilar_matches():
    data = [
        {'num': 1, 'label': 'foo'},
        {'num': 2, 'label': 'bar'},
        {'num': 3, 'label': 'baz'},
        {'num': 4, 'label': 'quux'},
    ]
    pattern_a = Dict(data, content=[
        DictField(
            Field('label', count=4, optional=False),
            Str([d['label'] for d in data], pattern=None)),
        DictField(
            Field('num', count=4, optional=False),
            Int([d['num'] for d in data])),
    ], similarity_threshold=1)
    data = [
        {'digit': 1, 'name': 'foo', 'active': True},
        {'digit': 2, 'name': 'bar', 'active': True},
        {'digit': 3, 'name': 'baz', 'active': False},
        {'digit': 4, 'name': 'quux', 'active': False},
    ]
    pattern_b = Dict(data, content=[
        DictField(
            Field('active', count=3, optional=False),
            Bool([d['active'] for d in data])),
        DictField(
            Field('name', count=4, optional=False),
            Str([d['name'] for d in data], pattern=None)),
        DictField(
            Field('digit', count=4, optional=False),
            Int([d['digit'] for d in data])),
    ], similarity_threshold=1)
    assert pattern_a != pattern_b
    assert pattern_b != pattern_a
    # Just to cover all lines in zip_dict_fields (which won't otherwise be
    # covered because equality will always terminate early). We're sorting here
    # to deal with odd/old Python versions where dicts are unordered as there
    # is an implicit assumption in zip_dict_fields that the fields iterate in
    # the order defined
    def key_func(t):
        a, b = t
        return (
            '' if a is None else a.key.value,
            '' if b is None else b.key.value,
        )
    assert sorted(zip_dict_fields(pattern_a.content, pattern_b.content), key=key_func) == [
        (None, pattern_b.content[0]),
        (None, pattern_b.content[2]),
        (None, pattern_b.content[1]),
        (pattern_a.content[0], None),
        (pattern_a.content[1], None),
    ]
    assert sorted(zip_dict_fields(pattern_b.content, pattern_a.content), key=key_func) == [
        (None, pattern_a.content[0]),
        (None, pattern_a.content[1]),
        (pattern_b.content[0], None),
        (pattern_b.content[2], None),
        (pattern_b.content[1], None),
    ]


def test_dictfield_equality():
    d = DictField(Field('foo', 3), Int(Counter((1, 2, 3))))
    assert d == d
    assert not d == 'foo'


def test_dict_merge_scalar_fields():
    data = [
        {'num1': '1', 'label': 'foo', 'foo': 'a'},
        {'num1': '2', 'label': 'bar', 'foo': 'b'},
        {'num1': '3', 'label': 'baz'},
        {'num1': '4', 'label': 'quux', 'foo': 'c'},
    ]
    # XXX Actual analysis thinks 'foo' is str-repr of hex int. What happens
    # when this is added to, say, 'q'?
    pattern_a = Dict(data, content=[
        DictField(
            Field('foo', count=3, optional=True),
            Str(Counter(set('abc')), pattern=None)),
        DictField(
            Field('label', count=4, optional=False),
            Str(Counter({'foo', 'bar', 'baz', 'quux'}), pattern=None)),
        DictField(
            Field('num1', count=4, optional=False),
            Str(Counter(str(i) for i in range(1, 5)), pattern='d')),
    ])
    data = [
        {'foo': 'a', 'label': 'foo', 'num{}'.format(i): str(i)}
        for i in range(50)
    ]
    pattern_b = Dict(data, content=[
        DictField(
            Str(Counter({'foo', 'label'} | set('num{}'.format(i) for i in range(50)))),
            Str(Counter(str(i) for i in range(50)), pattern=None)),
    ])
    assert pattern_a == pattern_b
    result = pattern_a + pattern_b
    assert len(result.content) == 1
    assert isinstance(result.content[0].key, Str)
    assert isinstance(result.content[0].value, Redo)
    # Test commutativity of mismatched merge
    assert pattern_b == pattern_a
    result = pattern_b + pattern_a
    assert len(result.content) == 1
    assert isinstance(result.content[0].key, Str)
    assert isinstance(result.content[0].value, Redo)


def test_dict_merge_compound_fields():
    data = [
        {('angle', 'len'): (0, 0)},
        {('angle', 'len'): (0, 1)},
        {('angle', 'len'): (90, 1)},
        {('angle', 'len'): (180, 1)},
        {('angle', 'len'): (270, 1)},
    ]
    pattern_a = Dict(data, content=[
        DictField(
            Field(('angle', 'len'), count=5, optional=False),
            Tuple([v for d in data for v in d.values()], content=[
                TupleField(0, Int(Counter(v[0] for d in data for v in d.values()))),
                TupleField(1, Int(Counter(v[1] for d in data for v in d.values()))),
            ])
        ),
    ])
    data = [
        {(chr(ord('a') + i), chr(ord('a') + i + 1)): (i, i + 1)}
        for i in range(25)
    ]
    pattern_b = Dict(data, content=[
        DictField(
            Tuple([k for d in data for k in d], content=[
                TupleField(0, Str(Counter(k[0] for d in data for k in d),
                                  pattern=None)),
                TupleField(1, Str(Counter(k[1] for d in data for k in d),
                                  pattern=None)),
            ]),
            Tuple([v for d in data for v in d.values()], content=[
                TupleField(0, Int(Counter(v[0] for d in data for v in d.values()))),
                TupleField(1, Int(Counter(v[1] for d in data for v in d.values()))),
            ])
        ),
    ])
    assert pattern_a == pattern_b
    result = pattern_a + pattern_b
    assert len(result.content) == 1
    assert isinstance(result.content[0].key, Tuple)
    assert isinstance(result.content[0].value, Redo)
    # Test commutativity of mismatched merge
    assert pattern_b == pattern_a
    result = pattern_b + pattern_a
    assert len(result.content) == 1
    assert isinstance(result.content[0].key, Tuple)
    assert isinstance(result.content[0].value, Redo)


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
    assert xml(pattern).tag == 'tuple'
    pattern.validate(())
    with pytest.raises(TypeError):
        pattern.validate('foo')
    with pytest.raises(ValueError):
        pattern.validate((1, 2, 3, 4))


def test_tuple_with_pattern():
    data = [
        ('foo', 1),
        ('bar', 2),
        ('baz', 3),
    ]
    pattern = Tuple(data, content=[
        TupleField(
            Field(0, count=3, optional=False),
            Str([t[0] for t in data],
                pattern=[any_char, any_char, any_char])),
        TupleField(Field(1, count=3, optional=False), Int([t[1] for t in data])),
    ])
    assert pattern.size == 5
    assert pattern.lengths.min == 2
    assert pattern.lengths.max == 2
    assert str(pattern) == '(str pattern=..., int range=1..3)'
    assert repr(pattern) == (
        "Tuple(content=["
        "TupleField(value=Str(pattern=[AnyChar(), AnyChar(), AnyChar()], values=...)), "
        "TupleField(value=Int(values=...))])")
    assert iselement(xml(pattern).find('content'))
    assert iselement(xml(pattern).find('content').find('str'))


def test_tuple_with_long_pattern():
    book = namedtuple('book', ('author', 'title', 'published'))
    data = [
        book('J. R. R. Tolkien', 'The Fellowship of the Ring', '1954-07-29'),
        book('J. R. R. Tolkien', 'The Two Towers', '1954-11-11'),
        book('J. R. R. Tolkien', 'The Return of the King', '1955-10-20'),
    ]
    pattern = List([data], content=[Tuple(data, content=[
        TupleField(
            Field(0, count=3, optional=False),
            Str(Counter(t[0] for t in data), pattern=[CharClass(c) for c in 'J. R. R. Tolkien'])),
        TupleField(
            Field(1, count=3, optional=False),
            Str(Counter(t[1] for t in data), pattern=None)),
        TupleField(
            Field(2, count=3, optional=False),
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
        "], values=...)), "
        "TupleField(value=Str(pattern=None, values=...)), "
        "TupleField(value=StrRepr(content=DateTime(values=...), "
        "pattern='%Y-%m-%d'))"
        "])])"
    )
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Int(Counter((1, 2, 3)))
    with pytest.raises(TypeError):
        pattern + 100


def test_tuple_similar_matches():
    data = [
        ('foo', 1),
        ('bar', 2),
        ('baz', 3),
    ]
    pattern_a = Tuple(data, content=[
        TupleField(
            Field(0, count=3, optional=False),
            Str([t[0] for t in data],
                pattern=[any_char, any_char, any_char])),
        TupleField(Field(1, count=3, optional=False), Int([t[1] for t in data])),
    ])
    data = [
        ('foo', 1, False),
        ('bar', 2, False),
        ('baz', 3, True),
    ]
    pattern_b = Tuple(data, content=[
        TupleField(
            Field(0, count=3, optional=False),
            Str([t[0] for t in data],
                pattern=[any_char, any_char, any_char])),
        TupleField(Field(1, count=3, optional=False), Int([t[1] for t in data])),
        TupleField(Field(2, count=3, optional=False), Bool([t[2] for t in data])),
    ])
    assert pattern_a == pattern_b
    assert pattern_b == pattern_a
    result = pattern_a + pattern_b
    assert result.content[2].index.optional
    result = pattern_b + pattern_a
    assert result.content[2].index.optional


def test_tuple_disimilar_matches():
    data = [
        ('foo', 1),
        ('bar', 2),
        ('baz', 3),
    ]
    pattern_a = Tuple(data, content=[
        TupleField(
            Field(0, count=3, optional=False),
            Str([t[0] for t in data],
                pattern=[any_char, any_char, any_char])),
        TupleField(
            Field(1, count=3, optional=False),
            Int([t[1] for t in data])),
    ])
    data = [
        (1, 'foo', False),
        (2, 'bar', False),
        (3, 'baz', True),
    ]
    pattern_b = Tuple(data, content=[
        TupleField(
            Field(0, count=3, optional=False),
            Int([t[0] for t in data])),
        TupleField(
            Field(1, count=3, optional=False),
            Str([t[1] for t in data], pattern=[any_char, any_char, any_char])),
        TupleField(
            Field(2, count=3, optional=False),
            Bool([t[2] for t in data])),
    ])
    assert pattern_a != pattern_b
    assert pattern_b != pattern_a


def test_tuplefield_equality():
    t = TupleField(Field(0, 3), Int(Counter((1, 2, 3))))
    assert t == t
    assert not t == 'foo'


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
    assert xml(pattern).tag == 'list'
    pattern.validate([])
    with pytest.raises(TypeError):
        pattern.validate('foo')


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
    assert iselement(xml(pattern).find('content'))
    assert iselement(xml(pattern).find('content').find('int'))


def test_list_with_long_pattern():
    data = [
        [
            {'num': 1,  'label': 'foo',   'active': 't'},
            {'num': 2,  'label': 'bar',   'active': 't'},
            {'num': 3,  'label': 'baz'},
            {'num': 4,  'label': 'quux',  'active': 'f'},
            {'num': 5,  'label': 'xyzzy', 'active': 'f'},
            {'num': 6,  'label': 'six',   'active': 'f'},
            {'num': 7,  'label': 'seven'},
            {'num': 8,  'label': 'eight'},
            {'num': 9,  'label': 'nine'},
            {'num': 10, 'label': 'foo'},
        ]
    ]
    pattern = List(data, content=[Dict(
        data[0], content=[
            DictField(
                Field('active', count=5, optional=True),
                StrRepr(Bool(Counter({False, True})), pattern="f|t")),
            DictField(
                Field('label', count=9, optional=False),
                Str(Counter([
                    'foo', 'bar', 'baz', 'quux', 'xyzzy', 'six', 'seven',
                    'eight', 'nine', 'foo',
                ]), pattern=None)),
            DictField(
                Field('num', count=10, optional=False),
                Int(Counter(range(1, 11)))),
        ])])
    assert pattern.lengths.min == pattern.lengths.max == 10
    assert str(pattern) == """\
[
    {
        'active'*: str of bool pattern=f|t,
        'label': str,
        'num': int range=1..10
    }
]"""
    assert iselement(xml(pattern).find('content'))
    assert iselement(xml(pattern).find('content/dict'))
    assert iselement(xml(pattern).find(
        'content/dict/content/field/str/values/sample/more'))
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Int(Counter((1, 2, 3)))


def test_str():
    data = ['foo', 'bar', 'baz', 'quux']
    pattern = Str(Counter(data))
    assert pattern.lengths.min == 3
    assert pattern.lengths.max == 4
    assert pattern.pattern is None
    assert pattern.values.unique
    assert pattern.size == 1
    assert Counter(pattern.sample) == Counter(data)
    assert str(pattern) == 'str'
    assert xml(pattern).tag == 'str'
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Int(Counter((1, 2, 3)))
    with pytest.raises(TypeError):
        pattern + 100
    pattern.validate('blah')
    with pytest.raises(ValueError):
        pattern.validate('')


def test_fixed_str():
    data = ['0x{:04x}'.format(n) for n in range(1000)]
    pattern = Str(Counter(data), pattern=[
        CharClass('0'), CharClass('x'), CharClass('0'), CharClass('0'),
        hex_digit, hex_digit])
    assert pattern.lengths.min == pattern.lengths.max == 6
    assert pattern.values.unique
    assert str(pattern) == 'str pattern=0x00xx'
    pattern.validate('0x0012')
    with pytest.raises(ValueError):
        pattern.validate('0xff')
    with pytest.raises(ValueError):
        pattern.validate('foobar')
    with pytest.raises(ValueError):
        pattern.validate('0x00fg')


def test_str_repr():
    pattern = StrRepr(Int(Counter({1, 2, 3, 4})), pattern='d')
    assert str(pattern) == 'str of int range=1..4 pattern=d'
    assert xml(pattern).tag == 'strof'
    assert pattern.values.unique
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    pattern2 = StrRepr(DateTime(Counter((dt.datetime.now(),))), pattern='%Y-%m-%dT%H:%M:%S')
    assert pattern != pattern2
    pattern.validate('1')
    with pytest.raises(TypeError):
        pattern.validate(1)
    with pytest.raises(ValueError):
        pattern.validate('a')


def test_num_repr():
    pattern = NumRepr(DateTime(Counter((
        dt.datetime.utcfromtimestamp(0),
        dt.datetime.utcfromtimestamp(1),
        dt.datetime.utcfromtimestamp(86400),
    ))), pattern=Int)
    assert str(pattern) == 'int of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'
    assert xml(pattern).tag == 'intof'
    pattern = NumRepr(DateTime(Counter((
        dt.datetime.utcfromtimestamp(0.0),
        dt.datetime.utcfromtimestamp(1.0),
        dt.datetime.utcfromtimestamp(86400.0),
    ))), pattern=Float)
    assert str(pattern) == 'float of datetime range=1970-01-01 00:00:00..1970-01-02 00:00:00'
    assert xml(pattern).tag == 'floatof'
    assert pattern == pattern + pattern
    assert pattern + pattern == pattern
    assert pattern != Int(Counter((1, 2, 3)))


def test_int():
    data = {1, 2, 3, 1000}
    pattern = Int(Counter(data))
    assert pattern.size == 1
    assert str(pattern) == 'int range=1..1.0K'
    assert xml(pattern).tag == 'int'
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    with pytest.raises(TypeError):
        pattern + 100
    pattern.validate(5)
    with pytest.raises(TypeError):
        pattern.validate('1')
    with pytest.raises(ValueError):
        pattern.validate(2000)


def test_int_strrepr():
    data = {1, 2, 3, 1000}
    pattern = Int.from_strings(Counter(str(i) for i in data), 'd', 1)
    assert pattern == StrRepr(Int(Counter(data)), pattern='d')
    assert pattern.size == 1
    assert str(pattern) == 'str of int range=1..1.0K pattern=d'
    assert xml(pattern).tag == 'strof'
    assert iselement(xml(pattern).find('int'))
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Str(Counter(('a', 'b', 'c')))
    with pytest.raises(TypeError):
        pattern + 100
    pattern.validate('5')
    with pytest.raises(TypeError):
        pattern.validate(1)
    with pytest.raises(ValueError):
        pattern.validate('2000')


def test_float():
    data = {0.0, 1.0, 1000.0}
    pattern = Float(Counter(data))
    assert str(pattern) == 'float range=0..1000'
    assert xml(pattern).tag == 'float'
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Str(Counter(('a', 'b', 'c')))
    with pytest.raises(TypeError):
        pattern + 100
    pattern.validate(1.0)
    with pytest.raises(TypeError):
        pattern.validate('1.0')
    with pytest.raises(ValueError):
        pattern.validate(2000.0)


def test_float_strrepr():
    data = {0.0, 1.0, 1000.0}
    pattern = Float.from_strings(Counter(str(f) for f in data), 'f', 1)
    assert pattern == StrRepr(Float(Counter(data)), pattern='f')
    assert str(pattern) == 'str of float range=0..1000 pattern=f'
    assert xml(pattern).tag == 'strof'
    assert iselement(xml(pattern).find('float'))
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Str(Counter(('a', 'b', 'c')))
    with pytest.raises(TypeError):
        pattern + 100
    pattern.validate('1.0')
    with pytest.raises(TypeError):
        pattern.validate(1.0)
    with pytest.raises(ValueError):
        pattern.validate('2000.0')


def test_datetime():
    iso_fmt = '%Y-%m-%d %H:%M:%S'
    data = {
        dt.datetime.strptime('1970-01-01 00:00:00', iso_fmt),
        dt.datetime.strptime('1970-01-01 00:00:01', iso_fmt),
        dt.datetime.strptime('1970-01-02 00:00:00', iso_fmt),
        dt.datetime.strptime('1970-02-01 00:00:00', iso_fmt),
    }
    pattern = DateTime(Counter(data))
    assert pattern.size == 1
    assert str(pattern) == 'datetime range=1970-01-01 00:00:00..1970-02-01 00:00:00'
    assert xml(pattern).tag == 'datetime'
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Str(Counter(('a', 'b', 'c')))
    pattern.validate(datetime.strptime('1970-01-01 00:30:00', iso_fmt))
    with pytest.raises(TypeError):
        pattern.validate(86400)
    with pytest.raises(ValueError):
        pattern.validate(datetime.strptime('1980-01-01 00:00:00', iso_fmt))


def test_datetime_strrepr():
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
    assert pattern.size == 1
    assert str(pattern) == 'str of datetime range=1970-01-01 00:00:00..1970-02-01 00:00:00 pattern=%Y-%m-%d %H:%M:%S'
    assert xml(pattern).tag == 'strof'
    assert iselement(xml(pattern).find('datetime'))
    assert pattern + pattern == pattern
    assert pattern == pattern + pattern
    assert pattern != Str(Counter(('a', 'b', 'c')))
    pattern.validate('1970-01-01 00:30:00')
    with pytest.raises(TypeError):
        pattern.validate(86400)
    with pytest.raises(ValueError):
        pattern.validate('1980-01-01 00:00:00')


@pytest.mark.skipif(sys.maxsize <= 2**32, reason="requires 64-bit arch")
def test_datetime_numrepr():
    data = {
        dt.datetime.utcfromtimestamp(0),
        dt.datetime.utcfromtimestamp(1),
        dt.datetime.utcfromtimestamp(86400),
        dt.datetime.utcfromtimestamp(100000),
    }
    numbers = Int(Counter(d.timestamp() for d in data))
    pattern = DateTime.from_numbers(numbers)
    assert pattern == NumRepr(DateTime(Counter(data)), pattern=Int)
    pattern.validate(1000)
    with pytest.raises(TypeError):
        pattern.validate('1000')
    with pytest.raises(ValueError):
        pattern.validate(1200000)
    with pytest.raises(ValueError):
        pattern.validate(2000000000000)


@pytest.mark.skipif(sys.maxsize <= 2**32, reason="requires 64-bit arch")
def test_datetime_numrepr_epoch():
    excel_epoch = dt.datetime(1899, 12, 30)
    offset = (dt.datetime.utcfromtimestamp(0) - excel_epoch).total_seconds() // 86400
    data = {
        dt.datetime(1943, 7, 20),
        dt.datetime(1970, 1, 1),
        dt.datetime(1976, 1, 1),
    }
    numbers = Int(Counter(d.timestamp() + offset for d in data))
    pattern = DateTime.from_numbers(numbers, epoch=excel_epoch)
    assert pattern == NumRepr(DateTime(Counter(data)), pattern=Int)
    pattern.validate(1000)
    with pytest.raises(TypeError):
        pattern.validate('1000')
    with pytest.raises(ValueError):
        pattern.validate(200000000)
    with pytest.raises(ValueError):
        pattern.validate(2000000000000)


@pytest.mark.skipif(sys.maxsize <= 2**32, reason="requires 64-bit arch")
def test_datetime_strrepr_numrepr():
    data = {
        dt.datetime.utcfromtimestamp(0),
        dt.datetime.utcfromtimestamp(1),
        dt.datetime.utcfromtimestamp(86400),
        dt.datetime.utcfromtimestamp(100000),
    }
    numbers = StrRepr(Int(Counter(d.timestamp() for d in data)), pattern='d')
    pattern = DateTime.from_numbers(numbers)
    assert pattern == StrRepr(NumRepr(DateTime(Counter(data)), pattern=Int), pattern='d')
    pattern.validate('1000')
    with pytest.raises(ValueError):
        pattern.validate('2000000000')
    with pytest.raises(ValueError):
        pattern.validate('foo')

    numbers = StrRepr(Float(Counter(d.timestamp() for d in data)), pattern='f')
    pattern = DateTime.from_numbers(numbers)
    assert pattern == StrRepr(NumRepr(DateTime(Counter(data)), pattern=Float), pattern='f')
    pattern.validate('1000')
    pattern.validate('1000.0')
    with pytest.raises(ValueError):
        pattern.validate('1e9')
    with pytest.raises(ValueError):
        pattern.validate('foo')


def test_bool():
    pattern = Bool(Counter((False, True)))
    assert pattern.size == 1
    assert xml(pattern).tag == 'bool'
    assert pattern + pattern == pattern
    with pytest.raises(TypeError):
        pattern + 100
    pattern.validate(True)
    pattern.validate(1)
    with pytest.raises(ValueError):
        pattern.validate(2)
    with pytest.raises(TypeError):
        pattern.validate('true')


def test_bool_strrepr():
    pattern = Bool.from_strings(Counter(('f', 't')), 'f|t')
    assert pattern == StrRepr(Bool(Counter((False, True))), pattern='f|t')
    assert pattern.size == 1
    assert xml(pattern).tag == 'strof'
    assert iselement(xml(pattern).find('bool'))
    assert pattern + pattern == pattern
    with pytest.raises(TypeError):
        pattern + 100
    pattern.validate('t')
    with pytest.raises(ValueError):
        pattern.validate('true')
    with pytest.raises(TypeError):
        pattern.validate(True)


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
        dt.datetime.utcfromtimestamp(0),
        dt.datetime.utcfromtimestamp(1),
        dt.datetime.utcfromtimestamp(86400),
        dt.datetime.utcfromtimestamp(100000),
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
    pattern = URL(Counter(data), pattern=[
        CharClass(c) for c in 'http'] + [
        AnyChar() for c in 's://structa.readthedocs.io/'])
    assert str(pattern) == 'URL'
    assert xml(pattern).tag == 'url'
    pattern.validate('http://localhost.local')
    with pytest.raises(ValueError):
        pattern.validate('foo')
    with pytest.raises(ValueError):
        pattern.validate('httpf://localhost')
    with pytest.raises(TypeError):
        pattern.validate(100)


def test_field_of_scalar():
    f1 = Field('url', False)
    f2 = Field('url', False)
    f3 = Field('count', False)
    f4 = Field(4, False)
    t1 = Str(Counter({'aaa': 3, 'zzz': 1}), pattern=None)
    assert f1 == f2
    assert f1 + f2 == f1
    assert f2 != f3
    assert t1 == f1
    assert f1 == t1
    assert t1 != f4
    assert f4 != t1
    assert f1 + t1 == t1
    assert t1 + f1 == t1
    assert f3 < f2
    assert f2 > f3
    assert f4 < f1
    assert f1 > f4
    with pytest.raises(TypeError):
        f2 + f3
    with pytest.raises(TypeError):
        f2 < 'abc'
    with pytest.raises(TypeError):
        f2 > 'abc'
    assert f1 != 1


def test_field_of_tuples():
    f1 = Field(('a', 'b', 'c'), False)
    f2 = Field(('a', 'b', 'c'), False)
    f3 = Field(('d', 'e'), False)
    data = [
        ('foo', 'bar', 'baz'),
        ('bar', 'baz', 'foo'),
        ('baz', 'bar', 'foo'),
    ]
    t1 = Tuple(data, content=[
        TupleField(Field(0, count=3, optional=False),
                   Str([t[0] for t in data], pattern=None)),
        TupleField(Field(1, count=3, optional=False),
                   Str([t[1] for t in data], pattern=None)),
        TupleField(Field(2, count=3, optional=False),
                   Str([t[2] for t in data], pattern=None)),
    ])
    assert f1 == f2
    assert f1 + f2 == f1
    assert f2 != f3
    assert f1 == t1
    assert f1 + t1 == t1
    assert f2 < f3
    assert f3 > f2
    with pytest.raises(TypeError):
        f1 + f3
    with pytest.raises(TypeError):
        f1 < 'abc'
    with pytest.raises(TypeError):
        f1 > 'abc'
    assert f1 != 1


def test_fields():
    data = {'url'}
    pattern = Fields({Field(s, False) for s in data})
    assert str(pattern) == "<'url'>"
    assert len(pattern) == 1
    pattern.validate('url')
    with pytest.raises(ValueError):
        pattern.validate('foo')

    data = {'url', 'count', 'active'}
    pattern = Fields({Field(s, False) for s in data})
    assert set(s.strip("'") for s in str(pattern).strip('<>').split('|')) == data
    assert len(pattern) == 3
    pattern.validate('url')
    with pytest.raises(ValueError):
        pattern.validate('foo')
    with pytest.raises(ValueError):
        pattern.validate(1)


def test_value():
    pattern = Value(sample=[])
    assert str(pattern) == 'value'
    assert repr(pattern) == 'Value()'
    assert pattern.size == 1
    assert xml(pattern).tag == 'value'
    assert Value(sample=[]) == Value(sample=[1, 'foo'])
    assert Value(sample=[]) == Empty()
    assert Value(sample=[]) == Int(Counter((1, 2, 3)))
    assert Int(Counter((1, 2, 3))) == Value(sample=[])
    assert Value(sample=[]) != 'foo'
    assert Value(sample=[]) + Empty() == Value(sample=[])
    with pytest.raises(TypeError):
        Value(sample=[]) + 1
    pattern.validate(None)
    pattern.validate(1)
    pattern.validate('foo')


def test_redo():
    pattern = Redo(sample=[])
    assert repr(pattern) == 'Redo([])'


def test_empty():
    pattern = Empty()
    assert str(pattern) == ''
    assert repr(pattern) == 'Empty()'
    assert pattern.size == 0
    assert xml(pattern).tag == 'empty'
    assert Empty() == Empty()
    assert Empty() == Value(sample=[])
    assert Empty() == Int(Counter((1, 2, 3)))
    assert Int(Counter((1, 2, 3))) == Empty()
    assert Empty() != 'foo'
    assert Empty() + Value(sample=[]) == Value(sample=[])
    f = Field(value='foo', count=5, optional=False)
    assert Empty() + f == f
    assert (Empty() + f).optional
    f = Field(value='foo', count=5, optional=True)
    assert Empty() + f == f
    assert (Empty() + f).optional
    with pytest.raises(TypeError):
        Empty() + 1
    pattern.validate(None)
    pattern.validate(1)
    pattern.validate('foo')
