import random
import datetime as dt
from itertools import count

from structa.chars import *
from structa.patterns import *
from structa.analyzer import Analyzer


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
        sample=[len(data)], pattern=[Choices(
            Choice(value=n, optional=False)
            for n in data
        )])
    data = list(range(100))
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)], pattern=[Int(sample=data, unique=True)])


def test_analyze_dict():
    data = {chr(ord('A') + n): n for n in range(10)}
    assert Analyzer().analyze(data) == Dict(
        sample=[len(data)], pattern={
            Choice(value=key, optional=False):
            Choices({Choice(value=value, optional=False)})
            for key, value in data.items()
        })
    data = {chr(ord('A') + n): n for n in range(50)}
    assert Analyzer(bad_threshold=0).analyze(data) == Dict(
        sample=[len(data)], pattern={
            Str(sample=data.keys(), pattern=(AnyChar,), unique=True):
            Int(sample=data.values(), unique=True)
        })


def test_analyze_int_bases():
    data = [hex(n) for n in random.sample(range(1000000), 1000)]
    data.append('0xA')  # Ensure there's at least one value with an alpha char
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)], pattern=[Int.from_strings(data, base=16, unique=True)])


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
        sample=[len(data)],
        pattern=[DateTime(sample=dates, pattern='%Y-%m-%d %H:%M:%S', unique=True)])


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
        sample=[len(data)],
        pattern=[DateTime(sample=dates, pattern='%Y-%m-%d %H:%M:%S%z', unique=True)])


def test_analyze_datetime_float():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    data = list(frange(start, finish, step=86400.0))
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)],
        pattern=[DateTime(sample=data, pattern=float, unique=True)])


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
        sample=[len(data)],
        pattern=[Float(sample=data, unique=True)])


def test_analyze_any_value_list():
    data = (
        list(range(100)) +
        list(float(n) for n in range(100)) +
        list(chr(ord('A') + n) for n in range(26))
    )
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)], pattern=[Value()])


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
        sample=[len(data)],
        pattern=[DateTime(sample=dates, pattern='%Y-%m-%d %H:%M:%S')])


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
    assert Analyzer(bad_threshold=0, empty_threshold=40).analyze(data) == List(
        sample=[len(data)],
        pattern=[Str(sample=set(data), pattern=None)])


def test_analyze_datetime_with_bad_data():
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
    assert Analyzer(bad_threshold=2).analyze(data) == List(
        sample=[len(data)],
        pattern=[DateTime(sample=dates, pattern='%Y-%m-%d %H:%M:%S', unique=True)])

