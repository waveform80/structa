.. structa: an application for analyzing repetitive data structures
..
.. Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
..
.. SPDX-License-Identifier: GPL-2.0-or-later

================
structa.analyzer
================

.. module:: structa.analyzer

The :mod:`structa.analyzer` module contains the :class:`Analyzer` class which
is the primary entry point for using structa's as an API. It can be constructed
without any arguments, and the :meth:`~Analyzer.analyze` method can be
immediately used to determine the structure of some data. The
:meth:`~Analyzer.merge` method can be used to further refine the returned
structure, and :meth:`~Analyzer.measure` can be used before-hand if you wish to
use the *progress* callback to track the progress of long analysis runs.

A typical example of basic usage would be:

.. code-block:: python3

    from structa.analyzer import Analyzer

    data = {
        str(i): i
        for i in range(1000)
    }
    an = Analyzer()
    structure = an.analyze(data)
    print(structure)

The structure returned by :meth:`~Analyzer.analyze` (and by
:meth:`~Analyzer.merge`) will be an instance of one of the classes in the
:mod:`structa.types` module, all of which have sensible :class:`str` and
:func:`repr` output.

A more complete example, using :class:`~structa.source.Source` to figure out
the source format and encoding:

.. code-block:: python3

    from structa.analyzer import Analyzer
    from structa.source import Source
    from urllib.request import urlopen

    with urlopen('https://usn.ubuntu.com/usn-db/database-all.json') as f:
        src = Source(f)
        an = Analyzer()
        an.measure(src.data)
        structure = an.analyze(src.data)
        structure = an.merge(structure)
        print(structure)

.. autoclass:: Analyzer
