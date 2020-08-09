import re

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta


_SUFFIXES = [
    # This ordering is important; the minutes regex must be checked *before*
    # the months regex as one is a legitimate subset of the other
    ('microseconds', 'm(icro)?s(ec(ond)?s?)?'),
    ('seconds',      's(ec(ond)?s?)?'),
    ('minutes',      'mi(n(ute)?s?)?'),
    ('hours',        'h((ou)?rs?)?'),
    ('days',         'd(ays?)?'),
    ('weeks',        'w(eeks?)?'),
    ('months',       'm(onths?)?'),
    ('years',        'y(ears?)?'),
]
_SPANS = [
    (span, re.compile('^(?:(?P<num>[+-]?\d+)\s*{})'.format(suffix)))
    for span, suffix in _SUFFIXES
]


def parse_duration(s):
    spans = {span: 0 for span, regex in _SPANS}
    t = s
    while True:
        t = t.lstrip()
        if not t:
            return relativedelta(**spans)
        for span, regex in _SPANS:
            m = regex.search(t)
            if m:
                spans[span] += int(m.group('num'))
                t = t[len(m.group(0)):]
                break
        else:
            raise ValueError('invalid duration {}'.format(s))


def parse_duration_or_timestamp(s):
    try:
        return parse_duration(s)
    except ValueError:
        return parse(s)