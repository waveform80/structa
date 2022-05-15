# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
import random
import hashlib
import datetime as dt
from itertools import count
from fractions import Fraction
from unittest import mock

import pytest

from structa.chars import *
from structa.types import *
from structa.analyzer import *


def frange(start, stop, step=1.0):
    assert step != 0.0
    for i in count():
        value = start + (i * step)
        if (
                (step > 0.0) and (value > stop) or
                (step < 0.0) and (value < stop)):
            break
        yield value


def test_flatten():
    assert list(flatten([1, 2, 3])) == [1, 2, 3, [1, 2, 3]]
    assert list(flatten([[1, 2], [3, 4], [5, 6]])) == [
        1, 2, [1, 2], 3, 4, [3, 4], 5, 6, [5, 6], [[1, 2], [3, 4], [5, 6]]]
    assert list(flatten({1: {2: {3: 4}}})) == [
        1, 2, 3, 4, {3: 4}, {2: {3: 4}}, {1: {2: {3: 4}}}]
    assert list(flatten('abc')) == ['abc']


def test_analyze_progress_trivial():
    progress = mock.Mock()
    a = Analyzer(bad_threshold=0, progress=progress)
    assert a.progress is progress
    data = 10
    a.measure(data)
    assert progress.reset.call_args == mock.call(total=1)
    assert progress.update.called
    progress.reset_mock()
    a.analyze(data)
    assert progress.reset.call_args == mock.call()
    assert progress.update.called


def test_analyze_progress():
    progress = mock.Mock()
    a = Analyzer(bad_threshold=0, progress=progress)
    data = [
        {'number': i}
        for i in range(1000)
    ]
    a.measure(data)
    assert progress.reset.call_args == mock.call(total=3001)
    assert progress.update.called
    progress.reset_mock()
    a.merge(a.analyze(data))
    assert progress.reset.call_args == mock.call()
    assert progress.update.called


def test_analyze_progress_partial():
    progress = mock.Mock()
    a = Analyzer(bad_threshold=0, progress=progress)
    data = [
        # Should be analyzed as { str: value } -- value cannot be counted by
        # the progress measurement as it doesn't store samples of the original
        # (because we can't guarantee they're hashable)
        {'number': i if i % 2 else str(i)}
        for i in range(1000)
    ]
    a.measure(data)
    assert progress.reset.call_args == mock.call(total=3001)
    assert progress.update.called
    progress.reset_mock()
    a.merge(a.analyze(data))
    assert progress.reset.call_args == mock.call()
    assert progress.update.called


def test_analyze_progress_dict():
    progress = mock.Mock()
    a = Analyzer(bad_threshold=0, progress=progress)
    data = {chr(ord('A') + n): n for n in range(50)}
    a.measure(data)
    assert progress.reset.call_args == mock.call(total=101)
    assert progress.update.called
    progress.reset_mock()
    a.analyze(data)
    assert progress.reset.call_args == mock.call()
    assert progress.update.called


def test_analyzer_scalar():
    data = 10
    a = Analyzer(bad_threshold=0)
    a.measure(data)
    assert a.analyze(data) == Int(sample=[data])


def test_analyze_list():
    data = list(range(100))
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data], content=[Int(FrozenCounter(data))])


def test_analyze_tuple():
    data = tuple(range(10))
    assert Analyzer(bad_threshold=0).analyze(data) == Tuple(
        sample=[data],
        content=[
            TupleField(
                index=Field(i, False),
                value=Int(FrozenCounter((i,)))
            )
            for i in range(10)
        ])
    data = tuple(range(100))
    assert Analyzer().analyze(data) == Tuple(
        sample=[data],
        content=[
            TupleField(
                index=Int(FrozenCounter(range(100))),
                value=Int(FrozenCounter(data)))
        ])


def test_analyze_dict():
    data = {chr(ord('A') + n): n for n in range(50)}
    assert Analyzer(bad_threshold=0).analyze(data) == Dict(
        sample=[data],
        content=[
            DictField(
                key=Str(FrozenCounter(data.keys()), pattern=[any_char]),
                value=Int(FrozenCounter(data.values()))
            )
        ])


def test_analyze_dict_optional_choices():
    data = [{'foo': 1, 'bar': 2}] * 999
    data.append({'foo': 1})
    assert Analyzer(bad_threshold=2/100).analyze(data) == List(
        sample=[data], content=[Dict(
            sample=data,
            content=[
                DictField(Field('bar', True), Int(Counter((2,) * 999))),
                DictField(Field('foo', False), Int(Counter((1,) * 1000))),
            ]
        )])


def test_analyze_dict_invalid_choices():
    data = [{chr(ord('A') + n): str(n) for n in range(50)}] * 99
    data.append({'foo': 'bar'})
    assert Analyzer(bad_threshold=1/100).analyze(data) == List(
        sample=[data], content=[Dict(
            sample=data,
            content=[
                DictField(
                    Str(Counter(k for d in data for k in d), pattern=None),
                    StrRepr(
                        Int(Counter(int(v) for d in data[:-1] for v in d.values())),
                        pattern='d'
                    )
                )
            ]
        )])


def test_analyze_dict_bad_data():
    data = {str(i): i for i in range(100)}
    data['a'] = 0
    assert Analyzer(bad_threshold=1/100).analyze(data) == Dict(
        sample=[data], content=[
            DictField(
                StrRepr(Int(Counter(range(100))), pattern='d'),
                Int(Counter(range(100)))
            )
        ])


def test_analyze_too_many_nulls():
    data = {str(i): i if i < 50 else None for i in range(100)}
    assert Analyzer().analyze(data) == Dict(
        sample=[data], content=[
            DictField(
                StrRepr(Int(Counter(range(100))), pattern='d'),
                Int(Counter(range(50)))
            )
        ])
    assert Analyzer(null_threshold=0).analyze(data) == Dict(
        sample=[data], content=[
            DictField(
                StrRepr(Int(Counter(range(100))), pattern='d'),
                Value(Counter(range(5)))
            )
        ])


def test_analyze_dict_of_dicts():
    data = {n: {'foo': n, 'bar': n} for n in range(99)}
    assert Analyzer().analyze(data) == Dict(
        sample=[data],
        content=[
            DictField(
                Int(Counter(data.keys())),
                Dict(
                    sample=data.values(),
                    content=[
                        DictField(Field('bar', False), Int(Counter(range(99)))),
                        DictField(Field('foo', False), Int(Counter(range(99)))),
                    ])
            )])



def test_analyze_dict_keyed_by_tuple():
    data = {
        (n, n + 1): n + 2
        for n in range(50)
    }
    assert Analyzer().analyze(data) == Dict(
        sample=[data],
        content=[
            DictField(
                Tuple(
                    sample=list(data.keys()),
                    content=[
                        TupleField(Field(0, False), Int(Counter(range(50)))),
                        TupleField(Field(1, False), Int(Counter(range(1, 51)))),
                    ]),
                Int(Counter(range(2, 52))))
        ])


def test_analyze_tuple_optional_fields():
    data = [
        (n, n + 1)
        for n in range(100)
    ]
    data.append((100,))
    assert Analyzer().analyze(data) == List(
        sample=[data],
        content=[Tuple(
            sample=data,
            content=[
                TupleField(Field(0, False), Int(Counter(range(101)))),
                TupleField(Field(1, True), Int(Counter(range(1, 101)))),
            ]
        )])


def test_analyze_namedtuples_optional_fields():
    t1 = namedtuple('t1', 'a b c')
    t2 = namedtuple('t2', 'a b')
    data = [
        t1(n, n + 1, n + 2)
        for n in range(100)
    ]
    data.append(t2(100, 101))
    assert Analyzer().analyze(data) == List(
        sample=[data],
        content=[Tuple(
            sample=data,
            content=[
                TupleField(Field(0, False), Int(Counter(range(101)))),
                TupleField(Field(1, False), Int(Counter(range(1, 102)))),
                TupleField(Field(2, True), Int(Counter(range(2, 102)))),
            ]
        )])


def test_analyze_lists_as_tuples():
    data = [
        [n, n + 1, n + 2]
        for n in range(100)
    ]
    assert Analyzer().analyze(data) == List(
        sample=[data],
        content=[Tuple(
            sample=data,
            content=[
                TupleField(Field(0, False), Int(Counter(range(100)))),
                TupleField(Field(1, False), Int(Counter(range(1, 101)))),
                TupleField(Field(2, False), Int(Counter(range(2, 102)))),
            ]
        )])


def test_analyze_bools():
    data = [bool(i % 2) for i in range(1000)]
    assert Analyzer(field_threshold=0).analyze(data) == List(
        sample=[data], content=[Bool(FrozenCounter(data))]
    )


def test_analyze_int_bases():
    data = [hex(n) for n in random.sample(range(1000000), 1000)]
    data.append('0xA')  # Ensure there's at least one value with an alpha char
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data], content=[Int.from_strings(Counter(data), pattern='x')]
    )


def test_analyze_fixed_oct_str():
    data = ['mode {:03o}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[Str(Counter(data), pattern=[
            CharClass('m'), CharClass('o'), CharClass('d'), CharClass('e'),
            CharClass(' '), oct_digit, oct_digit, oct_digit])
        ]
    )


def test_analyze_fixed_dec_str():
    data = ['num {:03d}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[Str(Counter(data), pattern=[
            CharClass('n'), CharClass('u'), CharClass('m'), CharClass(' '),
            dec_digit, dec_digit, dec_digit])
        ]
    )


def test_analyze_fixed_hex_str():
    data = ['hex {:02x}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[Str(Counter(data), pattern=[
            CharClass('h'), CharClass('e'), CharClass('x'), CharClass(' '),
            hex_digit, hex_digit])
        ]
    )


def test_analyze_datetimes():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    data = [
        dt.datetime.utcfromtimestamp(n).replace(microsecond=0)
        for n in frange(start, finish, step=86400.0)
    ]
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[DateTime(FrozenCounter(data))])


def test_analyze_datetime_str():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    dates = [
        dt.datetime.utcfromtimestamp(n).replace(microsecond=0)
        for n in frange(start, finish, step=86400.0)
    ]
    data = [date.strftime('%Y-%m-%d %H:%M:%S') for date in dates]
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[StrRepr(DateTime(Counter(dates)), pattern='%Y-%m-%d %H:%M:%S')])


@pytest.mark.xfail(sys.version_info < (3, 7),
                   reason='3.7+ datetime required for Z or +HH:MM timezones')
def test_analyze_datetime_str_varlen():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    dates = [
        dt.datetime.fromtimestamp(n, tz=dt.timezone.utc).replace(microsecond=0)
        for n in frange(start, finish, step=86400.0)
    ]
    data = [
        date.strftime('%Y-%m-%d %H:%M:%S') + ('Z', '+00:00')[i % 2]
        for i, date in enumerate(dates)
    ]
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[StrRepr(DateTime(Counter(dates)), pattern='%Y-%m-%d %H:%M:%S%z')])


def test_analyze_datetime_float():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    data = list(frange(start, finish, step=86400.0))
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[NumRepr(
            DateTime(Counter(dt.datetime.utcfromtimestamp(n) for n in data)),
            pattern=float)]
    )


def test_analyze_datetime_float_str():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    data = [str(f) for f in frange(start, finish, step=86400.0)]
    from pprint import pprint; pprint(data)
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[StrRepr(NumRepr(
            DateTime(Counter(dt.datetime.utcfromtimestamp(float(n)) for n in data)),
            pattern=float), pattern='f')]
    )


def test_analyze_datetime_bad_range():
    now = dt.datetime.now().timestamp()
    start = now - (1000 * 86400)
    finish = now + (1000 * 86400)
    randtime = lambda: random.random() * (finish - start) + start
    # Guarantee there's at least one value out of range
    data = {randtime() for n in range(99)} | {start}
    data = list(data)
    assert Analyzer(bad_threshold=0,
                    min_timestamp=dt.datetime.utcfromtimestamp(now),
                    max_timestamp=dt.datetime.utcfromtimestamp(finish)
                    ).analyze(data) == List(
        sample=[data],
        content=[Float(Counter(data))])


def test_analyze_any_value_list():
    data = (
        list(range(100)) +
        list(float(n) for n in range(100)) +
        list(chr(ord('A') + n) for n in range(26))
    )
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data], content=[Value(sample=data)])


def test_analyze_strs_with_blanks():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 10% of the data blank
    dates = [
        dt.datetime.utcfromtimestamp(randtime()).replace(microsecond=0)
        for n in range(90)
    ]
    data = [
        date.strftime('%Y-%m-%d %H:%M:%S') for date in dates
    ] + ['' for n in range(10)]
    random.shuffle(data)
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[StrRepr(DateTime(Counter(dates)),
                         pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_too_many_blanks():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 50% of the data blank
    data = [
        dt.datetime.utcfromtimestamp(randtime()).strftime('%Y-%m-%d %H:%M:%S')
        for n in range(50)
    ] + ['' for n in range(50)]
    random.shuffle(data)
    assert Analyzer(bad_threshold=0, empty_threshold=0.4).analyze(data) == List(
        sample=[data],
        content=[Str(Counter(data), pattern=None)])


def test_analyze_unique_list_with_bad_data():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=100)).timestamp()
    finish = now.timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 0.1% of the data invalid (oh noes! A MySQL dump!)
    dates = {
        dt.datetime.utcfromtimestamp(randtime()).replace(microsecond=0)
        for n in range(999)
    }
    data = {
        date.strftime('%Y-%m-%d %H:%M:%S') for date in dates
    } | {'2020-02-31 00:00:00'}
    data = list(data)
    random.shuffle(data)
    assert Analyzer(bad_threshold=0.02).analyze(data) == List(
        sample=[data],
        content=[StrRepr(DateTime(Counter(dates)),
                         pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_non_unique_list_with_bad_data():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=100)).timestamp()
    finish = now.timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    dates = [
        dt.datetime.utcfromtimestamp(randtime()).replace(microsecond=0)
        for n in range(100)
    ]
    dates = dates * 10
    data = [
        date.strftime('%Y-%m-%d %H:%M:%S') for date in dates
    ] + ['2020-02-31 00:00:00']
    random.shuffle(data)
    assert Analyzer(bad_threshold=Fraction(2, 1000)).analyze(data) == List(
        sample=[data],
        content=[StrRepr(DateTime(Counter(dates)),
                         pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_semi_unique_list_with_bad_data():
    ints = list(range(50)) * 10
    ints += list(range(51, 551))
    data = [str(i) for i in ints] + ['foobar']
    random.shuffle(data)
    assert Analyzer(bad_threshold=Fraction(2, 1000)).analyze(data) == List(
        sample=[data],
        content=[StrRepr(Int(Counter(ints)), pattern='d')])


def test_analyze_url_list():
    data = [
        'http://localhost/',
        'https://structa.readthedocs.io/',
        'https://picamera.readthedocs.io/',
        'https://pibootctl.readthedocs.io/',
        'https://lars.readthedocs.io/',
        'https://piwheels.org/',
        'https://ubuntu.com',
        'https://canonical.com',
        'https://google.com',
        'http://wikipedia.org/',
        'https://youtube.com/',
    ]
    assert Analyzer(field_threshold=5, bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[URL(FrozenCounter(data))])


def test_analyze_hashes():
    m = hashlib.sha1()
    data = [m.hexdigest()]
    for c in "Flat is better than nested\nSparse is better than dense":
        m.update(c.encode('ascii'))
        data.append(m.hexdigest())
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[Str(Counter(set(data)), pattern=[hex_digit] * 40)])


def test_analyze_strings():
    data = [
        "This goodly frame, the earth,",
        "seems to me a sterile promontory,",
        "this most excellent canopy, the air,"
        "look you, this brave o'erhanging firmament,",
        "this majestical roof fretted with golden fire,",
        "why, it appears no other thing to me than",
        "a foul and pestilent congregation of vapours.",
        "What a piece of work is a man!",
        "how noble in reason!",
        "how infinite in faculty!",
        "in form and moving how express and admirable!",
        "in action how like an angel!",
        "in apprehension how like a god!",
        "the beauty of the world!",
        "the paragon of animals!",
        "And yet, to me, what is this quintessence of dust?",
    ]
    assert Analyzer(field_threshold=5, bad_threshold=0).analyze(data) == List(
        sample=[data],
        content=[Str(FrozenCounter(data))])


def test_analyze_strings_with_strip():
    data = [
        (' ' * random.randint(0, 5)) +
        random.choice(('foo', 'bar', 'baz')) +
        (' ' * random.randint(0, 5))
        for i in range(1000)
    ]
    stripped = [s.strip() for s in data]
    assert Analyzer(field_threshold=0, bad_threshold=0,
                    strip_whitespace=True).analyze(data) == List(
        sample=[data],
        content=[Str(Counter(stripped),
                     pattern=[hex_digit, any_char, any_char])])


def test_analyze_empty():
    assert Analyzer().analyze([]) == List(sample=[[]], content=[Empty()])


def test_analyze_value():
    class Foo:
        __hash__ = None
    data = [Foo(), Foo(), Foo()]
    assert Analyzer().analyze(data) == List(
        sample=[data], content=[Value(sample=data)])


def test_analyze_merge_trivial():
    data = 10
    a = Analyzer(bad_threshold=0)
    struct = a.analyze(data)
    merged = a.merge(struct)
    assert struct == Int(sample=[data])
    assert struct == merged


def test_analyze_merge_tuples():
    data = {
        (i, i + 1): (chr(ord('a') + i), chr(ord('a') + i + 1))
        for i in range(25)
    }
    a = Analyzer()
    result = a.merge(a.analyze(data))
    print(result)
    assert a.merge(a.analyze(data)) == Dict(
        sample=[data],
        content=[
            DictField(
                Tuple(data.keys(), content=[
                    TupleField(
                        Field(0, False),
                        Int([k[0] for k in data])
                    ),
                    TupleField(
                        Field(1, False),
                        Int([k[1] for k in data])
                    ),
                ]),
                Tuple(data.values(), content=[
                    TupleField(
                        Field(0, False),
                        Str([v[0] for v in data.values()], pattern=[ident_first])
                    ),
                    TupleField(
                        Field(1, False),
                        Str([v[1] for v in data.values()], pattern=[ident_first])
                    ),
                ])
            )
        ]
    )


def test_analyze_merge_dict():
    releases = [
        'precise',
        'raring',
        'saucy',
        'trusty',
        'utopic',
        'vivid',
        'wily',
        'xenial',
        'yakkety',
        'zesty',
    ]
    data = {
        release: {
            'date': dt.datetime(2000, 1, 1) +
                    dt.timedelta(days=random.randint(1000, 2000)),
            'count': random.randint(1000, 2000),
            'name': release,
            'numbers': [
                random.randint(0, 10)
                for i in range(random.randint(1, 100))
            ],
        }
        for release in releases
    }
    a = Analyzer()
    assert a.merge(a.analyze(data)) == Dict(
        sample=[data],
        content=[
            DictField(
                key=Str(Counter(releases)),
                value=Dict(
                    sample=data,
                    content=[
                        DictField(
                            Field('count', False),
                            Int(Counter(r['count'] for r in data.values()))
                        ),
                        DictField(
                            Field('date', False),
                            DateTime(Counter(r['date'] for r in data.values()))
                        ),
                        DictField(
                            Field('name', False),
                            Str(Counter(r['name'] for r in data.values()))
                        ),
                        DictField(
                            Field('numbers', False),
                            List(
                                sample=[r['numbers'] for r in data.values()],
                                content=[
                                    Int(Counter(
                                        i for r in data.values()
                                        for i in r['numbers']
                                    ))
                                ]
                            )
                        ),
                    ]
                )
            )
        ]
    )


def test_analyze_merge_redo():
    data = {
        'id{i}'.format(i=i): {
            'count': i,
            'values': {
                chr(ord('a') + j): random.randint(1000, 2000)
                for j in range(i)
            }
        }
        for i in range(10)
    }
    a = Analyzer()
    assert a.merge(a.analyze(data)) == Dict(
        sample=[data],
        content=[
            DictField(
                Str(data.keys(), pattern=[CharClass('i'), CharClass('d'), AnyChar()]),
                Dict(
                    sample=data.values(),
                    content=[
                        DictField(
                            Field('count', False),
                            Int([d['count'] for d in data.values()])
                        ),
                        DictField(
                            Field('values', False),
                            Dict(
                                sample=[d['values'] for d in data.values()],
                                content=[
                                    DictField(
                                        Str([k for d in data.values() for k in d['values']], pattern=[AnyChar()]),
                                        Int([i for d in data.values() for i in d['values'].values()])
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            ),
        ]
    )
