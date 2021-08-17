.. structa: an application for analyzing repetitive data structures
..
.. Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
..
.. SPDX-License-Identifier: GPL-2.0-or-later

==============
structa.chars
==============

.. module:: structa.chars

The :mod:`structa.chars` module provides classes and constants for defining
and manipulating character classes (in the sense of `regular expressions`_).
The primary class of interest is :class:`CharClass`, but most uses can likely
be covered by the set of constants defined in the module.

.. _regular expressions: https://en.wikipedia.org/wiki/Regular_expression

.. autoclass:: CharClass

.. autoclass:: AnyChar

.. autofunction:: char_range

Constants
=========

.. data:: oct_digit

    Represents any valid digit in base 8 (octal).

.. data:: dec_digit

    Represents any valid digit in base 10 (decimal).

.. data:: hex_digit

    Represents any valid digit in base 16 (hexidecimal).

.. data:: ident_first

    Represents any character which is valid as the first character of a
    Python identifier.

.. data:: ident_char

    Represents any character which is valid within a Python identifier.

.. data:: any_char

    Represents any valid character (an instance of :class:`AnyChar`).
