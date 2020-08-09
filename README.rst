=======
structa
=======

structa is a small utility for analyzing repeating structures of a chunk of
data. Typically this is something like a document oriented database in JSON
format.

Usage
-----

Use from the command line::

    structa <filename>

The usual ``-help`` and ``--version`` switches are available for more
information.

Examples
--------

The `People in Space API`_ shows the number of people currently in space, and
their names and craft name::

    wget http://api.open-notify.org/astros.json
    structa astros.json

.. _People in Space API: http://open-notify.org/Open-Notify-API/People-In-Space/

Output::

    ├─ 'number': 5
    ├─ 'message': success
    └─ 'people': [
       ├─ 'craft': ISS
       └─ 'name': {Doug Hurley|Bob Behnken|Chris Cassidy|Anatoly...}
    ]

The `Python Package Index`_ (PyPI) provides a JSON API for packages::

    wget https://pypi.org/pypi/numpy/json -O numpy.json
    structa numpy.json

.. _Python Package Index: https://pypi.org/

Output::

    ├─ 'last_serial': 7391399
    ├─ 'urls': [
       ├─ 'requires_python': >=3.5
       ├─ 'filename': <str>
       ├─ 'yanked_reason': None
       ├─ 'comment_text':
       ├─ 'python_version': {cp36|source|cp35|cp38|cp37}
       ├─ 'md5_digest': <str 'hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'>
       ├─ 'size': <int 5.2M..19.6M>
       ├─ 'downloads': -1
       ├─ 'url': <URL>
       ├─ 'has_sig': False
       ├─ 'upload_time': <datetime '%Y-%m-%dT%H:%M:%S' 2020-06-04 00:10:51..2020-06-04 00:27:58>
       ├─ 'upload_time_iso_8601': <str '2020-06-04T00:dd:dd.ddddddZ'>
       ├─ 'digests':
       │  ├─ 'md5': <str 'hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'>
       │  └─ 'sha256': <str ...>
       ├─ 'packagetype': {sdist|bdist_wheel}
       └─ 'yanked': False
    ]
    ├─ 'info':
    │  └─ <str>: <value>
    └─ 'releases':
       └─ <str>: [
          ├─ 'requires_python': {>=3.5|>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*|>=3.6|None}
          ├─ 'filename': <str>
          ├─ 'yanked_reason': None
          ├─ 'comment_text': {|Simple installer, no SSE instructions. |Simple windows...}
          ├─ 'python_version': <str>
          ├─ 'md5_digest': <str 'hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'>
          ├─ 'size': <int 1.8M..23.4M>
          ├─ 'downloads': -1
          ├─ 'url': <URL>
          ├─ 'has_sig': {False|True}
          ├─ 'upload_time': <datetime '%Y-%m-%dT%H:%M:%S' 2006-12-02 02:07:43..2020-06-04 00:35:35>
          ├─ 'upload_time_iso_8601': <str>
          ├─ 'digests':
          │  ├─ 'md5': <str 'hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'>
          │  └─ 'sha256': <str ...>
          ├─ 'packagetype': {bdist_wheel|bdist_wininst|sdist}
          └─ 'yanked': False
       ]
