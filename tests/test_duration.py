import datetime as dt

import pytest

from dateutil.relativedelta import relativedelta
from structa.duration import *


def test_parse_duration():
    assert parse_duration('') == relativedelta(seconds=0)
    assert parse_duration('1 week') == relativedelta(days=7)
    assert parse_duration('1h') == relativedelta(hours=1)
    assert parse_duration('1hrs, 5mins') == relativedelta(hours=1, minutes=5)
    assert parse_duration('60 seconds') == relativedelta(minutes=1)
    with pytest.raises(ValueError):
        parse_duration('foo')


def test_parse_duration_or_timestamp():
    assert parse_duration_or_timestamp('') == relativedelta(seconds=0)
    assert parse_duration_or_timestamp('1 hour 30 minutes') == relativedelta(hours=1, minutes=30)
    assert parse_duration_or_timestamp('-1yr') == relativedelta(years=-1)
    assert parse_duration_or_timestamp('01:30:00') == dt.datetime.today().replace(
        hour=1, minute=30, second=0, microsecond=0)
    assert parse_duration_or_timestamp('2000-01-01 00:00:00') == dt.datetime(2000, 1, 1, 0, 0, 0)
