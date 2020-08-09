import random
import datetime as dt

from structa.chars import *
from structa.patterns import *
from structa.analyzer import Analyzer


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
        sample=[len(data)], pattern=[Int(sample=data)])


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
            Str(sample=data.keys(), pattern=(AnyChar,)):
            Int(sample=data.values())
        })


def test_analyze_int_bases():
    data = [hex(n) for n in random.sample(range(1000000), 1000)]
    data.append('0xA')  # Ensure there's at least one value with an alpha char
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)], pattern=[Int(sample=data, base=16)])


def test_analyze_datetime_str():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    data = [dt.datetime.fromtimestamp(randtime()).strftime('%Y-%m-%d %H:%M:%S')
            for n in range(100)]
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)],
        pattern=[DateTime(sample=data, pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_datetime_float():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    data = [randtime() for n in range(100)]
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)],
        pattern=[DateTime(sample=data, pattern=float)])


def test_analyze_datetime_bad_range():
    now = dt.datetime.now().timestamp()
    start = now - (1000 * 86400)
    finish = now + (1000 * 86400)
    randtime = lambda: random.random() * (finish - start) + start
    # Guarantee there's at least one value out of range
    data = [randtime() for n in range(100)] + [start]
    assert Analyzer(bad_threshold=0,
                    min_timestamp=dt.datetime.fromtimestamp(now),
                    max_timestamp=dt.datetime.fromtimestamp(finish)
                    ).analyze(data) == List(
        sample=[len(data)],
        pattern=[Float(sample=data)])


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
    data = [dt.datetime.fromtimestamp(randtime()).strftime('%Y-%m-%d %H:%M:%S')
            for n in range(100)] + ['' for n in range(10)]
    random.shuffle(data)
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[len(data)],
        pattern=[DateTime(sample=(s for s in data if s),
                          pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_too_many_blanks():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 50% of the data blank
    data = [dt.datetime.fromtimestamp(randtime()).strftime('%Y-%m-%d %H:%M:%S')
            for n in range(50)] + ['' for n in range(50)]
    random.shuffle(data)
    assert Analyzer(bad_threshold=0, empty_threshold=40).analyze(data) == List(
        sample=[len(data)],
        pattern=[Str(sample=set(data), pattern=None)])


def test_analyze_datetime_with_bad_data():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=1000)).timestamp()
    finish = (now + dt.timedelta(days=1000)).timestamp()
    randtime = lambda: random.random() * (finish - start) + start
    # Make 1% of the data invalid (oh noes! A MySQL dump!)
    data = [dt.datetime.fromtimestamp(randtime()).strftime('%Y-%m-%d %H:%M:%S')
            for n in range(99)] + ['2020-02-31 00:00:00']
    random.shuffle(data)
    assert Analyzer().analyze(data) == List(
        sample=[len(data)],
        pattern=[DateTime(sample=(s for s in data if s),
                          pattern='%Y-%m-%d %H:%M:%S')])
