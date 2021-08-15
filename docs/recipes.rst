=======
Recipes
=======

The following sections cover analyzing various common data scenarios with
structa, and how structa's various options should be set to handle them.


Analyzing from a URL
====================

While structa itself can't read URLs directly, the fact you can pipe data to
it makes it ideal for use with something like `curl`_:

.. code-block:: console

    $ curl -s https://piwheels.org/packages.json | structa
    [
        (
            str,
            int range=0..32.8K,
            int range=0..1.7M
        )
    ]

.. _curl: https://curl.se/


Dealing with large records
==========================

In the :doc:`tutorial_basic` we saw the following script, which generates a
mapping of mappings, for the purposes of learning about :option:`structa
--field-threshold`:

.. literalinclude:: examples/simple-fields.py
   :caption: simple-fields.py

We saw what happens when the threshold is too low:

.. code-block:: console

    $ python3 simple-fields.py | structa --field-threshold 2
    {
        str of int range=0..199 pattern="d": { str range="flight_id".."passengers": value }
    }

What happens if the threshold is set too high, resulting in the outer mapping
being treated as a (very large!) record?

.. code-block:: console

    $ python3 simple-fields.py | structa --field-threshold 300
    {
        str of int range=0..199 pattern="d": {
            'flight_id': int range=0..199,
            'from': str range="ABZ".."ORK" pattern="[A-EL-MO][A-EHMORU][IK-LNR-SUXZ]",
            'passengers': int range=50..199
        }
    }

Curiously it seems to have worked happily anyway, although the pattern of the
"from" field is now considerably more complex. The reasons for this are
relatively complicated, but has to do with a later pass of structa's algorithm
merging common sub-structures of records. The merging process unfortunately
handles certain things (like the merging of string field patterns) rather
crudely.

Hence, while it's generally safe to bump :option:`structa --field-threshold` up
quite high whenever you need to, be aware that it will:

* significantly slow down analysis of large files (because the merging process
  is quite slow)

* complicate the pattern analysis of repeated string fields and a few other
  things (e.g. string representations of date-times)

In other words, whenever you find yourself in a situation where you need to
bump up the field threshold, a reasonable procedure to follow is:

1. Bump the threshold very high (e.g. 1000) and run the analysis with
   :option:`structa --show-count` enabled.

2. Run the analysis again with the field threshold set below the count of the
   outer container(s), but above the count of the inner record mappings

The first run will probably be quite slow, but the second run will be much
faster and will produce better output.
