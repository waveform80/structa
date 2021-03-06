import re

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from .collections import Counter, FrozenCounter


def try_conversion(sample, conversion, threshold=0):
    """
    Given a :class:`~collections.Counter` *sample* of strings, call the
    specified *conversion* on each string returning the set of converted
    values.

    *conversion* must be a callable that accepts a single string parameter and
    returns the converted value. If the *conversion* fails it must raise a
    :exc:`ValueError` exception.

    If *threshold* is specified (defaults to 0), it defines the number of
    "bad" conversions (which result in :exc:`ValueError` being raised) that
    will be ignored. If *threshold* is exceeded, then :exc:`ValueError` will
    be raised (or rather passed through from the underlying *conversion*).
    """
    assert isinstance(sample, (Counter, FrozenCounter))
    assert sample
    result = Counter()
    if threshold:
        assert threshold > 0
        for item, count in sample.items():
            try:
                result[conversion(item)] += count
            except ValueError: # XXX and TypeError?
                threshold -= count
                if threshold < 0:
                    raise
        if result:
            return result
        else:
            # If threshold permitted us to get to this point but we managed to
            # convert absolutely nothing, that's not success!
            raise ValueError('zero successful conversions')
    else:
        for item, count in sample.items():
            result[conversion(item)] += count
        return result


def parse_bool(s, false='0', true='1'):
    """
    Convert the string *s* (stripped and lower-cased) to a bool, if it matches
    either the *false* string (defaults to '0') or *true* (defaults to '1').
    If it matches neither, raises a :exc:`ValueError`.
    """
    try:
        return {
            false: False,
            true:  True,
        }[s.strip().lower()]
    except KeyError:
        raise ValueError('not a valid bool {!r}'.format(s))


_SUFFIXES = [
    # This ordering is important; the minutes regex must be checked *before*
    # the months regex as one is a legitimate subset of the other
    ('microseconds', 'm(icro)?s(ec(ond)?s?)?'),
    ('seconds',      's(ec(ond)?s?)?'),
    ('minutes',      'mi(n(ute)?s?)?'),
    ('hours',        'h((ou)?rs?)?'),
    ('days',         'd(ays?)?'),
    ('weeks',        'w(eeks?)?'),
    ('months',       'm(on(th)?s?)?'),
    ('years',        'y((ea)?rs?)?'),
]
_SPANS = [
    (span, re.compile(r'^(?:(?P<num>[+-]?\d+)\s*{}\b)'.format(suffix)))
    for span, suffix in _SUFFIXES
]


def parse_duration(s):
    spans = {span: 0 for span, regex in _SPANS}
    t = s
    while True:
        t = t.lstrip(' \t\n,')
        if not t:
            return relativedelta(**spans)
        for span, regex in _SPANS:
            m = regex.search(t)
            if m:
                spans[span] += int(m.group('num'))
                # XXX This only truncates from the start; that in turn means
                # that things must be ordered year/month/day/hour/etc. Make
                # the algorithm order agnostic
                t = t[len(m.group(0)):]
                break
        else:
            raise ValueError('invalid duration {}'.format(s))


def parse_duration_or_timestamp(s):
    try:
        return parse_duration(s)
    except ValueError:
        return parse(s)
