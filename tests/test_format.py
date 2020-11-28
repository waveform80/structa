import datetime as dt
from collections import namedtuple, Counter

import pytest

from structa.format import *


def test_format_int():
    assert format_int(0) == '0'
    assert format_int(1) == '1'
    assert format_int(999) == '999'
    assert format_int(-999) == '-999'
    assert format_int(1000) == '1.0K'
    assert format_int(-1000) == '-1.0K'
    assert format_int(999900) == '999.9K'
    assert format_int(1000000) == '1.0M'
