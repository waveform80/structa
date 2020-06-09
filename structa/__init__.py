__project__      = 'structa'
__version__      = '0.1'
__keywords__     = ['structure', 'analysis', 'json']
__author__       = 'Dave Jones'
__author_email__ = 'dave@waveform.org.uk'
__url__          = 'https://github.com/waveform80/structa'
__platforms__    = 'ALL'

__requires__ = []
__extra_requires__ = {
    'doc':  ['sphinx'],
    'test': ['pytest', 'coverage'],
}

__classifiers__ = [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
]

__entry_points__ = {
    'console_scripts': [
        'structa = structa.ui:main',
    ],
}
