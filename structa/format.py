from math import log


def format_int(i):
    """
    Reduce *i* by some appropriate power of 1000 and suffix it with an
    appropriate Greek qualifier (K for kilo, M for mega, etc.)
    """
    suffixes = ('', 'K', 'M', 'G', 'T', 'P')
    try:
        index = min(len(suffixes) - 1, int(log(abs(i), 1000)))
    except ValueError:
        return '0'
    if not index:
        return str(i)
    else:
        return '{value:.1f}{suffix}'.format(
            value=(i / 1000 ** index),
            suffix=suffixes[index])


def format_repr(self, **override):
    args = (
        arg
        for cls in self.__class__.mro() if cls is not object
        for arg in cls.__slots__
    )
    return '{self.__class__.__name__}({args})'.format(
        self=self, args=', '.join(
            '{arg}={value}'.format(
                arg=arg, value=override.get(arg, repr(getattr(self, arg))))
            for arg in args
            if arg not in override
            or override[arg] is not None))
