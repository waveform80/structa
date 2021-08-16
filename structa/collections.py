# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

from collections import Counter
from collections.abc import Mapping


class FrozenCounter(Mapping):
    """
    An immutable variant of the :class:`collections.Counter` class from the
    Python standard library.

    This implements all readable properties and behaviours of the
    :class:`collections.Counter` class, but excludes all methods and behaviours
    which permit modification of the counter. The resulting instances are
    hashable and can be used as keys in mappings.
    """
    def __init__(self, it):
        self._counter = Counter(it)
        self._hash = None

    @classmethod
    def from_counter(cls, counter):
        """
        Construct a :class:`FrozenCounter` from a :class:`collections.Counter`
        instance. This is generally much faster than attempting to construct
        from the elements of an existing counter.

        The *counter* parameter must either be a :class:`collections.Counter`
        instance, or a :class:`FrozenCounter` instance (in which case it is
        returned verbatim).
        """
        if isinstance(counter, Counter):
            self = cls(())
            self._counter = counter.copy()
            return self
        elif isinstance(counter, FrozenCounter):
            # It's frozen; no need to go recreating stuff
            return counter
        else:
            assert False

    def most_common(self, n=None):
        """
        See :meth:`collections.Counter.most_common`.
        """
        return self._counter.most_common(n)

    def elements(self):
        """
        See :meth:`collections.Counter.elements`.
        """
        return self._counter.elements()

    def __iter__(self):
        return iter(self._counter)

    def __len__(self):
        return len(self._counter)

    def __getitem__(self, key):
        return self._counter[key]

    def __repr__(self):
        return "{self.__class__.__name__}({self._counter})".format(self=self)

    def __hash__(self):
        if self._hash is None:
            self._hash = hash((frozenset(self), frozenset(self.values())))
        return self._hash

    def __eq__(self, other):
        if isinstance(other, FrozenCounter):
            return self._counter == other._counter
        elif isinstance(other, Counter):
            return self._counter == other
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, FrozenCounter):
            return self._counter != other._counter
        elif isinstance(other, Counter):
            return self._counter != other
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, FrozenCounter):
            return FrozenCounter.from_counter(self._counter + other._counter)
        elif isinstance(other, Counter):
            return FrozenCounter.from_counter(self._counter + other)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, FrozenCounter):
            return FrozenCounter.from_counter(self._counter - other._counter)
        elif isinstance(other, Counter):
            return FrozenCounter.from_counter(self._counter - other)
        return NotImplemented
