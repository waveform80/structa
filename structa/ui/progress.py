import sys
from datetime import datetime

import humanize
from blessings import Terminal


class FakeTerm:
    def __getattr__(self, key):
        return ''


class ProgressBar:
    def __init__(self):
        self.pos = 0
        self.size = 0

    def __format__(self, spec=''):
        if not spec:
            spec = '#.'
        return '{bar:{fill}<{size}}'.format(
            bar=spec[:1] * int(self.pos * self.size), fill=spec[-1:],
            size=self.size)


class ProgressSpin:
    def __init__(self):
        self.pos = 0
        self.inc = 1

    def __format__(self, spec=''):
        if not spec:
            spec = '|/-\\'
        self.pos += self.inc
        return spec[self.pos % len(spec)]


class Progress:
    def __init__(self, stream=sys.__stderr__,
                 format='{term.black_on_green}{pct:5.1f}% {eta}'
                 '{term.normal} {term.cyan}{bar:█ }{term.normal}',
                 force_styling=False):
        self.term = Terminal(stream=stream, force_styling=force_styling)
        self._bar = ProgressBar()
        self._spin = ProgressSpin()
        self._format = format
        self._started = None
        self._message = ''
        self._position = 0.0
        self._last_spinner = '-'

    def hide(self):
        self.term.stream.write(self.term.move_x(0) + self.term.clear_eol)
        if self._message:
            self.term.stream.write(self.term.move_up + self.term.clear_eol)
            self._message = ''

    def show(self, msg=None):
        if msg is not None:
            self.hide()
            if msg:
                self.term.stream.write(msg + '\n')
                self._message = msg
        else:
            self.term.stream.write(self.term.clear_bol + self.term.move_x(0))
        if self.term.does_styling:
            eta = ''
            if self._started is not None and self._position > 0.1:
                eta = ' {eta} remaining '.format(
                    eta=humanize.naturaldelta(
                        (1 - self._position) * (datetime.now() - self._started)
                        / self._position))
            self._bar.size = 0
            self._spin.inc = 0
            sample = self._format.format(
                term=FakeTerm(), eta=eta, spin=self._spin, bar=self._bar,
                pct=100 * self._position)
            self._bar.size = self.term.width - len(sample) - 1
            self._bar.pos = self._position
            self._spin.inc = 1
            self.term.stream.write(self._format.format(
                term=self.term, eta=eta, spin=self._spin, bar=self._bar,
                pct=100 * self._position))
        self.term.stream.flush()

    def message(self, msg):
        """
        Output the message *s* to the output stream.
        """
        self.show(msg)

    def reset_eta(self):
        """
        Reset the estimated time to finish; useful if multiple distinct tasks
        are being displayed in one block of :class:`Progress`.
        """
        self._started = None

    @property
    def position(self):
        """
        The progress of the activity; a floating-point value between 0.0
        (just begun) and 1.0 (finished). Set this property to update the
        progress bar.
        """
        return self._position

    @position.setter
    def position(self, value):
        if self._started is None:
            self._started = datetime.now()
        value = min(1.0, max(0.0, value))
        self._position = float(value)
        self.show()

    def __enter__(self):
        self._position = 0.0
        self._started = None
        return self

    def __exit__(self, *exc):
        self.hide()
        if self.term.stream:
            self.term.stream.flush()
