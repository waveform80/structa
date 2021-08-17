#!/usr/bin/env python3
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2018-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
import os
import configparser
from datetime import datetime
from pathlib import Path

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
config = configparser.ConfigParser()
config.read([Path(__file__).parent / '..' / 'setup.cfg'])
metadata = config['metadata']

# -- Project information -----------------------------------------------------

project = metadata['name'].title()
author = metadata['author']
copyright = '{year} {author}'.format(year=datetime.now().year, author=author)
release = metadata['version']
version = release

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

if on_rtd:
    needs_sphinx = '1.4.0'
    extensions.append('sphinx.ext.imgmath')
    imgmath_image_format = 'svg'
    tags.add('rtd')
else:
    # FIXME limit to the debian package build only
    extensions.append('sphinx.ext.mathjax')
    mathjax_path = '/usr/share/javascript/mathjax/MathJax.js?config=TeX-AMS_HTML'

templates_path = ['_templates']
master_doc = 'index'

exclude_patterns = ['_build']
pygments_style = 'sphinx'

# -- Autodoc options ---------------------------------------------------------

autodoc_member_order = 'groupwise'
autodoc_default_options = {
    'members': True,
}
autodoc_mock_imports = [
    'lxml',
    'chardet',
    'blessings',
    'tqdm',
    'dateutil',
]

# -- Intersphinx options -----------------------------------------------------

intersphinx_mapping = {
    'python': ('http://docs.python.org/3.8', None),
}

# -- Options for HTML output ----------------------------------------------

html_theme = 'sphinx_rtd_theme'
pygments_style = 'default'
html_title = '{project} {version} Documentation'.format(
    project=project, version=version)
html_static_path = ['_static']
manpages_url = 'https://manpages.ubuntu.com/manpages/focal/en/man{section}/{page}.{section}.html'

# Hack to make wide tables work properly in RTD
# See https://github.com/snide/sphinx_rtd_theme/issues/117 for details
def setup(app):
    app.add_css_file('style_override.css')

# -- Options for LaTeX output ------------------------------------------------

latex_engine = 'xelatex'

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    'preamble': r'\def\thempfootnote{\arabic{mpfootnote}}', # workaround sphinx issue #2530
}

latex_documents = [
    (
        'index',            # source start file
        '{metadata[name]}.tex'.format(metadata=metadata), # filename
        '{project} {version} Documentation'.format(project=project, version=version), # title
        author,             # author
        'manual',           # documentclass
        True,               # documents ref'd from toctree only
    ),
]

latex_show_pagerefs = True
latex_show_urls = 'footnote'

# -- Options for epub output -------------------------------------------------

epub_basename = metadata['name']
epub_author = author
epub_identifier = 'https://structa.readthedocs.io/'
epub_show_urls = 'no'

# -- Options for manual page output ------------------------------------------

man_pages = [
    (
        'manual',
        metadata['name'],
        '{project} Utility'.format(project=project),
        [metadata['author']],
        1
    ),
]

man_show_urls = True

# -- Options for linkcheck builder -------------------------------------------

linkcheck_retries = 3
linkcheck_workers = 20
linkcheck_anchors = True
