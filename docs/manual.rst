.. structa: an application for analyzing repetitive data structures
..
.. Copyright (c) 2021 Dave Jones <dave@waveform.org.uk>
..
.. SPDX-License-Identifier: GPL-2.0-or-later

======================
Command Line Reference
======================

Synopsis
========

.. code-block:: text

    structa [-h] [--version] [-f {auto,csv,json,yaml}] [-e ENCODING]
            [--encoding-strict] [--no-encoding-strict]
            [-F INT] [-M NUM] [-B NUM] [-E NUM] [-N NUM] [--str-limit NUM]
            [--hide-count] [--show-count] [--hide-lengths] [--show-lengths]
            [--hide-pattern] [--show-pattern]
            [--hide-range] [--show-range {hidden,limits,median,quartiles,graph}]
            [--hide-samples] [--show-samples]
            [--min-timestamp WHEN] [--max-timestamp WHEN] [--epoch WHEN ]
            [--max-numeric-len LEN] [--sample-bytes SIZE]
            [--strip-whitespace] [--no-strip-whitespace]
            [--csv-format FIELD[QUOTE]] [--yaml-safe] [--no-yaml-safe]
            [file [file ...]]


.. program:: structa

Positional Arguments
====================

.. option:: file

    The data-file(s) to analyze; if this is - or unspecified then stdin will be
    read for the data; if multiple files are specified all will be read and
    analyzed as an array of similar structures

Optional Arguments
==================

.. option:: -h, --help

    show this help message and exit

.. option:: --version

    show program's version number and exit

.. option:: -f {auto,csv,json,yaml}, --format {auto,csv,json,yaml}

    The format of the data file; if this is unspecified, it will be guessed
    based on the first bytes of the file; valid choices are auto (the default),
    csv, or json

.. option:: -e ENCODING, --encoding ENCODING

    The string encoding of the file, e.g. utf-8 (default: auto). If "auto" then
    the file will be sampled to determine the encoding (see
    :option:`--sample-bytes`)

.. option:: --encoding-strict, --no-encoding-strict

    Controls whether character encoding is strictly enforced and will result in
    an error if invalid characters are found during analysis. If disabled, a
    replacement character will be inserted for invalid sequences. The default
    is strict decoding

.. option:: -F INT, --field-threshold INT

    If the number of distinct keys in a map, or columns in a tuple is less than
    this then they will be considered distinct fields instead of being lumped
    under a generic type like *str* (default: 20)

.. option:: -M NUM, --merge-threshold NUM

    The proportion of mapping fields which must match other mappings for them
    to be considered potential merge candidates (default: 50%)

.. option:: -B NUM, --bad-threshold NUM

    The proportion of string values which are allowed to mismatch a pattern
    without preventing the pattern from being reported; the proportion of "bad"
    data permitted in a field (default: 1%)

.. option:: -E NUM, --empty-threshold NUM

    The proportion of string values permitted to be empty without preventing
    the pattern from being reported; the proportion of "empty" data permitted
    in a field (default: 99%)

.. option:: -N NUM, --null-threshold NUM

    The proportion of values permitted to be null without preventing type
    analysis (default: 99%)

.. option:: --str-limit NUM

    The length beyond which only the lengths of strs will be reported; below
    this the actual value of the string will be displayed (default: 20)

.. option:: --hide-count, --show-count

    If set, show the count of items in containers, the count of unique scalar
    values, and the count of all sample values (if :option:`--show-samples` is
    set). If disabled, counts will be hidden

.. option:: --hide-lengths, --show-lengths

    If set, display the range of lengths of string fields in the same format as
    specified by :option:`--show-range`

.. option:: --hide-pattern, --show-pattern

    If set, show the pattern determined for fixed length string fields. If
    disabled, pattern information will be hidden

.. option:: --hide-range, --show-range {hidden,limits,median,quartiles,graph}

    Show the range of numeric (and temporal) fields in a variety of forms. The
    default is 'limits' which simply displays the minimum and maximum; 'median'
    includes the median between these; 'quartiles' shows all three quartiles
    between the minimum and maximum; 'graph' displays a crude chart showing the
    positions of the quartiles relative to the limits. Use
    :option:`--hide-range` to hide all range info

.. option:: --hide-samples, --show-samples

    If set, show samples of non-unique scalar values including the most and
    least common values. If disabled, samples will be hidden

.. option:: --min-timestamp WHEN

    The minimum timestamp to use when guessing whether floating point fields
    represent UNIX timestamps (default: 20 years). Can be specified as an
    absolute timestamp (in ISO-8601 format) or a duration to be subtracted from
    the current timestamp

.. option:: --max-timestamp WHEN

    The maximum timestamp to use when guessing whether floating point fields
    represent UNIX timestamps (default: 10 years). Can be specified as an
    absolute timestamp (in ISO-8601 format) or a duration to be added to the
    current timestamp

.. option:: --epoch WHEN

    The epoch from which datetimes are measured. Can be specified as an
    absolute timestamp (in ISO-8601 format: YYYY-mm-ddTHH:MM:SS), or one of the
    special strings, "unix" (which is equivalent to 1970-01-01) or
    "excel" (which is roughly equivalent to 1900-01-01, with some adjustments).
    The default is "unix"

.. option:: --max-numeric-len LEN

    The maximum number of characters that a number, integer or floating-point,
    may use in its representation within the file. Defaults to 30

.. option:: --sample-bytes SIZE

    The number of bytes to sample from the file for the purposes of encoding
    and format detection. Defaults to 1m. Typical suffixes of k, m, g, etc. may
    be specified

.. option:: --strip-whitespace, --no-strip-whitespace

    Controls whether leading and trailing found in strings in the will be left
    alone and thus included or excluded in any data-type analysis. The default
    is to strip whitespace

.. option:: --csv-format FIELD[QUOTE]

    The characters used to delimit fields and strings in a CSV file. Can be
    specified as a single character which will be used as the field delimiter,
    or two characters in which case the second will be used as the string
    quotation character. Can also be "auto" which indicates the delimiters
    should be detected. Bear in mind that some characters may require quoting
    for the shell, e.g. ';"'

.. option:: --yaml-safe, --no-yaml-safe

    Controls whether the "safe" or "unsafe" YAML loader is used to parse YAML
    files. The default is the "safe" parser. Only use :option:`--no-yaml-safe`
    if you trust the source of your data

.. option:: --json-strict, --no-json-strict

    Controls whether the JSON decoder permits control characters within
    strings, which isn't technically valid JSON. The default is to be strict
    and disallow such characters

