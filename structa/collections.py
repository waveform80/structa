from collections import Counter
from collections.abc import Mapping


class FrozenCounter(Mapping):
    def __init__(self, it):
        self._counter = Counter(it)
        self._hash = None

    @classmethod
    def from_counter(cls, counter):
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
        return self._counter.most_common(n)

    def elements(self):
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
        return self._counter == other

    def __ne__(self, other):
        return self._counter != other
