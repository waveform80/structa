# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2020-2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import csv
import json
from unittest import mock

import pytest
from ruamel import yaml

from structa.analyzer import ValidationWarning
from structa.source import Source


@pytest.fixture
def table(request):
    return [
        ['Name', 'Nationality'],
        ['Johann Gottfried Hübert', 'German'],
        ['Francis Bacon', 'British'],
        ['August Sallé', 'French'],
        ['Adam Bøving', 'Danish'],
        ['Justus Henning Böhmer', 'German'],
        ['Émilie du Châtelet', 'French'],
        ['Mihály Csokonai Vitéz', 'Hungarian'],
        ['Carl von Linné', 'Swedish'],
        ['François Marie Arouet', 'French'],
        # The following rows cannot be encoded in latin-1
        ['Zdenek Bouček', 'Czech'],
        ['Ruđer Josip Bošković', 'Croatian'],
        ['Hugo Kołłątaj', 'Polish'],
    ]


def test_source_sample_limit(tmpdir):
    filename = str(tmpdir.join('data.file'))
    with open(filename, 'wb') as f:
        f.write(b'\xff' * 2000)
    with open(filename, 'rb') as f:
        s = Source(f, sample_limit=1000)
        assert s._sample_bytes() == b'\xff' * 1000
        assert f.tell() == 1000
        # Check query idempotency
        assert s._sample_bytes() == b'\xff' * 1000
        assert f.tell() == 1000


def test_source_encoding(tmpdir, table):
    filename = str(tmpdir.join('latin-1.csv'))
    with open(filename, 'w', encoding='latin-1') as f:
        writer = csv.writer(f)
        for row in table[:-3]:
            writer.writerow(row)
    with open(filename, 'rb') as f:
        with pytest.warns(ValidationWarning):
            assert Source(f).encoding.lower() == 'iso-8859-1'
        f.seek(0)
        with pytest.raises(UnicodeError):
            Source(f, encoding='utf-8').data

    filename = str(tmpdir.join('utf-8.csv'))
    with open(filename, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow(row)
    with open(filename, 'rb') as f:
        assert Source(f).encoding.lower() == 'utf-8'


def test_source_format(tmpdir, table):
    filename = str(tmpdir.join('data.csv'))
    with open(filename, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow(row)
    with open(filename, 'rb') as f:
        assert Source(f).format == 'csv'
        f.seek(0)
        with pytest.raises(ValueError):
            Source(f, format='json').data


def test_source_csv_dialect(tmpdir, table):
    comma_file = str(tmpdir.join('comma.csv'))
    tab_file = str(tmpdir.join('tab.csv'))
    passwd_file = str(tmpdir.join('weird.csv'))
    json_file = str(tmpdir.join('data.json'))

    with open(comma_file, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow(row)
    with open(tab_file, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        for row in table:
            writer.writerow(row)
    with open(passwd_file, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=':')
        for row in table:
            writer.writerow(row)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(table, f)

    with open(comma_file, 'rb') as f:
        s = Source(f)
        assert s.csv_dialect.delimiter == ','
        assert s.csv_dialect.quotechar == '"'
    with open(tab_file, 'rb') as f:
        s = Source(f)
        assert s.csv_dialect.delimiter == '\t'
        assert s.csv_dialect.quotechar == '"'
    with open(passwd_file, 'rb') as f:
        s = Source(f, format='csv', csv_delimiter=':', csv_quotechar="'")
        assert s.csv_dialect.delimiter == ':'
        assert s.csv_dialect.quotechar == "'"
    with open(json_file, 'rb') as f:
        assert Source(f).csv_dialect is None


def test_source_csv_data(tmpdir, table):
    data_file = str(tmpdir.join('data.csv'))
    with open(data_file, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow(row)
    with open(data_file, 'rb') as f:
        s = Source(f)
        assert s.data == table[1:]
        # Check repeat-query idempotency
        assert s.data == table[1:]


def test_source_json_data(tmpdir, table):
    data_file = str(tmpdir.join('data.json'))
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(table, f)
    with open(data_file, 'rb') as f:
        s = Source(f)
        assert s.data == table
        # Check repeat-query idempotency
        assert s.data == table


def test_source_yaml_data(tmpdir, table):
    data_file = str(tmpdir.join('data.yaml'))
    with open(data_file, 'w', encoding='utf-8') as f:
        yaml.dump(table, f)
    with open(data_file, 'rb') as f:
        s = Source(f)
        assert s.data == table
        # Check repeat-query idempotency
        assert s.data == table


def test_source_detect_xml(tmpdir):
    filename = str(tmpdir.join('data.xml'))
    with open(filename, 'w') as f:
        f.write('<?xml version="1.0" encoding="utf-8" ?><doc></doc>')
    with open(filename, 'rb') as f:
        assert Source(f).format == 'xml'
    with open(filename, 'w') as f:
        f.write('\n<?xml version="1.0" encoding="utf-8" ?><doc></doc>')
    with open(filename, 'rb') as f:
        with pytest.warns(ValidationWarning):
            assert Source(f).format == 'xml'
    with open(filename, 'w') as f:
        f.write('<doc><header></header><footer></footer></doc>')
    with open(filename, 'rb') as f:
        with pytest.warns(ValidationWarning):
            assert Source(f).format == 'xml'


def test_source_detect_csv(tmpdir, table):
    filename = str(tmpdir.join('data.csv'))
    with open(filename, 'w') as f:
        f.write('\r\n'.join(
            ','.join(
                '"{value}"'.format(value=value.replace('"', '""'))
                for value in row
            )
            for row in table
        ))
    with open(filename, 'rb') as f:
        assert Source(f).format == 'csv'


def test_source_detect_yaml_missing(tmpdir):
    with mock.patch('structa.source.yaml', None):
        filename = str(tmpdir.join('data.yaml'))
        with open(filename, 'w') as f:
            f.write("""\
structa:
  language: Python
  versions: 3.5, 3.6, 3.7, 3.8
  os: all
""")
        with open(filename, 'rb') as f:
            with pytest.raises(ImportError):
                Source(f).data


def test_source_detect_yaml(tmpdir):
    filename = str(tmpdir.join('data.yaml'))
    with open(filename, 'w') as f:
        f.write("""\
structa:
  language: Python
  versions: 3.5, 3.6, 3.7, 3.8
  os: all
""")
    with open(filename, 'rb') as f:
        assert Source(f).format == 'yaml'


def test_source_unknown(tmpdir):
    filename = str(tmpdir.join('data.yaml'))
    with open(filename, 'w') as f:
        f.write('\n' * 100)
    with open(filename, 'rb') as f:
        assert Source(f).format == 'unknown'


def test_source_bad_data(tmpdir):
    filename = str(tmpdir.join('data.yaml'))
    with open(filename, 'w') as f:
        f.write('\n' * 100)
    with open(filename, 'rb') as f:
        with pytest.raises(ValueError):
            Source(f).data
