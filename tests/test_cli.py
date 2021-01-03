import os
import json
import random
import datetime as dt
from fractions import Fraction

import pytest
from dateutil.relativedelta import relativedelta

from structa.types import *
from structa.ui import cli


def test_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(['-h'])
    assert exc_info.value.args[0] == 0  # return code 0
    captured = capsys.readouterr()
    assert captured.out.lstrip().startswith('usage: ')


def test_min_timestamp():
    assert cli.min_timestamp('2000-01-01') == dt.datetime(2000, 1, 1)
    assert cli.min_timestamp('10 years') == cli._start - relativedelta(years=10)


def test_max_timestamp():
    assert cli.max_timestamp('2050-01-01') == dt.datetime(2050, 1, 1)
    assert cli.max_timestamp('10 years') == cli._start + relativedelta(years=10)


def test_num():
    assert cli.num('1') == 1
    assert cli.num('1/2') == Fraction(1, 2)
    assert cli.num('1%') == Fraction(1, 100)
    assert cli.num('1.0') == 1.0
    assert cli.num('1e0') == 1.0

    assert isinstance(cli.num('1'), int)
    assert isinstance(cli.num('1/2'), Fraction)
    assert isinstance(cli.num('1%'), Fraction)
    assert isinstance(cli.num('1.0'), float)
    assert isinstance(cli.num('1e0'), float)


def test_size():
    assert cli.size('1') == 1
    assert cli.size(' 100 ') == 100
    assert cli.size('2K') == 2048
    assert cli.size('1M') == 1048576


def test_main(tmpdir, capsys):
    data = list(range(100))
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        json.dump(data, f)
    assert cli.main([filename]) == 0
    assert capsys.readouterr().out.strip() == '[ int range=0..99 ]'


def test_debug(tmpdir, capsys):
    filename = str(tmpdir.join('foo.json'))
    with open(filename, 'w') as f:
        f.write('foo bar baz')
    os.environ['DEBUG'] = '0'
    assert cli.main([filename, '--format', 'json']) == 1
    assert capsys.readouterr().err.splitlines()[-1].strip() == 'Expecting value: line 1 column 1 (char 0)'
    os.environ['DEBUG'] = '1'
    with pytest.raises(Exception):
        cli.main([filename, '--format', 'json'])

# A big load of data drawn from my local apt-cache for the purposes of testing
apt_cache = {
    'acl2': {
        '8.3dfsg-1':
            'ACL2 is both a programming language in which you can model '
            'computer systems and a tool to help you prove properties of '
            'those models.\n\nThis package contains the base ACL2 binary.'
    },
    'augustus-doc': {
        '3.3.3+dfsg-3':
            'This package contains documentation for AUGUSTUS: a '
            'comprehensive manual-style README both for AUGUSTUS in general '
            'as well as for its comparative gene prediction (cgp) mode, as '
            'well as a HTML tutorial.'
    },
    'calcoo': {
        '1.3.18-8':
            'Calcoo is a scientific calculator designed to provide maximum '
            'usability. The features that make Calcoo better than (at least '
            'some) other calculator programs are:\n\n- bitmapped button '
            'labels and display digits to improve readability\n- no '
            'double-function buttons - you need to click only one button\n  '
            'for any operation (except for arc-hyp trigonometric '
            'functions)\n- undo/redo buttons\n- both RPN (reverse Polish '
            'notation) and algebraic modes\n- copy/paste interaction with X '
            'clipboard\n- display tick marks to separate thousands\n- two '
            'memory registers with displays\n- displays for Y, Z, and T '
            'registers\n'
    },
    'console-braille': {
        '1.8':
            'This package includes\n\n- fonts with various sizes to render '
            'braille on the Linux console\n- keymaps to type braille as '
            'unicode characters on the Linux console.\n'
    },
    'dict-freedict-eng-hin': {
        '2018.10.21-3':
            'This is the English-Hindi dictionary from the FreeDict project, '
            'version 1.6. It contains 25642 headwords (FreeDict status: low '
            'quality). It can be either used with the dictd server and a dict '
            'client or with GoldenDict.'
    },
    'elpa-nose': {
        '0.1.1-5':
            "This package provides a bunch of functions that handle running "
            "nosetests on a particular buffer or part of a buffer. Also "
            "`nose.el' adds a minor mode that is used to manage keybindings "
            "and provide a hook for changing the behaviour of the nose output "
            "buffer."
    },
    'firefox-locale-oc': {
        '84.0+build3-0ubuntu0.20.10.1':
            'This package contains Occitan (post 1500) translations and '
            'search plugins for Firefox', '81.0.2+build1-0ubuntu1': 'This '
            'package contains Occitan (post 1500) translations and search '
            'plugins for Firefox'
    },
    'fuseiso': {
        '20070708-3.2build1':
            'This package provides a module to mount ISO filesystem images '
            'using FUSE. With FUSE it is possible to implement a fully '
            'functional filesystem in a userspace program.\n\nIt can also '
            'mount single-tracks .BIN, .MDF, .IMG and .NRG.'
    },
    'gdisk': {
        '1.0.5-1':
            'GPT fdisk (aka gdisk) is a text-mode partitioning tool that '
            'provides utilities for Globally Unique Identifier (GUID) '
            'Partition Table (GPT) disks.\n\nFeatures:\n\n- Edit GUID '
            'partition table definitions\n- In place conversion of BSD '
            'disklabels to GPT\n- In place conversion of MBR to GPT\n- In '
            'place conversion of GPT to MBR\n- Create hybrid MBR/GPT layouts\n'
            '- Repair damaged GPT data structures\n- Repair damaged MBR '
            'structures\n- Back up GPT data to a file (and restore from file)\n'
    },
    'gnat-10-mipsisa64r6-linux-gnuabi64': {
        '10.2.0-8ubuntu1cross1':
            'GNAT is a compiler for the Ada programming language. It produces '
            'optimized code on platforms supported by the GNU Compiler '
            'Collection (GCC).\n\nThis package provides the compiler, tools '
            'and runtime library that handles exceptions using the default '
            'zero-cost mechanism.'
    },
    'golang-github-dnstap-golang-dnstap-cli': {
        '0.2.0-4build1':
            'dnstap implements an encoding format for DNS server events. It '
            'uses a lightweight framing on top of event payloads encoded '
            'using Protocol Buffers and is transport neutral. dnstap can '
            'represent internal state inside a DNS server that is difficult '
            'to obtain using techniques based on traditional packet capture '
            'or unstructured textual format logging.\n\nThis package contains '
            'the "dnstap" command line tool.'
    },
    'golang-golang-x-crypto-dev': {
        '1:0.0~git20200604.70a84ac-2':
            'This package contains cryptographic algorithms and protocols not '
            'packaged in the main Go distribution, such as:\n\n- blowfish\n- '
            'nacl\n- openpgp\n- otr\n- sha3\n- ssh\nand many others.'
    },
    'hol88-contrib-source': {
        '2.02.19940316-35build2':
            'The HOL System is an environment for interactive theorem proving '
            'in a higher-order logic. Its most outstanding feature is its '
            'high degree of programmability through the meta-language ML. The '
            'system has a wide variety of uses from formalizing pure '
            'mathematics to verification of industrial hardware. Academic and '
            'industrial sites world-wide are using HOL.'
    },
    'jing-trang-doc': {
        '20181222+dfsg2-3':
            'This package provides documentation for libjing-java, libtrang-'
            'java, and libdtdinst-java'
    },
    'language-pack-gnome-fa-base': {
        '1:20.10+20201015':
            'Translation data for all supported GNOME packages for: '
            'Persian\n\nThis package provides the bulk of translation data '
            'and is updated only seldom. language-pack-gnome-fa provides '
            'frequent translation updates, so you should install this as well.'
    },
    'libadasockets9': {
        '1.11.1-4':
            'This package provides a binding for socket services to be used '
            'with GNAT (the GNU Ada compiler). One can use it to write '
            'clients and servers that will talk with programs written in Ada '
            'or any other programming language.\n\nThis package contains the '
            'library needed to execute Ada program using sockets.'
    },
    'libbg-dev': {
        '2.04+dfsg-2':
            'This package contains a collection of libraries written by Bruce '
            'Guenter and put in use in various packages.\n\nThe library '
            'collection is mandatory to build most of software packages '
            'available at http://untroubled.org.\n\nThis package contains the '
            'development files.'
    },
    'libcgi-application-plugin-dbh-perl': {
        '4.04-2':
            'CGI::Application::Plugin::DBH adds access to a DBI database '
            'handle to your CGI::Application modules. Lazy loading is used to '
            'prevent a database connection from being made if the dbh method '
            'is not called during the request.  In other words, the database '
            'connection is not created until it is actually needed.'
    },
    'libcxsparse3': {
        '1:5.8.1+dfsg-2':
            'Suitesparse is a collection of libraries for computations '
            'involving sparse matrices.\n\nThe CXSparse library provides '
            'several matrix algorithms. The focus is on direct methods; '
            'iterative methods and solvers for eigenvalue problems are beyond '
            'the scope of this package.\n\nThe performance of the sparse '
            'factorization methods in CXSparse will not be competitive with '
            'UMFPACK or CHOLMOD, but the codes are much more concise and easy '
            'to understand. Other methods are competitive.'
    },
    'libeclipse-linuxtools-java': {
        '7.4.0+dfsg.1-2':
            'The Linux Tools project aims to bring a full-featured C and C++ '
            'IDE to Linux developers. It builds on the source editing and '
            'debugging features of the CDT and integrate popular native '
            'development tools such as Valgrind, OProfile, RPM, SystemTap, '
            'GCov, GProf, LTTng, etc. Current projects include LTTng trace '
            'viewers and analyzers, an RPM .spec editor, a Valgrind heap '
            'usage analysis tool, and OProfile and Perf call profiling '
            'tools.\n\nThis package only builds the piechart library.'
    },
    'libforms-doc': {
        '1.2.3-1.4':
            'This package contains PDF and HTML documentation for the XForms '
            'library.'
    },
    'libghc-cabal-doctest-dev': {
        '1.0.8-1build1':
            "Currently (beginning of 2017), there isn't a `cabal doctest` "
            "command. Yet to properly work, doctest needs plenty of "
            "configuration. This library provides the common bits for writing "
            "custom Setup.hs until that is resolved.\n\nThis package provides "
            "a library for the Haskell programming language. See "
            "http://www.haskell.org/ for more information on Haskell."
    },
    'libghc-hsyaml-aeson-doc': {
        '0.2.0.0-2build3':
            "This Haskell module provides a compatibility layer atop HsYAML "
            "which allows decoding YAML documents in the more limited JSON "
            "data-model while also providing convenience by reusing aeson's "
            "'FromJSON' instances for decoding the YAML data into native "
            "Haskell data types.\n\nThis package provides the documentation "
            "for a library for the Haskell programming language. See "
            "http://www.haskell.org/ for more information on Haskell."
    },
    'libghc-sbv-doc': {
        '8.7-1build2':
            'Express properties about Haskell programs and automatically '
            'prove them using SMT (Satisfiability Modulo Theories) '
            'solvers.\n\nThis package provides the documentation for a '
            'library for the Haskell programming language. See '
            'http://www.haskell.org/ for more information on Haskell.'
    },
    'libglobus-gass-cache-dev': {
        '10.1-2':
            'The Grid Community Toolkit (GCT) is an open source software '
            'toolkit used for building grid systems and applications. It is a '
            'fork of the Globus Toolkit originally created by the Globus '
            'Alliance. It is supported by the Grid Community Forum (GridCF) '
            'that provides community-based support for core software packages '
            'in grid computing.\n\nThe libglobus-gass-cache-dev package '
            'contains: Globus Gass Cache Development Files'
    },
    'libgts-dev': {
        '0.7.6+darcs121130-4':
            'The GTS Library is intended to provide a set of useful functions '
            'to deal with 3D surfaces meshed with interconnected '
            'triangles.\n\nThis package contains the headers and development '
            'libraries needed to build applications using GTS.'
    },
    'libiso9660++-dev': {
        '2.1.0-2':
            'This package contains C++ development files (headers and static '
            'library) for the libiso9660 library.\n\nThis library is made to '
            'read and write ISO9660 filesystems; those filesystems are mainly '
            'used on CDROMs.'
    },
    'libkf5akonadinotes-data': {
        '4:20.08.1-0ubuntu1':
            'This library provides notes manipulation helpers using the '
            'Akonadi PIM data server.\n\nThis package is part of the KDE '
            'Development Platform PIM libraries module.'
    },
    'liblog4shib-dev': {
        '2.0.0-2build1':
            'log4shib provides a library of C++ classes for flexible logging '
            'to files, syslog, and other destinations.  It is modeled after '
            'the log4j Java library, staying as close to that API as is '
            'reasonable.\n\nlog4shib is a fork of the log4cpp library with '
            'additional fixes and modifications to improve its thread safety '
            'and robustness.  It is primarily intended for use by the '
            'Shibboleth web authentication system.\n\nThis package contains '
            'the headers and other necessary files to build applications or '
            'libraries that use or extend the log4shib library.'
    },
    'libmono-microsoft-build-tasks-v4.0-4.0-cil': {
        '6.8.0.105+dfsg-3':
            'Mono is a platform for running and developing applications based '
            'on the ECMA/ISO Standards. Mono is an open source effort led by '
            'Xamarin. Mono provides a complete CLR (Common Language Runtime) '
            'including compiler and runtime, which can produce and execute '
            'CIL (Common Intermediate Language) bytecode (aka assemblies), '
            'and a class library.\n\nThis package contains the Mono '
            'Microsoft.Build.Tasks.v4.0 library for CLI 4.0.'
    },
    'libnet1-doc': {
        '1.1.6+dfsg-3.1build1':
            'libnet provides a portable framework for low-level network '
            'packet writing and handling.\n\nlibnet features portable packet '
            'creation interfaces at the IP layer and link layer, as well as a '
            'host of supplementary functionality.\n\nUsing libnet, quick and '
            'simple packet assembly applications can be whipped up with '
            'little effort. With a bit more time, more complex programs can '
            'be written (Traceroute and ping were easily rewritten using '
            'libnet and libpcap).\n\nThis package contains the documentation '
            'files for developers.'
    },
    'libortp13': {
        '1:1.0.2-1.1':
            'This library implements RFC 1889 (RTP) and offers an easy to use '
            'API with high-level and low-level access. It is part of '
            'Linphone.\n\nThe main features are support for multiple profiles '
            '(AV profile RFC 1890 being the default one); an optional packet '
            'scheduler for synchronizing RTP recv and send; blocking or '
            'non-blocking IO for RTP sessions; multiplexed IO; some of RFC '
            '2833 for telephone events over RTP.'
    },
    'libpostproc-dev': {
        '7:4.3.1-4ubuntu1':
            'FFmpeg is the leading multimedia framework, able to decode, '
            'encode, transcode, mux, demux, stream, filter and play pretty '
            'much anything that humans and machines have created. It supports '
            'the most obscure ancient formats up to the cutting edge.\n\nThis '
            'library provides video post processing.\n\nThis package contains '
            'the development files.'
    },
    'libreoffice-style-colibre': {
        '1:7.0.3-0ubuntu0.20.10.1':
            'LibreOffice is a full-featured office productivity suite that '
            'provides a near drop-in replacement for Microsoft(R) '
            'Office.\n\nThis package contains the "colibre" symbol style - a '
            'icon theme which follow Microsoft(R) Offices color scheme.',
        '1:7.0.2-0ubuntu1':
            'LibreOffice is a full-featured office productivity suite that '
            'provides a near drop-in replacement for Microsoft(R) '
            'Office.\n\nThis package contains the "colibre" symbol style - a '
            'icon theme which follow Microsoft(R) Offices color scheme.',
    },
    'librust-hexyl-dev': {
        '0.8.0-2':
            'This package contains the source for the Rust hexyl crate, '
            'packaged by debcargo for use with cargo and dh-cargo.'
    },
    'libseccomp-dev': {
        '2.4.3-1ubuntu4':
            "This library provides a high level interface to constructing, "
            "analyzing and installing seccomp filters via a BPF passed to the "
            "Linux Kernel's prctl() syscall.\n\nThis package contains the "
            "development files."
    },
    'libstk-4.6.1': {
        '4.6.1+dfsg-3':
            'The Sound Synthesis Toolkit is a C++ library with '
            'implementations of several sound synthesis algorithms, starting '
            'from Frequency Modulation, over Physical Modelling and others. '
            'It can be used as a library, but it also provides some nice '
            'software synthesizers.'
    },
    'libtoolkit-perl': {
        '0.0.2-2':
            'The Toolkit module provides a standard location to store modules '
            'that you use all the time, and then loads them for you '
            'automatically. For example, instead of always writing:\n\nuse '
            'strict;\nuse warnings;\nuse Carp;\nuse Smart::Comments;\nin '
            'every program/module, you can just write:\n\nuse Toolkit;\nand '
            'put all your favorite modules in a file.'
    },
    'libwcstools-dev': {
        '3.9.6-1':
            'WCSTools is a set of software utilities, written in C, which '
            'create, display and manipulate the world coordinate system of a '
            'FITS or IRAF image, using specific keywords in the image header '
            'which relate pixel position within the image to position on the '
            'sky.  Auxiliary programs search star catalogs and manipulate '
            'images.\n\nThis package contains the files needed for '
            'development.'
    },
    'libzlcore-dev': {
        '0.12.10dfsg2-4build1':
            'This package contains development files for the ZLibrary '
            'core.\n\nZLibrary is a cross-platform library to build '
            'applications running on desktop Linux, Windows, different '
            'Linux-based PDAs using this library.'
    },
    'lxsession-data': {
        '0.5.3-2ubuntu1':
            'LXSession is the default session manager for the Lightweight X11 '
            'Desktop Environment (LXDE).\n\nThis package provides common '
            'files for lxsession and supplementary packages.'
    },
    'mono-source': {
        '6.8.0.105+dfsg-3':
            'Mono is a platform for running and developing applications based '
            'on the ECMA/ISO Standards. Mono is an open source effort led by '
            'Xamarin. Mono provides a complete CLR (Common Language Runtime) '
            'including compiler and runtime, which can produce and execute '
            'CIL (Common Intermediate Language) bytecode (aka assemblies), '
            'and a class library.\n\nThis package contains an archive of the '
            'source code used to build the Mono packages in Debian.'
    },
    'node-array-uniq': {
        '2.1.0-1':
            'This module creates an array without duplicates. It is already '
            'pretty fast, but will be much faster when Set becomes available '
            'in V8 (especially with large arrays).\n\nNode.js is an '
            'event-based server-side JavaScript engine.'
    },
    'node-puka': {
        '1.0.1+dfsg-1':
            "A Node.js module that provides a simple and platform-agnostic "
            "way to build shell commands with arguments that pass through "
            "your shell unaltered and with no unsafe side effects, whether "
            "you are running on Windows or a Unix-based OS.\n\nIt is useful "
            "when launching a child process from Node.js using a shell (as "
            "with child_process.exec); in that case you have to construct "
            "your command as a single string instead of using an array of "
            "arguments. And doing that can be buggy (if not dangerous) if you "
            "don't take care to quote any arguments correctly for the shell "
            "you're targeting, and the quoting has to be done differently on "
            "Windows and non-Windows shells.\n\nNode.js is an event-based "
            "server-side JavaScript engine."
    },
    'opendbx-utils': {
        '1.4.6-14':
            "OpenDBX provides a simple and lightweight API for interfacing "
            "native relational database APIs in a consistent way. By using "
            "the OpenDBX API you don't have to adapt your program to the "
            "different database APIs by yourself.\n\nThis package provides "
            "the odbx-sql utility application for accessing database content "
            "directly via libopendbx and the opendbx test suite for verifying "
            "that various backends are working"
    },
    'php-cache-lite': {
        '1.8.2-1build3':
            'This package is a little cache system optimized for file '
            'containers. It is fast and safe (because it uses file locking '
            'and/or anti-corruption tests).'
    },
    'potool': {
        '0.19-1':
            "This package contains the filter program 'potool', as well as a "
            "few helper scripts:\npoedit  - helps editing of po files in your "
            "favourite editor\npostats - prints statistics of how much of a "
            "file is translated\n"
    },
    'python-netifaces-dbg': {
        '0.10.4-1ubuntu4':
            'netifaces provides a (hopefully portable-ish) way for Python '
            'programmers to get access to a list of the network interfaces on '
            'the local machine, and to obtain the addresses of those network '
            'interfaces.\n\nThis package contains debug symbols of '
            'python-netifaces.'
    },
    'python3-distutils-extra': {
        '2.45':
            'This package provides additional functions to Python\'s '
            'distutils and setuptools. It allows you to easily integrate '
            'gettext, icons and GNOME documentation into your build and '
            'installation process.\n\nIt also provides an "auto" module which '
            'provides a "do what I mean" automatic build system; if you stick '
            'to the conventions, you do not need to write setup.cfg, '
            'POTFILES.in, or MANIFEST.in, and setup.py just needs to have the '
            'package metadata (such as project name and version).'
    },
    'python3-mbed-ls': {
        '1.6.2+dfsg-3':
            'This module detects and lists "Mbed Enabled" devices connected '
            'to the host computer.\n\nmbedls provides the following '
            'information for all connected boards using console (terminal) '
            'output:\n\n-  Mbed OS platform name\n-  mount point (MSD or '
            'disk)\n-  serial port\nThis package contains the module for '
            'Python 3 and the mbedls utility.'
    },
    'python3-quark-sphinx-theme': {
        '0.5.1-2':
            "Quark is a Sphinx theme specifically designed to look and work "
            "well within the limitations of the Qt toolkit's QTextBrowser. "
            "This theme was originally designed for the bundled manual of "
            "SpeedCrunch.\n\nThis is the Python 3 version of the package."
    },
    'qflow-tech-osu018': {
        '1.3.17+dfsg.1-2':
            'Qflow is an open-source digital synthesis flow.\n\nThis package '
            'only contains the technology files needed for qflow. (osu018)'
    },
    'r-cran-modeltools': {
        '0.2-23-2build1':
            'The r-cran-modeltools package is a GNU R package providing a '
            'collection of tools to deal with statistical models.'
    },
    'rt4-fcgi': {
        '4.4.4-2':
            'Request Tracker (RT) is a ticketing system which enables a group '
            'of people to intelligently and efficiently manage tasks, issues, '
            'and requests submitted by a community of users. It features web, '
            'email, and command-line interfaces (see the package '
            'rt4-clients).\n\nRT manages key tasks such as the '
            'identification, prioritization, assignment, resolution, and '
            'notification required by enterprise-critical applications, '
            'including project management, help desk, NOC ticketing, CRM, and '
            'software development.\n\nThis package provides the 4 series of '
            'RT. It can be installed alongside the 3.8 series without any '
            'problems.\n\nThis package provides an external FCGI interface '
            'for web servers including, but not limited to, nginx, and is not '
            'needed for web servers such as Apache which invoke FCGI programs '
            'directly.'
    },
    'ruby-rails-assets-jquery-textchange': {
        '0.2.3-1ubuntu1':
            'jQuery TextChange Plugin for rails '
            'applications.\n\nrails-assets.org provided library '
            '(automatically generated from its bower package)'
    },
    'sidplay-base': {
        '1.0.9-7build2':
            'This is a simple music player for C64 and C128 tunes, also known '
            'as SID tunes. The package includes a program (sid2wav) for '
            'creating .wav files.'
    },
    'sword-text-gerlut1545': {
        '1.2-0ubuntu2':
            "This is Martin Luther's German 1545 Version of the Holy "
            "Bible.\n\nThis package contains data that requires a viewer to "
            "be seen properly, such as GnomeSword, BibleTime or "
            "Kio-Sword.\n\nHomepage: "
            "http://www.crosswire.org/sword/modules/ModInfo.jsp?modName=GerLut1545\n"
    },
    'tran': {
        '5-2':
            'This tool lets you transliterate, with a ¼-hearted attempt at '
            'transcription, both ways between Latin and a number of other '
            'writing scripts.  Thus for example the word “Debian” is “Дэбян” '
            'in Cyrillic or “Δεβιαν” in Greek. Conversion to Latin lets you '
            'understand foreign text (at least names if not meaning), '
            'conversion from Latin is for fun, i10n testing, '
            'etc.\n\nSupported scripts:\n* latin\n* cyrillic\n* greek\n* '
            'devanagari\n* futhark (runes)\n* hiragana\n* katakana\n* old '
            'italic\n* gothic (Ulfilas\' — you may be looking for fraktur '
            'instead)\n* georgian (mkhedruli)\n* mtavruli (also Georgian)\n* '
            'armenian\n* ascii (Latin without diacritics or digraphs)\n* '
            'fullwidth (double-width ASCII)\n* smallcaps\n* Unicode Plane 1 '
            '"math" characters: bold, italic, bold italic, script,\n  bold '
            'script, fraktur, double-struck, bold fraktur, sans-serif,\n  '
            'sans-serif bold, sans-serif italic, sans-serif bold italic,\n  '
            'monospace\n* enclosed alphanumerics: circled, parenthesized, '
            'squared, negative\n  circled, negative squared, regional '
            'indicators\n'
    },
    'valgrind': {
        '1:3.16.1-1ubuntu1':
            'Valgrind is a system for debugging and profiling Linux programs. '
            'With its tool suite you can automatically detect many memory '
            'management and threading bugs, avoiding hours of frustrating '
            'bug-hunting and making your programs more stable. You can also '
            'perform detailed profiling to help speed up your programs and '
            'use Valgrind to build new tools.\n\nThe Valgrind distribution '
            'currently includes six production-quality tools:\n* a memory '
            'error detector (Memcheck)\n* two thread error detectors '
            '(Helgrind and DRD)\n* a cache and branch-prediction profiler '
            '(Cachegrind)\n* a call-graph generating cache and '
            'branch-prediction profiler (Callgrind)\n* a heap profiler '
            '(Massif)\nIt also includes three experimental tools:\n* a '
            'stack/global array overrun detector (SGCheck)\n* a second heap '
            'profiler that examines how heap blocks are used (DHAT)\n* a '
            'SimPoint basic block vector generator (BBV)\n'
    },
    'xcursor-themes': {
        '1.0.6-0ubuntu1':
            'This package contains the additional base X cursor themes -- '
            'handhelds, redglass, and whiteglass. These themes are not '
            'essential for the X server to run.'
    }
}

def test_big_struct(tmpdir, capsys):
    # Generate a big load of data for analysis (but not so big it takes ages)'
    # note that two levels of fields which require merging (metavar and
    # release) are included to test recursive merge
    data = {
        'ID{num:04d}-{sub:02d}'.format(num=num, sub=sub): {
            'id': 'ID{num:04d}-{sub:02d}'.format(num=num, sub=sub),
            'releases': {
                release: {
                    package: {
                        'version': version,
                        'description': apt_cache[package][version],
                        'metavars': {
                            metavar: {
                                num: list(range(num))
                                for num in [
                                    random.randint(1, 50)
                                    for i in range(random.randint(2, 10))
                                ]
                            }
                            for metavar in random.choices(
                                ('foo', 'bar', 'baz', 'quux', 'xyzzy'),
                                weights=(5, 5, 5, 4, 2), k=random.randint(2, 4))
                        }
                    }
                    for package in (random.choice(list(apt_cache.keys())),)
                    for version in (next(iter(apt_cache[package])),)
                }
                for release in random.choices(
                    ('precise', 'trusty', 'xenial', 'bionic', 'focal', 'groovy'),
                    weights=(3, 3, 4, 4, 5, 6), k=random.randint(2, 4))
            }
        }
        for num in range(40)
        for sub in range(random.randint(1, 6))
    }

    filename = str(tmpdir.join('mergetest.json'))
    with open(filename, 'w') as fp:
        json.dump(data, fp)
    assert cli.main([filename, '--hide-range', '--hide-count']) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == """\
{
    str pattern="ID00dd-0d": {
        'id': str pattern="ID00dd-0d",
        'releases': {
            str: {
                str: {
                    'description': str,
                    'metavars': {
                        str: {
                            str of int pattern=d: [ int ]
                        }
                    },
                    'version': str
                }
            }
        }
    }
}"""
