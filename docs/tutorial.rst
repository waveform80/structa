========
Tutorial
========

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
is figuring out what to twiddle them to.


Basic Usage
===========

We'll start with some basic data structures and see how structa handles them.
The following code dumps a list of strings representing integers to stdout in
JSON format:

.. literalinclude:: examples/str-nums.py
   :caption:

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
------------------------------

Let's see how structa handles bad data. We'll add a non-numeric string into our
list of numbers:

.. literalinclude:: examples/bad-nums.py
   :caption:

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
   :caption:

.. code-block:: console

    $ python3 bad-types.py | structa
    [ value ]

In this case, even with the default 1% bad threshold, structa doesn't exclude
the bad data; the analysis simply returns it as a list of mixed "values".

This is because structa assumes that the *types* of data are at least correct,
under the assumption that if whatever is generating your data hasn't even got
the data types right, you've got bigger problems! The bad threshold mechanism
only applies to bad data *within* a homogenous type (typically bad string
representations of numeric or boolean types).


Missing Data (``--empty-threshold``)
------------------------------------

Another type of "bad" data commonly encountered is empty strings which are
typically used to represent *missing* data, and (predictably) structa has
another knob that can be twiddled for this: :option:`structa
--empty-threshold`. The following script generates a list of strings of
integers in which most of the strings (~70%) are blank:

.. literalinclude:: examples/mostly-blank.py
   :caption:

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


Fields (``--field-threshold``)
------------------------------

The final major knob that can be twiddled in structa is the :option:`structa
--field-threshold`. This is used to distinguish between mappings that act as a
"table" (mapping keys to records) and mappings that act as a record (mapping
field-names, typically strings, to their values).

Specifically, if mappings are found with more keys than the threshold, those
mappings will be treated as tables. However, if mappings are found with fewer
(or equal) keys to the threshold, they will be analyzed as records. It's a
rather arbitrary value that (unfortunately) usually requires some
fore-knowledge of the data being analyzed. However, it's usually quite easy to
spot when the threshold is wrong, as we'll see.

First, let's take a look at what happens when the threshold is set correctly.
The following script generates a mapping of mappings. The outer mapping
contains 200 items, while the inner mappings each contain 3 items labelled
"id", "foo", and "bar":

.. literalinclude:: examples/simple-fields.py
   :caption:

When passed to structa, with the default field threshold of 20, we see the
following output:

.. code-block:: console

    $ python3 simple-fields.py | structa
    {
        str of int range=0..199 pattern="d": {
            'bar': str range="ABZ".."ORK" pattern="Iii",
            'foo': int range=15..50,
            'id': int range=0..199
        }
    }

This indicates that structa has recognized the data as consisting of a mapping
(indicated by the surrounding braces), which is keyed by a decimal string
representation of an integer (in the range 0 to 199), and the values of which
are another mapping with the keys "id", "foo", and "bar".

The reason the inner mappings were treated as a set of records was because all
those mappings had less than 20 entries. The outer mapping had more than 20
entries (200 in this case) and thus was treated as a table.

What happens if we force the field threshold down so low that the inner
mappings are also treated as a table?

.. code-block:: console

    $ python3 simple-fields.py | structa --field-threshold 2
    {
        str of int range=0..199 pattern="d": { str range="bar".."id": value }
    }

The inner mappings are now defined simply as mappings of strings (in the range
"bar" to "id", sorted alphabetically) which map to "value" (an arbitrary mix of
types). Anytime you see a mapping of ``{ str: value }`` in structa's output,
it's a *fairly* good clue that :option:`structa --field-threshold` might be
too low.


"Real World" Data
=================

Next, we'll move onto using a slight more complex, custom made data-set which
will allow us to tweak things and see what's going on under structa's hood a
bit more easily.

The following script generates a fairly sizeable JSON file (~11MB) apparently
recording various air quality readings from places which bear absolutely no
resemblance whatsoever to my adoptive home city (ahem):

.. literalinclude:: examples/air-quality.py
   :caption:

.. note::

    The script requires `scipy`_ installed for the purposes of generating some
    nicely skewed (but otherwise relatively "normal") datasets. If you're
    using Debian or Ubuntu, simply do the following prior to running the
    script::

        $ sudo apt install python3-scipy

.. _scipy: https://www.scipy.org/

If you run the script it will output JSON on stdout, which you can redirect to
a file (or straight to structa, but given the script takes a while to run you
may wish to capture the output to a file for experimentation purposes). Passing
the output to structa should produce output something like this:

.. code-block:: console

    $ python3 air-quality.py > air-quality.json
    $ structa air-quality.json
    {
        str range="Blackshire".."St. Wigpools": {
            'alt': int range=31..85,
            'euid': str range="GB1012A".."GB1958A" pattern="GB1[0-139][13-58][2-37-9]A",
            'lat': float range=53.29812..53.6833,
            'long': float range=-2.901626..-2.362118,
            'readings': {
                str range="NO".."PM2.5": { str of timestamp range=2020-01-01 00:00:00..2021-02-20 15:00:00 pattern="%Y-%m-%dT%H:%M:%S": float range=-5.634479..335.6384 }
            },
            'ukid': str range="UKA00129".."UKA00713" pattern="UKA00[1-24-57][1-38][0-13579]"
        }
    }

It should be notable that the output of structa looks awfully similar to the
end of the :file:`air-quality.py` script, where the "data" variable that is
ultimately dumped is put together. This is the purpose of structa: to summarize
repeating structures in a mass of hierarchical data (e.g. from a big JSON
file).

Looking at this output we can see that the
data consists of a dictionary (or Javascript "object") at the top level, keyed
by strings in the range "Blackshire" to "St. Wigpools" (when sorted).

Under these keys are more dictionaries which have six keys (which structa has
displayed in alphabetical order for ease of use):

* "alt" which maps to an integer in some range (in the example above 31 to 85,
  but this will likely be different for you)

* "euid" which maps to a string which always started with "GB" and is followed
  by several numerals

* "lat" which maps to a floating point value around 53

* "long" which maps to another floating point roughly around -2

* "ukid" which maps to a string always starting with UKA00 followed by several
  numerals

* And finally, "readings" which maps to another dictionary of strings ...

* Which maps to *another* dictionary which is keyed by timestamps in string
  format, which map to floating point values

If you have a terminal capable of ANSI codes, you may note that types are
displayed in a different color (to distinguish them from literals like the
"ukid" and "euid" keys), as are patterns within fixed length strings, and
various keywords like "range=".

You may also notice that several of the types (definitely the outer "str", but
possibly other types within the top-level dictionary) are underlined. This
indicates that these values are *unique* throughout the entire dataset
(suitable as top-level keys if entered into a database).


Optional Keys
=============

Let's explore how structa handles various "problems" in the data. Firstly,
we'll remove approximately half of the altitude readings by adding the
highlighted chunk of code to the end of our script:

.. literalinclude:: examples/air-quality-opt.py
   :start-at: data =
   :emphasize-lines: 19-21

What does structa make of this?

.. code-block:: console

    $ python3 air-quality.py > air-quality-opt.json
    $ structa air-quality-opt.json
    {
        str range="Blackshire".."St. Wigpools": {
            'alt'?: int range=31..85,
            'euid': str range="GB1012A".."GB1958A" pattern="GB1[0-139][13-58][2-37-9]A",
            'lat': float range=53.29812..53.6833,
            'long': float range=-2.901626..-2.362118,
            'readings': {
                str range="NO".."PM2.5": { str of timestamp range=2020-01-01 00:00:00..2021-02-20 15:00:00 pattern="%Y-%m-%dT%H:%M:%S": float range=-5.634479..335.6384 }
            },
            'ukid': str range="UKA00129".."UKA00713" pattern="UKA00[1-24-57][1-38][0-13579]"
        }
    }

Note that a question-mark has now been appended to the "alt" key in the
second-level dictionary (if your terminal supports color codes, this should
appear in red). This indicates that the "alt" key is optional and not present
in every single dictionary at that level.


"Bad" Data
==========

Next, we'll add some more code which "corrupts" some of the timestamps:

.. literalinclude:: examples/air-quality-bad.py
   :start-at: for location in data:
   :emphasize-lines: 4-7

What does structa make of this?

.. code-block:: console

    $ python3 air-quality.py > air-quality-bad.json
    $ structa air-quality-bad.json
    {
        str range="Blackshire".."St. Wigpools": {
            'alt'?: int range=31..85,
            'euid': str range="GB1012A".."GB1958A" pattern="GB1[0-139][13-58][2-37-9]A",
            'lat': float range=53.29812..53.6833,
            'long': float range=-2.901626..-2.362118,
            'readings': {
                str range="NO".."PM2.5": { str of timestamp range=2020-01-01 00:00:00..2021-02-20 15:00:00 pattern="%Y-%m-%dT%H:%M:%S": float range=-5.634479..335.6384 }
            },
            'ukid': str range="UKA00129".."UKA00713" pattern="UKA00[1-24-57][1-38][0-13579]"
        }
    }

Apparently nothing! It may seem odd that structa raised no errors, or even
warnings when encountering subtly incorrect data. One might (incorrectly)
assume that structa just thinks anything that vaguely looks like a timestamp in
a string is such.

For the avoidance of doubt, this is not the case: structa *does* attempt to
convert timestamps correctly and does *not* think February 31st is a valid date
(unlike certain databases!). However, structa does have a "bad threshold"
setting (:option:`structa --bad-threshold`) which means not all data in a given
sequence has to match the pattern under test.


Whitespace
==========

By default, structa strips whitespace from strings prior to analysis. This is
probably not necessary for the vast majority of modern datasets, but it's a
reasonably safe default, and can be controlled with the :option:`structa
--strip-whitespace` and :option:`structa --no-strip-whitespace` options in any
case.

One other option that is affected by whitespace stripping is the "empty"
threshold. This is the proportion of string values that are permitted to be
empty (and thus ignored) when analysing a field of data. By default, this is
99% meaning the vast majority of a given field can be blank, and structa will
still analyze the remaining strings to determine whether they represent
integers, datetimes, etc.

If the proportion of blank strings in a field exceeds the empty threshold, the
field will simply be marked as a string without any further processing.

For example:

.. literalinclude:: examples/mostly-blank.py
   :caption:

This script outputs (as JSON) a list of strings of integers, roughly 70% of
which will be blank. By default, structa is happy with this:

.. code-block:: console

    $ python3 mostly-blank.py | structa
    [ str of int range=0..100 pattern="d" ]

However, if we force the empty threshold down below 70%:
