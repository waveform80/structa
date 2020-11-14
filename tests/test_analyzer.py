import random
import hashlib
import datetime as dt
from itertools import count
from fractions import Fraction

import pytest

from structa.chars import *
from structa.patterns import *
from structa.analyzer import Analyzer, ValidationWarning


def frange(start, stop, step=1.0):
    assert step != 0.0
    for i in count():
        value = start + (i * step)
        if (
                (step > 0.0) and (value > stop) or
                (step < 0.0) and (value < stop)):
            break
        yield value


def test_analyze_scalar():
    assert Analyzer().analyze(False) == Choices(
        {Choice(value=False, optional=False)})
    assert Analyzer().analyze(1) == Choices(
        {Choice(value=1, optional=False)})
    assert Analyzer().analyze(0.5) == Choices(
        {Choice(value=0.5, optional=False)})
    assert Analyzer().analyze('foo') == Choices(
        {Choice(value='foo', optional=False)})


def test_analyze_list():
    data = list(range(10))
    assert Analyzer().analyze(data) == List(
        sample=[data], pattern=[Choices(
            Choice(value=n, optional=False)
            for n in data
        )])
    data = list(range(100))
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data], pattern=[Int(sample=data, unique=True)])


def test_analyze_dict():
    data = {chr(ord('A') + n): n for n in range(10)}
    assert Analyzer().analyze(data) == Dict(
        sample=[data], pattern={
            Choice(value=key, optional=False):
            Choices({Choice(value=value, optional=False)})
            for key, value in data.items()
        })
    data = {chr(ord('A') + n): n for n in range(50)}
    assert Analyzer(bad_threshold=0).analyze(data) == Dict(
        sample=[data], pattern={
            Str(sample=data.keys(), pattern=(AnyChar,), unique=True):
            Int(sample=data.values(), unique=True)
        })


def test_analyze_dict_optional_chocies():
    data = [{'foo': 1, 'bar': 2}] * 999
    data.append({'foo': 1})
    assert Analyzer(bad_threshold=2/100).analyze(data) == List(
        sample=[data], pattern=[Dict(
            sample=data, pattern={
                Choice('bar', optional=True): Choices({Choice(2, optional=True)}),
                Choice('foo', optional=False): Choices({Choice(1, optional=False)}),
            }
        )]
    )


def test_analyze_dict_invalid_choices():
    data = [{chr(ord('A') + n): n for n in range(50)}] * 999
    data.append({'foo': 'bar'})
    with pytest.warns(ValidationWarning):
        assert Analyzer(bad_threshold=1/1000).analyze(data) == List(
            sample=[data], pattern=[Dict(
                sample=data, pattern={
                    Str(sample=[k for d in data[:-1] for k in d],
                        pattern=(AnyChar,), unique=False):
                    Int(sample=[v for d in data[:-1] for v in d.values()], unique=False)
                }
            )]
        )


def test_analyze_bools():
    data = [bool(i % 2) for i in range(1000)]
    assert Analyzer(choice_threshold=0).analyze(data) == List(
        sample=[data], pattern=[Bool(data)]
    )


def test_analyze_int_bases():
    data = [hex(n) for n in random.sample(range(1000000), 1000)]
    data.append('0xA')  # Ensure there's at least one value with an alpha char
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data], pattern=[Int.from_strings(data, pattern='x', unique=True)]
    )


def test_analyze_fixed_oct_str():
    data = ['mode {:03o}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(data, pattern=('m', 'o', 'd', 'e', ' ',
                                    OctDigit, OctDigit, OctDigit), unique=False)]
    )


def test_analyze_fixed_dec_str():
    data = ['num {:03d}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(data, pattern=('n', 'u', 'm', ' ',
                                    DecDigit, DecDigit, DecDigit), unique=False)]
    )


def test_analyze_fixed_hex_str():
    data = ['hex {:02x}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(data, pattern=('h', 'e', 'x', ' ',
                                    HexDigit, HexDigit), unique=False)]
    )


def test_analyze_datetimes():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    data = [
        dt.datetime.fromtimestamp(n).replace(microsecond=0)
        for n in frange(start, finish, step=86400.0)
    ]
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[DateTime(sample=data, unique=True)])


def test_analyze_datetime_str():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    dates = [
        dt.datetime.fromtimestamp(n).replace(microsecond=0)
        for n in frange(start, finish, step=86400.0)
    ]
    data = [date.strftime('%Y-%m-%d %H:%M:%S') for date in dates]
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[StrRepr(DateTime(sample=dates, unique=True),
                         pattern='%Y-%m-%d %H:%M:%S')])


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
        pattern=[StrRepr(DateTime(sample=dates, unique=True),
                         pattern='%Y-%m-%d %H:%M:%S%z')])


def test_analyze_datetime_float():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    data = list(frange(start, finish, step=86400.0))
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[NumRepr(
            DateTime(
                sample=[dt.datetime.fromtimestamp(n) for n in data],
                unique=True),
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
        pattern=[StrRepr(NumRepr(
            DateTime(
                sample=[dt.datetime.fromtimestamp(float(n)) for n in data],
                unique=True),
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
                    min_timestamp=dt.datetime.fromtimestamp(now),
                    max_timestamp=dt.datetime.fromtimestamp(finish)
                    ).analyze(data) == List(
        sample=[data],
        pattern=[Float(sample=data, unique=True)])


def test_analyze_any_value_list():
    data = (
        list(range(100)) +
        list(float(n) for n in range(100)) +
        list(chr(ord('A') + n) for n in range(26))
    )
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data], pattern=[Value()])


def test_analyze_strs_with_blanks():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 10% of the data blank
    dates = [
        dt.datetime.fromtimestamp(randtime()).replace(microsecond=0)
        for n in range(90)
    ]
    data = [
        date.strftime('%Y-%m-%d %H:%M:%S') for date in dates
    ] + ['' for n in range(10)]
    random.shuffle(data)
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[StrRepr(DateTime(sample=dates),
                         pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_too_many_blanks():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 50% of the data blank
    data = [
        dt.datetime.fromtimestamp(randtime()).strftime('%Y-%m-%d %H:%M:%S')
        for n in range(50)
    ] + ['' for n in range(50)]
    random.shuffle(data)
    assert Analyzer(bad_threshold=0, empty_threshold=0.4).analyze(data) == List(
        sample=[data],
        pattern=[Str(sample=set(data), pattern=None)])


def test_analyze_unique_list_with_bad_data():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=100)).timestamp()
    finish = now.timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 0.1% of the data invalid (oh noes! A MySQL dump!)
    dates = {
        dt.datetime.fromtimestamp(randtime()).replace(microsecond=0)
        for n in range(999)
    }
    data = {
        date.strftime('%Y-%m-%d %H:%M:%S') for date in dates
    } | {'2020-02-31 00:00:00'}
    data = list(data)
    random.shuffle(data)
    assert Analyzer(bad_threshold=0.02).analyze(data) == List(
        sample=[data],
        pattern=[StrRepr(DateTime(sample=dates, unique=True),
                         pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_non_unique_list_with_bad_data():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=100)).timestamp()
    finish = now.timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    dates = [
        dt.datetime.fromtimestamp(randtime()).replace(microsecond=0)
        for n in range(100)
    ]
    dates = dates * 10
    data = [
        date.strftime('%Y-%m-%d %H:%M:%S') for date in dates
    ] + ['2020-02-31 00:00:00']
    random.shuffle(data)
    assert Analyzer(bad_threshold=Fraction(2, 1000)).analyze(data) == List(
        sample=[data],
        pattern=[StrRepr(DateTime(sample=set(dates), unique=False),
                         pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_semi_unique_list_with_bad_data():
    ints = list(range(50)) * 10
    ints += list(range(51, 551))
    data = [str(i) for i in ints] + ['foobar']
    random.shuffle(data)
    assert Analyzer(bad_threshold=Fraction(2, 1000)).analyze(data) == List(
        sample=[data],
        pattern=[StrRepr(Int(sample=set(ints), unique=False), pattern='d')])


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
    assert Analyzer(choice_threshold=5, bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[URL(unique=True)])


def test_analyze_hashes():
    m = hashlib.sha1()
    data = [m.hexdigest()]
    for c in "Flat is better than nested\nSparse is better than dense":
        m.update(c.encode('ascii'))
        data.append(m.hexdigest())
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(sample=set(data), pattern=tuple([HexDigit] * 40),
                     unique=True)])


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
    assert Analyzer(choice_threshold=5, bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(sample=set(data), unique=True)])


def test_analyze_strings_with_strip():
    data = [
        (' ' * random.randint(0, 5)) +
        random.choice(('foo', 'bar', 'baz')) +
        (' ' * random.randint(0, 5))
        for i in range(1000)
    ]
    stripped = [s.strip() for s in data]
    assert Analyzer(choice_threshold=0, bad_threshold=0,
                    strip_whitespace=True).analyze(data) == List(
        sample=[data],
        pattern=[Str(sample=stripped, pattern=(HexDigit, AnyChar, AnyChar),
                     unique=False)])


def test_analyze_empty():
    assert Analyzer().analyze([]) == List(sample=[[]], pattern=[Empty()])


def test_analyze_value():
    class Foo:
        __hash__ = None
    data = [Foo(), Foo(), Foo()]
    assert Analyzer().analyze(data) == List(sample=[data], pattern=[Value()])
