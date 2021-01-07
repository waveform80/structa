import io
from datetime import datetime, timedelta
from unittest import mock

import pytest

from structa.ui.progress import *


@pytest.fixture()
def output(request):
    return io.StringIO()


@pytest.fixture()
def term(request, output):
    with mock.patch('structa.ui.progress.Terminal') as term:
        term().stream = output
        term().does_styling = True
        term().clear_bol = 'C'
        term().move_x.side_effect = lambda x: 'X%d' % x
        term().width = 40
        term().normal = 'N'
        term().black_on_green = 'Bg'
        yield term()


def test_progress_no_tty(output):
    with Progress(stream=output) as p:
        p.message('Foo')
    assert output.getvalue() == 'Foo\n'


def test_progress_tty(term, output):
    with Progress(show_percent=True, show_bar=True, show_eta=False) as p:
        p.message('Foo')
        assert p.position == 0.0
        p.position = 0.5
        assert p.position == 0.5
        p.position = 1.0
        assert p.position == 1.0
    assert output.getvalue() == (
        'CX0'
        'Foo\n'
        'X0Bg'
        '   0.0% '
        'N'
        '[.............................]'
        'X0Bg'
        '  50.0% '
        'N'
        '[##############...............]'
        'X0Bg'
        ' 100.0% '
        'N'
        '[#############################]'
        'CX0'
    )


def test_progress_eta(term, output):
    with mock.patch('structa.ui.progress.datetime') as dt, \
            Progress(show_percent=True, show_bar=False, show_eta=True) as p:
        now = datetime.now()
        dt.now.return_value = now
        p.message('Foo')
        p.position = 0.0
        dt.now.return_value = now + timedelta(seconds=5)
        p.position = 0.1
        dt.now.return_value = now + timedelta(seconds=25)
        p.position = 0.5
        dt.now.return_value = now + timedelta(seconds=45)
        p.position = 0.9
        dt.now.return_value = now + timedelta(seconds=50)
        p.position = 1.0
    assert output.getvalue() == (
        'CX0'
        'Foo\n'
        'X0Bg'
        '   0.0% '
        'N'
        'X0Bg'
        '   0.0% '
        'N'
        'X0Bg'
        '  10.0% '
        'N'
        'X0Bg'
        '  50.0% '
        ' 25 seconds remaining '
        'N'
        'X0Bg'
        '  90.0% '
        ' 5 seconds remaining '
        'N'
        'X0Bg'
        ' 100.0% '
        ' a moment remaining '
        'N'
        'CX0'
    )


def test_progress_reset_eta(term, output):
    with mock.patch('structa.ui.progress.datetime') as dt, \
            Progress(show_percent=True, show_bar=False, show_eta=True) as p:
        now = datetime.now()
        dt.now.return_value = now
        p.position = 0.0
        dt.now.return_value = now + timedelta(seconds=15)
        p.position = 0.25
        dt.now.return_value = now + timedelta(seconds=30)
        p.position = 0.5
        p.reset_eta()
        dt.now.return_value = now + timedelta(seconds=45)
        p.position = 0.75
        dt.now.return_value = now + timedelta(seconds=54)
        p.position = 0.9
        dt.now.return_value = now + timedelta(seconds=60)
        p.position = 1.0
    assert output.getvalue() == (
        'X0Bg'
        '   0.0% '
        'N'
        'X0Bg'
        '  25.0% '
        ' 45 seconds remaining '
        'N'
        'X0Bg'
        '  50.0% '
        ' 30 seconds remaining '
        'N'
        'X0Bg'
        '  75.0% '
        ' a moment remaining '
        'N'
        'X0Bg'
        '  90.0% '
        ' a second remaining '
        'N'
        'X0Bg'
        ' 100.0% '
        ' a moment remaining '
        'N'
        'CX0'
    )


def test_progress_spinner(term, output):
    with Progress(show_percent=False, show_bar=False, show_eta=False, show_spinner=True) as p:
        p.message('Foo')
        for i in range(5):
            p.position = i / 4
    assert output.getvalue() == (
        'CX0'
        'Foo\n'
        'X0Bg'
        'N'
        ' \\'
        'X0Bg'
        'N'
        ' |'
        'X0Bg'
        'N'
        ' /'
        'X0Bg'
        'N'
        ' -'
        'X0Bg'
        'N'
        ' \\'
        'X0Bg'
        'N'
        ' |'
        'CX0'
    )
