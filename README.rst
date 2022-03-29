=======
structa
=======

structa is a small, semi-magical utility for discerning the "overall structure"
of large data files. Typically this is something like a document oriented
database in JSON format, or a CSV file of a database dump, or a YAML document.


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


The `Python Package Index`_ (PyPI) provides a JSON API for packages. You can
feed the JSON of several packages to ``structa`` to get an idea of the overall
structure of these records (when structa is given multiple inputs on the same
invocation, it assumes all have a common source)::

    for pkg in numpy scipy pandas matplotlib structa; do
        curl -s https://pypi.org/pypi/$pkg/json > $pkg.json
    done
    structa numpy.json scipy.json pandas.json matplotlib.json structa.json

Output::

    {
        'info': { str: value },
        'last_serial': int range=11.9M..13.1M,
        'releases': {
            str range="0.1".."3.5.1": [
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
                    'python_version': str range="2.4".."source",
                    'requires_python': value,
                    'size': int range=39.3K..118.4M,
                    'upload_time': str of timestamp range=2006-01-09 14:02:01..2022-03-10 16:45:20 pattern="%Y-%m-%dT%H:%M:%S",
                    'upload_time_iso_8601': str of timestamp range=2009-04-06 06:19:25..2022-03-10 16:45:20 pattern="%Y-%m-%dT%H:%M:%S.%f%z",
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
                'packagetype': str range="bdist_wheel".."sdist",
                'python_version': str range="cp310".."source",
                'requires_python': value,
                'size': int range=47.2K..55.6M,
                'upload_time': str of timestamp range=2021-10-27 23:57:01..2022-03-10 16:45:20 pattern="%Y-%m-%dT%H:%M:%S",
                'upload_time_iso_8601': str of timestamp range=2021-10-27 23:57:01..2022-03-10 16:45:20 pattern="%Y-%m-%dT%H:%M:%S.%f%z",
                'url': URL,
                'yanked': bool,
                'yanked_reason': value
            }
        ],
        'vulnerabilities': [ empty ]
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
