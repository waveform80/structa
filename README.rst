=======
structa
=======

structa is a small utility for analyzing repeating structures in large data
sources. Typically this is something like a document oriented database in JSON
format, or a CSV file of a database dump, or a YAML document.


Usage
-----

Use from the command line::

    structa <filename>

The usual ``--help`` and ``--version`` switches are available for more
information. The full `documentation`_ may also help understanding the myriad
switches!


Examples
--------

The `People in Space API`_ shows the number of people currently in space, and
their names and craft name::

    wget http://api.open-notify.org/astros.json
    structa astros.json

Output::

    {
        'message': str pattern=success,
        'number': int range=7..7,
        'people': [{'craft': str pattern=ISS, 'name': str}]
    }

The `Python Package Index`_ (PyPI) provides a JSON API for packages::

    wget https://pypi.org/pypi/numpy/json -O numpy.json
    structa numpy.json

Output::

    {
        'info': {str: value},
        'last_serial': int range=8.6M..8.6M,
        'releases': {
            str: [
                {
                    'comment_text': str,
                    'digests': {
                        'md5': str pattern=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX,
                        'sha256': str pattern=...
                    },
                    'downloads': int range=-1..-1,
                    'filename': str,
                    'has_sig': bool,
                    'md5_digest': str pattern=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX,
                    'packagetype': str,
                    'python_version': str,
                    'requires_python': value,
                    'size': int range=1.9M..24.5M,
                    'upload_time': str of datetime range=2006-12-02 02:07:43..2020-11-02 16:18:20 format=%Y-%m-%dT%H:%M:%S,
                    'upload_time_iso_8601': str of datetime range=2009-04-06 06:19:25+00:00..2020-11-02 16:18:20+00:00 format=%Y-%m-%dT%H:%M:%S.%f%z,
                    'url': URL,
                    'yanked': bool,
                    'yanked_reason': value
                }
            ]
        },
        'urls': [
            {
                'comment_text': str,
                'digests': {
                    'md5': str pattern=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX,
                    'sha256': str pattern=...
                },
                'downloads': int range=-1..-1,
                'filename': str,
                'has_sig': bool,
                'md5_digest': str pattern=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX,
                'packagetype': str pattern=bdist_wheel,
                'python_version': str pattern=.p3D,
                'requires_python': str pattern=>=3.6,
                'size': int range=7.3M..15.4M,
                'upload_time': str of datetime range=2020-11-02 15:46:22..2020-11-02 16:18:20 format=%Y-%m-%dT%H:%M:%S,
                'upload_time_iso_8601': str of datetime range=2020-11-02 15:46:22+00:00..2020-11-02 16:18:20+00:00 format=%Y-%m-%dT%H:%M:%S.%f%z,
                'url': URL,
                'yanked': bool,
                'yanked_reason': value
            }
        ]
    }

The `Ubuntu Security Notices`_ database contains the list of all security
issues in releases of Ubuntu (warning, this one takes some time to analyze and
eats about a gigabyte of RAM while doing so)::

    wget https://usn.ubuntu.com/usn-db/database.json
    structa database.json

Output::

    {
        str pattern=DDDD-D: {
            'action'*: str,
            'cves': [str],
            'description': str,
            'id': str pattern=DDDD-D,
            'isummary'*: str,
            'releases': {
                str: {
                    'allbinaries'*: {str: {'version': str}},
                    'archs'*: {
                        str: {
                            'urls': {
                                URL: {
                                    'md5': str pattern=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX,
                                    'size': int range=808..577.2M
                                }
                            }
                        }
                    },
                    'binaries': {str: {'version': str}},
                    'sources': {str: {'description': str, 'version': str}}
                }
            },
            'summary': str,
            'timestamp': float of datetime range=2012-04-27 12:57:41..2020-11-11 18:01:48,
            'title': str
        }
    }

.. _documentation: https://structa.readthedocs.io/
.. _People in Space API: http://open-notify.org/Open-Notify-API/People-In-Space/
.. _Python Package Index: https://pypi.org/
.. _Ubuntu Security Notices: https://usn.ubuntu.com/usn-db/database.json
