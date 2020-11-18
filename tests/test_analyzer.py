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
        sample=[data], pattern=[Int(sample=Counter(data))])


def test_analyze_tuple():
    data = tuple(range(10))
    defs = {
        Choice(i, False): Choices({Choice(i, False)})
        for i in range(10)
    }
    assert Analyzer().analyze(data) == Tuple(
        sample=[data],
        fields=tuple(defs.keys()),
        pattern=tuple(defs.values())
    )
    data = tuple(range(100))
    assert Analyzer().analyze(data) == Tuple(
        sample=[data],
        fields=(Int(sample=Counter(range(100))),),
        pattern=(Int(sample=Counter(data)),))


def test_analyze_namedtuple():
    book = namedtuple('book', ('author', 'title', 'published'))
    data = [
        book('J. R. R. Tolkien', 'The Hobbit', '1937-09-21'),
        book('J. R. R. Tolkien', 'The Fellowship of the Ring', '1954-07-29'),
        book('J. R. R. Tolkien', 'The Two Towers', '1954-11-11'),
        book('J. R. R. Tolkien', 'The Return of the King', '1955-10-20'),
        book('J. R. R. Tolkien', 'The Adventures of Tom Bombadil', '1962-11-22'),
    ]
    defs = (
        (Choice('author', False), Choices({Choice('J. R. R. Tolkien', False)})),
        (Choice('title', False), Str(Counter(b.title for b in data), pattern=None)),
        (Choice('published', False), StrRepr(
            DateTime(Counter(dt.datetime.strptime(b.published, '%Y-%m-%d') for b in data)),
            pattern='%Y-%m-%d'
        ))
    )
    assert Analyzer(choice_threshold=4).analyze(data) == List(
        sample=[data],
        pattern=[Tuple(
            sample=Counter(data),
            fields=tuple(i[0] for i in defs),
            pattern=tuple(i[1] for i in defs),
        )]
    )


def test_analyze_namedtuple_wide():
    t = namedtuple('t', tuple('field{:02d}'.format(i) for i in range(50)))
    data = t(*range(50))
    assert Analyzer().analyze(data) == Tuple(
        sample=[data],
        fields=(Str(sample=Counter(t._fields),
                    pattern=tuple('field') + (DecDigit, DecDigit)),),
        pattern=(Int(sample=Counter(data)),))


def test_analyze_dict():
    data = {chr(ord('A') + n): n for n in range(10)}
    fields = Choices(Choice(i, False) for i in data)
    assert Analyzer().analyze(data) == Dict(
        sample=[data],
        fields=fields,
        pattern=tuple(
            Choices({Choice(data[field.value], False)})
            for field in fields
        )
    )
    data = {chr(ord('A') + n): n for n in range(50)}
    assert Analyzer(bad_threshold=0).analyze(data) == Dict(
        sample=[data],
        fields={Str(sample=Counter(data.keys()), pattern=(AnyChar,))},
        pattern=(Int(sample=Counter(data.values())),)
    )


def test_analyze_dict_optional_chocies():
    data = [{'foo': 1, 'bar': 2}] * 999
    data.append({'foo': 1})
    fields = Choices(Choice(s, optional=(s == 'bar')) for s in data[0])
    assert Analyzer(bad_threshold=2/100).analyze(data) == List(
        sample=[data], pattern=[Dict(
            sample=data,
            fields=fields,
            pattern=tuple(
                Choices({Choice(data[0][field.value], field.optional)})
                for field in fields
            )
        )]
    )


def test_analyze_dict_invalid_choices():
    data = [{chr(ord('A') + n): n for n in range(50)}] * 99
    data.append({'foo': 'bar'})
    with pytest.warns(ValidationWarning):
        assert Analyzer(bad_threshold=1/100).analyze(data) == List(
            sample=[data], pattern=[Dict(
                sample=data,
                fields={Str(sample=Counter(k for d in data[:-1] for k in d),
                            pattern=(AnyChar,))},
                pattern=(Int(sample=Counter(v for d in data[:-1] for v in d.values())),)
            )]
        )


def test_analyze_dict_of_dicts():
    data = {n: {'foo': n, 'bar': n} for n in range(99)}
    fields = Choices(Choice(s, False) for s in data[0])
    assert Analyzer().analyze(data) == Dict(
        sample=[data],
        fields={Int(sample=Counter(data.keys()))},
        pattern=(
            Dict(
                sample=data.values(),
                fields=fields,
                pattern=(
                    Int(sample=Counter(range(99))),
                    Int(sample=Counter(range(99))),
                )
            ),
        )
    )


def test_analyze_dict_keyed_by_tuple():
    data = {
        (n, n + 1): n + 2
        for n in range(50)
    }
    defs = {
        Choice(0, False): Int(Counter(range(50))),
        Choice(1, False): Int(Counter(range(1, 51))),
    }
    assert Analyzer().analyze(data) == Dict(
        sample=[data],
        fields={Tuple(
            sample=list(data.keys()),
            fields=tuple(defs.keys()),
            pattern=tuple(defs.values()),
        )},
        pattern=(Int(Counter(range(2, 52))),)
    )


def test_analyze_tuple_optional_fields():
    data = [
        (n, n + 1)
        for n in range(100)
    ]
    data.append((100,))
    assert Analyzer().analyze(data) == List(
        sample=[data],
        pattern=[Tuple(
            sample=data,
            fields=(
                Choice(0, False),
                Choice(1, True),
            ),
            pattern=(
                Int(sample=Counter(range(101))),
                Int(sample=Counter(range(1, 101))),
            )
        )]
    )


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
        pattern=[Tuple(
            sample=data,
            fields=(
                Choice('a', False),
                Choice('b', False),
                Choice('c', True),
            ),
            pattern=(
                Int(sample=Counter(range(101))),
                Int(sample=Counter(range(1, 102))),
                Int(sample=Counter(range(2, 102))),
            )
        )]
    )


def test_analyze_tuple_and_namedtuple():
    t = namedtuple('t1', 'a b c')
    data = [
        t(n, n + 1, n + 2)
        for n in range(100)
    ]
    data.append((100, 101, 102))
    assert Analyzer().analyze(data) == List(
        sample=[data],
        pattern=[Tuple(
            sample=data,
            fields=(
                Choice(0, True),
                Choice(1, True),
                Choice(2, True),
            ),
            pattern=(
                Int(sample=Counter(range(101))),
                Int(sample=Counter(range(1, 102))),
                Int(sample=Counter(range(2, 103))),
            )
        )]
    )


def test_analyze_lists_as_tuples():
    data = [
        [n, n + 1, n + 2]
        for n in range(100)
    ]
    assert Analyzer().analyze(data) == List(
        sample=[data],
        pattern=[Tuple(
            sample=data,
            fields=(
                Choice(0, False),
                Choice(1, False),
                Choice(2, False),
            ),
            pattern=(
                Int(sample=Counter(range(100))),
                Int(sample=Counter(range(1, 101))),
                Int(sample=Counter(range(2, 102))),
            )
        )]
    )


def test_analyze_bools():
    data = [bool(i % 2) for i in range(1000)]
    assert Analyzer(choice_threshold=0).analyze(data) == List(
        sample=[data], pattern=[Bool(Counter(data))]
    )


def test_analyze_int_bases():
    data = [hex(n) for n in random.sample(range(1000000), 1000)]
    data.append('0xA')  # Ensure there's at least one value with an alpha char
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data], pattern=[Int.from_strings(Counter(data), pattern='x')]
    )


def test_analyze_fixed_oct_str():
    data = ['mode {:03o}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(Counter(data), pattern=('m', 'o', 'd', 'e', ' ',
                                    OctDigit, OctDigit, OctDigit))]
    )


def test_analyze_fixed_dec_str():
    data = ['num {:03d}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(Counter(data), pattern=('n', 'u', 'm', ' ',
                                    DecDigit, DecDigit, DecDigit))]
    )


def test_analyze_fixed_hex_str():
    data = ['hex {:02x}'.format(n) for n in range(256)] * 10
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[Str(Counter(data), pattern=('h', 'e', 'x', ' ',
                                    HexDigit, HexDigit))]
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
        pattern=[DateTime(Counter(data))])


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
        pattern=[StrRepr(DateTime(Counter(dates)), pattern='%Y-%m-%d %H:%M:%S')])


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
        pattern=[StrRepr(DateTime(Counter(dates)), pattern='%Y-%m-%d %H:%M:%S%z')])


def test_analyze_datetime_float():
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=50)).timestamp()
    finish = (now + dt.timedelta(days=50)).timestamp()
    data = list(frange(start, finish, step=86400.0))
    assert Analyzer(bad_threshold=0).analyze(data) == List(
        sample=[data],
        pattern=[NumRepr(
            DateTime(Counter(dt.datetime.fromtimestamp(n) for n in data)),
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
            DateTime(Counter(dt.datetime.fromtimestamp(float(n)) for n in data)),
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
        pattern=[Float(Counter(data))])


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
        pattern=[StrRepr(DateTime(Counter(dates)),
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
        pattern=[Str(Counter(data), pattern=None)])


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
        pattern=[StrRepr(DateTime(sample=Counter(dates)),
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
        pattern=[StrRepr(DateTime(sample=Counter(dates)),
                         pattern='%Y-%m-%d %H:%M:%S')])


def test_analyze_semi_unique_list_with_bad_data():
    ints = list(range(50)) * 10
    ints += list(range(51, 551))
    data = [str(i) for i in ints] + ['foobar']
    random.shuffle(data)
    assert Analyzer(bad_threshold=Fraction(2, 1000)).analyze(data) == List(
        sample=[data],
        pattern=[StrRepr(Int(sample=Counter(ints)), pattern='d')])


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
        pattern=[Str(sample=Counter(set(data)), pattern=tuple([HexDigit] * 40))])


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
        pattern=[Str(sample=Counter(set(data)))])


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
        pattern=[Str(sample=Counter(stripped),
                     pattern=(HexDigit, AnyChar, AnyChar))])


def test_analyze_empty():
    assert Analyzer().analyze([]) == List(sample=[[]], pattern=[Empty()])


def test_analyze_value():
    class Foo:
        __hash__ = None
    data = [Foo(), Foo(), Foo()]
    assert Analyzer().analyze(data) == List(sample=[data], pattern=[Value()])
