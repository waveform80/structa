from collections import Counter

import pytest

from structa.collections import *


def test_frozencounter_construction():
    a = FrozenCounter((1, 1, 1))
    b = FrozenCounter((1, 2, 3))
    assert a.keys() == {1}
    assert a[1] == 3
    assert b.keys() == {1, 2, 3}
    assert len(b) == 3
    assert sorted(b) == [1, 2, 3]
    assert tuple(b.values()) == (1,) * 3


def test_frozencounter_hashable():
    c = Counter((1, 2, 3) * 100 + (4, 5) * 50)
    f = FrozenCounter(c)
    d = {f: 1}
    assert d[f] == 1


def test_frozencounter_repr():
    c = Counter((1, 2, 3) * 100 + (4, 5) * 50)
    f = FrozenCounter(c)
    assert repr(f) == 'FrozenCounter({c!r})'.format(c=c)


def test_frozencounter_comparisons():
    c = Counter((1, 2, 3) * 100 + (4, 5) * 50)
    f = FrozenCounter(c)
    assert c == f
    c[6] = 1
    assert c != f
    assert f == f
    assert not (f != f)
    assert not (f == None)
    assert f != None


def test_frozencounter_operations():
    a = FrozenCounter((1, 1, 1))
    b = Counter((1, 2, 3))
    c = Counter((1, 1, 1, 1, 2, 3))
    assert a + b == c
    assert a + FrozenCounter.from_counter(b) == c
    with pytest.raises(TypeError):
        a + 0
    c = FrozenCounter.from_counter(c)
    assert c - a == b
    assert c - b == a
    with pytest.raises(TypeError):
        a - 0


def test_frozencounter_elements():
    c = Counter((1, 2, 3) * 100 + (4, 5) * 50)
    f = FrozenCounter(c)
    assert Counter(c.elements()) == Counter(f.elements())
    c[6] = 1
    assert Counter(c.elements()) != Counter(f.elements())


def test_frozencounter_from_counter():
    c = Counter((1, 2, 3) * 100 + (4, 5) * 50)
    f = FrozenCounter(c)
    with pytest.raises(AssertionError):
        FrozenCounter.from_counter({})
    assert FrozenCounter.from_counter(c)._counter is not c
    assert FrozenCounter.from_counter(f) is f
