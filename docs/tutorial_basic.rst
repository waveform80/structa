.. structa: an application for analyzing repetitive data structures
..
.. Copyright (c) 2021 Dave Jones <dave@waveform.org.uk>
..
.. SPDX-License-Identifier: GPL-2.0-or-later

===============
Getting Started
===============

.. warning::

    Big fat "unfinished" warning: structa is still very much incomplete at this
    time and there's plenty of rough edges (like not showing CSV column
    titles).

    If you run into unfinished stuff, do check the `issues`_ first as I may
    have a ticket for that already. If you run into genuinely "implemented but
    broken" stuff, please do file an issue; it's these things I'm most
    interested in at this stage.

.. _issues: https://github.com/waveform80/structa/issues

Getting the most out of structa is part science, part art. The science part is
understanding how structa works and what knobs it has to twiddle. The art bit
is figuring out what to twiddle them to!


Pre-requisites
==============

You'll need the following to start this tutorial:

* A structa installation; see :doc:`install` for more information on this.

* A Python 3 installation; given that structa requires this to run at all, if
  you've got structa installed, you've got this too. However, it'll help
  enormously if Python is in your system's "PATH" so that you can run python
  scripts at the command line.

* Some basic command line knowledge. In particular, it'll help if you're
  familiar with `shell redirection and piping`_ (note: while that link is on
  `askubuntu.com`_ the contents are equally applicable to the vast majority of
  UNIX shells, and even to Windows' cmd!)

.. _shell redirection and piping: https://askubuntu.com/a/172989
.. _askubuntu.com: https://askubuntu.com/


Basic Usage
===========

We'll start with some basic data structures and see how structa handles them.
The following Python script dumps a list of strings representing integers to
stdout in JSON format:

.. literalinclude:: examples/str-nums.py
   :caption: str-nums.py

This produces output that looks (partially) like this:

.. code-block:: js

    ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13",
    "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
    "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
    "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
    "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
    "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85",
    "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97",
    "98", "99", "100", "101", "102", "103", "104", "105", "106", "107", "108",
    "109", "110", "111", "112", "113", "114", "115", "116", "117", "118",
    "119", "120", "121", "122", "123", "124", "125", "126", "127", "128",
    "129", "130",
    // lots more output...
    ]

We can capture the output in a file and pass this to structa:

.. code-block:: console

    $ python3 str-nums.py > str-nums.json
    $ structa str-nums.json
    [ str of int range=0..999 pattern="d" ]

Alternatively, we can pipe the output straight to structa:

.. code-block:: console

    $ python3 str-nums.py | structa
    [ str of int range=0..999 pattern="d" ]

The output shows that the data contains a list (indicated by the
square-brackets surrounding the output) of strings of integers ("str of int"),
which have values between 0 and 999 (inclusive). The "pattern" at the end
indicates that the strings are in decimal ("d") form (structa would also
recognize octal, "o", and hexadecimal "x" forms of integers).


Bad Data (``--bad-threshold``)
==============================

Let's see how structa handles bad data. We'll add a non-numeric string into our
list of numbers:

.. literalinclude:: examples/bad-nums.py
   :caption: bad-nums.py

What does structa do in the presence of this "corrupt" data?

.. code-block:: console

    $ python3 bad-nums.py | structa
    [ str of int range=0..999 pattern="d" ]

Apparently nothing! It may seem odd that structa raised no errors, or even
warnings when encountering subtly incorrect data. However, structa has a "bad
threshold" setting (:option:`structa --bad-threshold`) which means not all data
in a given sequence has to match the pattern under test.

This setting defaults to 1% (or 0.01) meaning that up to 1% of the values can
fail to match and the pattern will still be considered valid. If we lower the
bad threshold to zero, this is what happens:

.. code-block:: console

    $ python3 bad-nums.py | structa --bad-threshold 0
    [ str range="0".."foo" ]

It's still recognized as a list of strings, but no longer as string
representations of integers.

How about mixing types? The following script outputs our errant string, "foo",
along with a list of numbers. However, note that this time the numbers are
integers, not strings of integers. In other words we have a list of a string,
and lots of integers:

.. literalinclude:: examples/bad-types.py
   :caption: bad-types.py

.. code-block:: console

    $ python3 bad-types.py | structa
    [ value ]

In this case, even with the default 1% bad threshold, structa doesn't exclude
the bad data; the analysis simply returns it as a list of mixed "values".

This is because structa assumes that the *types* of data are at least
consistent and correct, under the assumption that if whatever is generating
your data hasn't even got the data types right, you've got bigger problems! The
bad threshold mechanism only applies to bad data *within* a homogenous type
(typically bad string representations of numeric or boolean types).


Missing Data (``--empty-threshold``)
====================================

Another type of "bad" data commonly encountered is empty strings which are
typically used to represent *missing* data, and (predictably) structa has
another knob that can be twiddled for this: :option:`structa
--empty-threshold`. The following script generates a list of strings of
integers in which most of the strings (~70%) are blank:

.. literalinclude:: examples/mostly-blank.py
   :caption: mostly-blank.py

Despite the vast majority of the data being blank, structa handles this as
normal:

.. code-block:: console

    $ python3 mostly-blank.py | structa
    [ str of int range=0..100 pattern="d" ]

This is because the default for :option:`structa --empty-threshold` is 99% or
0.99. If the proportion of blank strings in a field exceeds the empty
threshold, the field will simply be marked as a string without any further
processing. Hence, when we re-run this script with the setting turned down to
50%, the output changes:

.. code-block:: console

    $ python3 mostly-blank.py | structa --empty-threshold 50%
    [ str range="".."99" ]

.. note::

    For those slightly confused by the above output: structa hasn't lost the
    "100" value, but because it's now considered a string (not a string of
    integers), "100" sorts before "99" alphabetically.


Fields or Tables (``--field-threshold``)
========================================

The next major knob that can be twiddled in structa is the :option:`structa
--field-threshold`. This is used to distinguish between mappings that act as a
"table" (mapping keys to records) and mappings that act as a record (mapping
field-names, typically strings, to their values).

To illustrate the difference between these, consider the following script:

.. literalinclude:: examples/simple-fields.py
   :caption: simple-fields.py

The generates a JSON file containing a mapping of mappings which looks
something like this snippet (but with a lot more output):

.. code-block:: js

    {
      "0": { "flight_id": 0, "passengers": 53, "from": "BHX" },
      "1": { "flight_id": 1, "passengers": 157, "from": "AMS" },
      "2": { "flight_id": 2, "passengers": 118, "from": "DAL" },
      "3": { "flight_id": 3, "passengers": 111, "from": "MAN" },
      "4": { "flight_id": 4, "passengers": 192, "from": "BRU" },
      "5": { "flight_id": 5, "passengers": 69, "from": "DAL" },
      "6": { "flight_id": 6, "passengers": 147, "from": "LON" },
      "7": { "flight_id": 7, "passengers": 187, "from": "LON" },
      "8": { "flight_id": 8, "passengers": 171, "from": "AMS" },
      "9": { "flight_id": 9, "passengers": 89, "from": "DAL" },
      "10": { "flight_id": 10, "passengers": 169, "from": "LHR" },
      // lots more output...
    }

The outer mapping is what structa would consider a "table" since it maps keys
(in this case a string representation of an integer) to records. The inner
mappings are what structa would consider "records" since they map a relatively
small number of field names to values.

.. note::

    Record fields don't have to be simple scalar values (although they are
    here); they can be complex structures including lists or indeed further
    embedded records.

If structa finds mappings with more keys than the threshold, those mappings
will be treated as tables. However, if mappings are found with fewer (or equal)
keys to the threshold, they will be analyzed as records. It's a rather
arbitrary value that (unfortunately) usually requires some fore-knowledge of
the data being analyzed. However, it's usually quite easy to spot when the
threshold is wrong, as we'll see.

First, let's take a look at what happens when the threshold is set correctly.
When passed to structa, with the default field threshold of 20, we see the
following output:

.. code-block:: console

    $ python3 simple-fields.py | structa
    {
        str of int range=0..199 pattern="d": {
            'flight_id': int range=0..199,
            'from': str range="ABZ".."ORK" pattern="Iii",
            'passengers': int range=50..200
        }
    }

This indicates that structa has recognized the data as consisting of a mapping
(indicated by the surrounding braces), which is keyed by a decimal string
representation of an integer (in the range 0 to 199), and the values of which
are another mapping with the keys "flight_id", "from", and "passengers".

The reason the inner mappings were treated as a set of records was because all
those mappings had less than 20 entries. The outer mapping had more than 20
entries (200 in this case) and thus was treated as a table.

What happens if we force the field threshold down so low that the inner
mappings are also treated as a table?

.. code-block:: console

    $ python3 simple-fields.py | structa --field-threshold 2
    {
        str of int range=0..199 pattern="d": { str range="flight_id".."passengers": value }
    }

The inner mappings are now defined simply as mappings of strings (in the range
"bar" to "id", sorted alphabetically) which map to "value" (an arbitrary mix of
types). Anytime you see a mapping of ``{ str: value }`` in structa's output,
it's a *fairly* good clue that :option:`structa --field-threshold` might be
too low.


Merging structures (``--merge-threshold``)
==========================================


Whitespace
==========
