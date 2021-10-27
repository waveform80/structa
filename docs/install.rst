.. structa: an application for analyzing repetitive data structures
..
.. Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
..
.. SPDX-License-Identifier: GPL-2.0-or-later

============
Installation
============

structa is distributed in several formats. The following sections detail
installation on a variety of platforms.


Ubuntu Linux
============

For Ubuntu Linux, it is simplest to install from the `author's PPA`_ as follows
(this also ensures you are kept up to date as new releases are made):

.. code-block:: console

    $ sudo add-apt-repository ppa://waveform/structa
    $ sudo apt update
    $ sudo apt install structa

If you wish to remove structa:

.. code-block:: console

    $ sudo apt remove structa


Microsoft Windows
=================

Firstly, install a version of `Python 3`_ (this must be Python 3.5 or later),
or ensure you have an existing installation of Python 3.

Ideally, for the purposes of following the :doc:`tutorial_basic` you should add
your Python 3 install to the system PATH variable so that python can be easily
run from any command line.

You can install structa with the "pip" tool like so:

.. code-block:: doscon

    C:\Users\me> pip install structa

Upgrading structa can be done via pip too:

.. code-block:: doscon

    C:\Users\me> pip install --upgrade structa

And removal can be performed via pip:

.. code-block:: doscon

    C:\Users\me> pip uninstall structa


.. _Python 3: https://www.python.org/downloads/windows/


Other Platforms
===============

If your platform is *not* covered by one of the sections above, structa is
available from PyPI and can therefore be installed with the Python setuptools
"pip" tool:

.. code-block:: console

    $ pip install structa

On some platforms you may need to use a Python 3 specific alias of pip:

.. code-block:: console

    $ pip3 install structa

If you do not have either of these tools available, please install the Python
`setuptools`_ package first.

You can upgrade structa via pip:

.. code-block:: console

    $ pip install --upgrade structa

And removal can be performed as follows:

.. code-block:: console

    $ pip uninstall structa


.. _author's PPA: https://launchpad.net/~waveform/+archive/ppa
.. _setuptools: https://pypi.python.org/pypi/setuptools/
