# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN DataStore Restful Extension.

# CKAN DataStore Restful Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN DataStore Restful Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN DataStore Restful Extension.  If not, see <http://www.gnu.org/licenses/>.

import ckanext.datastore_restful.response_parser as response_parser

from nose_parameterized import parameterized
from nose.tools import assert_equal

CONTENT_TO_CONVERT_IN_CSV = {
    "fields": [
        {
            "type": "int4",
            "id": "_id"
        },
        {
            "type": "text",
            "id": "nombre"
        },
        {
            "type": "text",
            "id": "apellido1"
        },
        {
            "type": "timestamp",
            "id": "fecha_nombramiento"
        },
        {
            "type": "timestamp",
            "id": "fecha_cese"
        }
    ],
    "records": [
        {
            "apellido1": "ABC",
            "nombre": "DEF",
            "fecha_cese": "1991-07-13T00:00:00",
            "_id": 1,
            "fecha_nombramiento": "1987-07-22T00:00:00"
        },
        {
            "apellido1": "GHI",
            "nombre": "JKL",
            "fecha_cese": "1991-07-13T00:00:00",
            "_id": 2,
            "fecha_nombramiento": "1987-07-22T00:00:00"
        },
        {

            "apellido1": "MNO",
            "nombre": "PQR",
            "_id": 3,
            "fecha_nombramiento": "1991-07-13T00:00:00",
            "fecha_cese": ""
        }
    ]
}

XML_TEST_CASES = [
    {
        'content': [{'test': 'a'}, {'test': 'b'}],
        'xml': '<?xml version="1.0" ?>\n<rows>\n\t<row>\n\t\t<test>a</test>\n\t</row>\n\t<row>\n\t\t<test>b</test>\n\t</row>\n</rows>\n'
    },
    {
        'content': [{'test': 'a'}, {'test': 'b'}],
        'xml': '<?xml version="1.0" ?>\n<records>\n\t<record>\n\t\t<test>a</test>\n\t</record>\n\t<record>\n\t\t<test>b</test>\n\t</record>\n</records>\n',
        'field': 'records'
    },
    {
        'content': [{'test': 'a', 'another': {'c': 'value'}}, {'test': 'b'}],
        'xml': '''<?xml version="1.0" ?>\n<rows>\n\t<row>\n\t\t<test>a</test>\n\t\t<another>\n\t\t\t<c>value</c>\n\t\t</another>\n\t</row>
\t<row>\n\t\t<test>b</test>\n\t</row>\n</rows>\n'''
    },
    {
        'content': {'original': 'test', 'another_value': 3, 'ringos': ['a', 'b', 'c']},
        'xml': '''<?xml version="1.0" ?>\n<rows>\n\t<another_value>3</another_value>\n\t<ringos>\n\t\t<ringo>a</ringo>\n\t\t<ringo>b</ringo>
\t\t<ringo>c</ringo>\n\t</ringos>\n\t<original>test</original>\n</rows>\n'''
    },
    {
        'content': {'original': 'test', 'another_value': 3},
        'xml': '<?xml version="1.0" ?>\n<fields>\n\t<another_value>3</another_value>\n\t<original>test</original>\n</fields>\n',
        'field': 'fields'
    },
    {
        'content': {'original': {'__attr': 'test'}, 'another_value': 3},
        'xml': '<?xml version="1.0" ?>\n<fields>\n\t<another_value>3</another_value>\n\t<original attr="test"/>\n</fields>\n',
        'field': 'fields'
    },
    {
        'content': {'original<': {'__attr': 'test'}, 'another_value': 3},
        'exception': True
    }
]

EXPECTED_CSV = '''nombre,apellido1,fecha_nombramiento,fecha_cese\r
DEF,ABC,1987-07-22T00:00:00,1991-07-13T00:00:00\r
JKL,GHI,1987-07-22T00:00:00,1991-07-13T00:00:00\r
PQR,MNO,1991-07-13T00:00:00,\r\n'''


class TestParsers(object):
    '''Tests for the module.'''

    def test_csv_parser(self):
        result = response_parser.csv_parser(CONTENT_TO_CONVERT_IN_CSV)
        assert_equal(EXPECTED_CSV, result)

    @parameterized.expand([
        (XML_TEST_CASES[0],),
        (XML_TEST_CASES[1],),
        (XML_TEST_CASES[2],),
        (XML_TEST_CASES[3],),
        (XML_TEST_CASES[4],),
        (XML_TEST_CASES[5],),
    ])
    def test_xml_parser(self, test_case):
        root = None if not 'field' in test_case else test_case['field']
        exception = False if not 'exception' in test_case else test_case['exception']

        try:
            result = response_parser.xml_parser(test_case['content'], root)
            assert exception is False
            assert_equal(test_case['xml'], result)
        except Exception as e:
            print e
            assert exception is True
