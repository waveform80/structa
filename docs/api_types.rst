.. structa: an application for analyzing repetitive data structures
..
.. Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
..
.. SPDX-License-Identifier: GPL-2.0-or-later

=============
structa.types
=============

.. module:: structa.types

The :mod:`structa.types` module defines the class hierarchy used to represent
the structural types of analyzed data. The root of the hierarchy is the
:class:`Type` class. The rest of the hierarchy is illustrated in the chart
below:

.. image:: images/types.*
   :align: center

.. autoclass:: Type

.. autoclass:: Container

.. autoclass:: Dict

.. autoclass:: Tuple

.. autoclass:: List

.. autoclass:: DictField

.. autoclass:: TupleField

.. autoclass:: Scalar

.. autoclass:: Float

.. autoclass:: Int

.. autoclass:: Bool

.. autoclass:: DateTime

.. autoclass:: Str

.. autoclass:: Repr

.. autoclass:: StrRepr

.. autoclass:: NumRepr

.. autoclass:: URL

.. autoclass:: Fields

.. autoclass:: Field

.. autoclass:: Value

.. autoclass:: Empty

.. autoclass:: Stats
