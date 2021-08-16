===========
Development
===========

.. currentmodule:: structa

The main GitHub repository for the project can be found at:

    https://github.com/waveform80/structa

The project is currently in its early stages, but is quite useable and the
documentation, while incomplete, should be useful to both users and developers
wishing to hack on the project itself. The test suite is also nearing full
coverage.


.. _dev_install:

Development installation
========================

If you wish to develop structa, obtain the source by cloning the GitHub
repository and then use the "develop" target of the Makefile which will install
the package as a link to the cloned repository allowing in-place development.
The following example demonstrates this method within a virtual Python
environment:

.. code-block:: console

    $ sudo apt install build-essential git virtualenvwrapper

After installing ``virtualenvwrapper`` you'll need to restart your shell before
commands like :command:`mkvirtualenv` will operate correctly. Once you've
restarted your shell, continue:

.. code-block:: console

    $ cd
    $ mkvirtualenv -p /usr/bin/python3 structa
    $ workon structa
    (structa) $ git clone https://github.com/waveform80/structa.git
    (structa) $ cd structa
    (structa) $ make develop

To pull the latest changes from git into your clone and update your
installation:

.. code-block:: console

    $ workon structa
    (structa) $ cd ~/structa
    (structa) $ git pull
    (structa) $ make develop

To remove your installation, destroy the sandbox and the clone:

.. code-block:: console

    (structa) $ deactivate
    $ rmvirtualenv structa
    $ rm -rf ~/structa


Building the docs
=================

If you wish to build the docs, you'll need a few more dependencies. Inkscape
is used for conversion of SVGs to other formats, Graphviz is used for rendering
certain charts, and TeX Live is required for building PDF output. The following
command should install all required dependencies:

.. code-block:: console

    $ sudo apt install texlive-latex-recommended texlive-latex-extra \
        texlive-fonts-recommended texlive-xetex graphviz inkscape \
        python3-sphinx python3-sphinx-rtd-theme latexmk xindy

Once these are installed, you can use the "doc" target to build the
documentation in all supported formats (HTML, ePub, and PDF):

.. code-block:: console

    $ workon structa
    (structa) $ cd ~/structa
    (structa) $ make doc

However, the easiest way to develop the documentation is with the "preview"
target which will build the HTML version of the docs, and start a web-server to
preview the output. The web-server will then watch for source changes (in both
the documentation source, and the application's source) and rebuild the HTML
automatically as required:

.. code-block:: console

    $ workon structa
    (structa) $ cd ~/structa
    (structa) $ make preview

The HTML output is written to :file:`build/html` while the PDF output
goes to :file:`build/latex`.


Test suite
==========

If you wish to run the structa test suite, follow the instructions in
:ref:`dev_install` above and then make the "test" target within the sandbox:

.. code-block:: console

    $ workon structa
    (structa) $ cd ~/structa
    (structa) $ make test

The test suite is also setup for usage with the :command:`tox` utility, in
which case it will attempt to execute the test suite with all supported
versions of Python. If you are developing under Ubuntu you may wish to look
into the `Dead Snakes PPA`_ in order to install old/new versions of Python; the
tox setup *should* work with the version of tox shipped with Ubuntu Focal, but
more features (like parallel test execution) are available with later versions.

For example, to execute the test suite under tox, skipping interpreter versions
which are not installed:

.. code-block:: console

    $ tox -s

To execute the test suite under all installed interpreter versions in parallel,
using as many parallel tasks as there are CPUs, then displaying a combined
report of coverage from all environments:

.. code-block:: console

    $ tox -p auto -s
    $ coverage combine --rcfile coverage.cfg
    $ coverage report --rcfile coverage.cfg


.. _Dead Snakes PPA: https://launchpad.net/~deadsnakes/%2Barchive/ubuntu/ppa
