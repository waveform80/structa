.. structa: an application for analyzing repetitive data structures
..
.. Copyright (c) 2021 Dave Jones <dave@waveform.org.uk>
..
.. SPDX-License-Identifier: GPL-2.0-or-later

===============
Real World Data
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


Pre-requisites
==============

You'll need the following to start this tutorial:

* A structa installation; see :doc:`install` for more information on this.

* A Python 3 installation; given that structa requires this to run at all, if
  you've got structa installed, you've got this too. However, it'll help
  enormously if Python is in your system's "PATH" so that you can run python
  scripts at the command line.

* The `scipy`_ library must be installed for the scripts we're going to be
  using to generate data. On Debian/Ubuntu systems you can run the following:

  .. code-block:: console

      $ sudo apt install python3-scipy

  On Windows, or if you're running in a virtual environment, you should run the
  following:

  .. code-block:: console

      $ pip install scipy

* Some basic command line knowledge. In particular, it'll help if you're
  familiar with `shell redirection and piping`_ (note: while that link is on
  `askubuntu.com`_ the contents are equally applicable to the vast majority of
  UNIX shells, and even to Windows' cmd!)

.. _scipy: https://scipy.org/
.. _shell redirection and piping: https://askubuntu.com/a/172989
.. _askubuntu.com: https://askubuntu.com/


"Real World" Data
=================

For this tutorial, we'll use a custom made data-set which will allow us to
tweak things and see what's going on under structa's hood a bit more easily.

The following script generates a fairly sizeable JSON file (~11MB) apparently
recording various air quality readings from places which bear absolutely no
resemblance whatsoever to my adoptive city (ahem):

.. literalinclude:: examples/air-quality.py
   :caption: air-quality.py

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

.. note::

    It should be notable that the output of structa looks rather similar to the
    end of the :file:`air-quality.py` script, where the "data" variable that is
    ultimately dumped is constructed. This neatly illustrates the purpose of
    structa: to summarize repeating structures in a mass of hierarchical data.

Looking at this output we can see that the data consists of a mapping (or
Javascript "object") at the top level, keyed by strings in the range
"Blackshire" to "St. Wigpools" (when sorted).

Under these keys are more mappings which have six keys (which structa has
displayed in alphabetical order for ease of reading):

* **alt** which maps to an integer in some range (in the example above 31 to
  85, but this will likely be different for you)

* **euid** which maps to a string which always started with "GB" and is
  followed by several numerals

* **lat** which maps to a floating point value around 53

* **long** which maps to another floating point roughly around -2

* **ukid** which maps to a string always starting with UKA00 followed by
  several numerals

* And finally, **readings** which maps to another dictionary of strings …

* Which maps to *another* dictionary which is keyed by timestamps in string
  format, which map to floating point values

If you have a terminal capable of ANSI codes, you may note that types are
displayed in a different color (to distinguish them from literals like the
"ukid" and "euid" keys), as are patterns within fixed length strings, and
various keywords like "range=".

.. note::

    You may also notice that several of the types (definitely the outer "str",
    but possibly other types within the top-level dictionary, like lat/long)
    are underlined. This indicates that these values are *unique* throughout
    the entire dataset, and thus potentially suitable as top-level keys if
    entered into a database.

    Just because you *can* use something as a unique key, however, doesn't mean
    you *should* (floating point values being a classic example).


Optional Keys
=============

Let's explore how structa handles various "problems" in the data. Firstly,
we'll make a copy of our script and add a chunk of code to remove approximately
half of the altitude readings:

.. code-block:: console

    $ cp air-quality.py air-quality-opt.py
    $ editor air-quality-opt.py

.. literalinclude:: examples/air-quality-opt.py
   :caption: air-quality-opt.py
   :start-at: data =
   :emphasize-lines: 19-21

What does structa make of this?

.. code-block:: console

    $ python3 air-quality-opt.py > air-quality-opt.json
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

Next, we'll make another script (a copy of :file:`air-quality-opt.py`), which
adds some more code to "corrupt" some of the timestamps:

.. code-block:: console

    $ cp air-quality-opt.py air-quality-bad.py
    $ editor air-quality-bad.py

.. literalinclude:: examples/air-quality-bad.py
   :caption: air-quality-bad.py
   :start-at: for location in data:
   :emphasize-lines: 3-7

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


Multiple Inputs
===============

Time for another script (based on a copy of the prior
:file:`air-quality-bad.py` script), which produces each location as its own
separate JSON file:

.. code-block:: console

    $ cp air-quality-bad.py air-quality-multi.py
    $ editor air-quality-multi.py

.. literalinclude:: examples/air-quality-multi.py
   :caption: air-quality-multi.py
   :start-at: for location in data:
   :emphasize-lines: 2-5

We can pass all the files as inputs to structa simultaneously, which will cause
it to assume that they should all be processed as if they have comparable
structures:

.. code-block:: console

    $ python3 air-quality-multi.py
    $ ls *.json
    air-quality-blackshire.json           air-quality-prestchester.json
    air-quality-mancford-peccadillo.json  air-quality-salport.json
    air-quality-mancford-shartson.json    air-quality-st-wigpools.json
    $ structa air-quality-*.json
    {
        str range="Blackshire".."St. Wigpools": {
            'alt': int range=15..92,
            'euid': str range="GB0213A".."GB1029A" pattern="GB[01][028-9][1-26-7][2-379]A",
            'lat': float range=53.49709..53.98315,
            'long': float range=-2.924566..-2.021445,
            'readings': {
                str range="NO".."PM2.5": { str of timestamp range=2020-01-01 00:00:00..2021-02-20 15:00:00 pattern="%Y-%m-%dT%H:%M:%S": float range=-2.982586..327.4161 }
            },
            'ukid': str range="UKA00148".."UKA00786" pattern="UKA00[135-7][13-47-8][06-9]"
        }
    }

In this case, structa has merged the top-level mapping in each file into one
large top-level mapping. It would do the same if a top-level list were found in
each file too.


Conclusion
==========

This concludes the structa tutorial series. You should now have some experience
of using structa with more complex datasets, how to tune its various settings
for different scenarios, and what to look out for in the results to get the
most out of its analysis.

In other words, if you wish to use structa from the command line, you should be
all set. If you want help dealing with some specific scenarios, the sections in
:doc:`recipes` may be of interest. Alternatively, if you wish to use structa in
your own Python scripts, the :doc:`api` may prove useful.

Finally, if you wish to hack on structa yourself, please see the
:doc:`development` chapter for more information.
