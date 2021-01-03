import sys
from datetime import datetime

import humanize
from blessings import Terminal


class Progress:
    def __init__(self, stream=sys.__stderr__, show_bar=True, show_percent=True,
                 show_eta=True, show_spinner=False):
        self.term = Terminal(stream=stream)
        self._show_bar = show_bar and self.term.is_a_tty
        self._show_percent = show_percent
        self._show_eta = show_eta
        self._show_spinner = show_spinner and self.term.is_a_tty
        self._started = None
        self._position = 0.0
        self._last_spinner = '-'

    def hide(self):
        if self.term.is_a_tty:
            self.term.stream.write(self.term.clear_bol + self.term.move_x(0))

    def show(self):
        if self.term.is_a_tty:
            eta = pct = bar = spin = ''
            if self._show_eta and self._started is not None and self._position > 0.1:
                eta = ' {eta} remaining '.format(
                    eta=humanize.naturaldelta(
                        (1 - self._position) * (datetime.now() - self._started)
                        / self._position))
            if self._show_percent:
                pct = ' {p:5.1f}% '.format(p=self._position * 100)
            if self._show_spinner:
                self._last_spinner = {
                    '|': '/',
                    '/': '-',
                    '-': '\\',
                    '\\': '|',
                }[self._last_spinner]
                spin = ' ' + self._last_spinner
            if self._show_bar:
                size = self.term.width - len(pct) - len(eta) - len(spin) - 3
                bar = '[{bar:.<{size}}]'.format(
                    size=size, bar='#' * int(size * self._position))
            self.term.stream.write(self.term.move_x(0))
            self.term.stream.write(self.term.black_on_green)
            self.term.stream.write(pct)
            self.term.stream.write(eta)
            self.term.stream.write(self.term.normal)
            self.term.stream.write(bar)
            self.term.stream.write(spin)
            self.term.stream.flush()

    def message(self, msg):
        """
        Output the message *s* to the output stream.
        """
        self.hide()
        if self.term.stream:
            self.term.stream.write(msg)
            self.term.stream.write('\n')
            if not self.term.is_a_tty:
                self.term.stream.flush()
        self.show()

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
