=======
structa
=======

structa is a small utility for analyzing repeating structures in large data
sources. Typically this is something like a document oriented database in JSON
format, or a CSV file of a database dump, or a YAML document.


Usage
=====

Use from the command line::

    structa <filename>

The usual ``--help`` and ``--version`` switches are available for more
information. The full `documentation`_ may also help understanding the myriad
switches!


Examples
========

The `People in Space API`_ shows the number of people currently in space, and
their names and craft name::

    curl -s http://api.open-notify.org/astros.json | structa

Output::

    {
        'message': str range="success" pattern="success",
        'number': int range=10,
        'people': [
            {
                'craft': str range="ISS".."Tiangong",
                'name': str range="Akihiko Hoshide".."Thomas Pesquet"
            }
        ]
    }


The `Python Package Index`_ (PyPI) provides a JSON API for packages::

    curl -s https://pypi.org/pypi/numpy/json | structa

Output::

    {
        'info': { str: value },
        'last_serial': int range=9.0M,
        'releases': {
            str range="0.9.6".."1.9.3": [
                {
                    'comment_text': str,
                    'digests': {
                        'md5': str pattern="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                        'sha256': str pattern="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    },
                    'downloads': int range=-1,
                    'filename': str,
                    'has_sig': bool,
                    'md5_digest': str pattern="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    'packagetype': str range="bdist_wheel".."sdist",
                    'python_version': str range="2.5".."source",
                    'requires_python': value,
                    'size': int range=1.9M..24.5M,
                    'upload_time': str of timestamp range=2006-12-02 02:07:43..2020-12-25 03:30:00 pattern=%Y-%m-%dT%H:%M:%S,
                    'upload_time_iso_8601': str of timestamp range=2009-04-06 06:19:25..2020-12-25 03:30:00 pattern=%Y-%m-%dT%H:%M:%S.%f%z,
                    'url': URL,
                    'yanked': bool,
                    'yanked_reason': value
                }
            ]
        },
        'urls': [
            {
                'comment_text': str range="",
                'digests': {
                    'md5': str pattern="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    'sha256': str pattern="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                },
                'downloads': int range=-1,
                'filename': str,
                'has_sig': bool,
                'md5_digest': str pattern="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                'packagetype': str range="bdist_wheel" pattern="bdist_wheel",
                'python_version': str range="cp36".."pp36" pattern="Ip3d",
                'requires_python': str range="&gt;=3.6" pattern="&gt;=3.6",
                'size': int range=7.3M..15.4M,
                'upload_time': str of timestamp range=2020-11-02 15:46:22..2020-11-02 16:18:20 pattern=%Y-%m-%dT%H:%M:%S,
                'upload_time_iso_8601': str of timestamp range=2020-11-02 15:46:22..2020-11-02 16:18:20 pattern=%Y-%m-%dT%H:%M:%S.%f%z,
                'url': URL,
                'yanked': bool,
                'yanked_reason': value
            }
        ]
    }

The `Ubuntu Security Notices`_ database contains the list of all security
issues in releases of Ubuntu (warning, this one takes some time to analyze and
eats about a gigabyte of RAM while doing so)::

    curl -s https://usn.ubuntu.com/usn-db/database.json | structa

Output::

    {
        str range="1430-1".."4630-1" pattern="dddd-d": {
            'action'?: str,
            'cves': [ str ],
            'description': str,
            'id': str range="1430-1".."4630-1" pattern="dddd-d",
            'isummary'?: str,
            'releases': {
                str range="artful".."zesty": {
                    'allbinaries'?: {
                        str: { 'version': str }
                    },
                    'archs'?: {
                        str range="all".."source": {
                            'urls': {
                                URL: {
                                    'md5': str pattern="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                                    'size': int range=20..1.2G
                                }
                            }
                        }
                    },
                    'binaries': {
                        str: { 'version': str }
                    },
                    'sources': {
                        str: {
                            'description': str,
                            'version': str
                        }
                    }
                }
            },
            'summary': str,
            'timestamp': float of timestamp range=2012-04-27 12:57:41..2020-11-11 18:01:48,
            'title': str
        }
    }

.. _documentation: https://structa.readthedocs.io/
.. _People in Space API: http://open-notify.org/Open-Notify-API/People-In-Space/
.. _Python Package Index: https://pypi.org/
.. _Ubuntu Security Notices: https://usn.ubuntu.com/usn-db/database.json
