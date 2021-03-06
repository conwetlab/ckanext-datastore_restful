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

from __future__ import unicode_literals
import StringIO
import unicodecsv as csv
from xml.dom.minidom import parseString
import unicodedata


def csv_parser(result):
    f = StringIO.StringIO()
    wr = csv.writer(f, encoding='utf-8')

    header = [x['id'] for x in result['fields'] if x['id'] != '_id']
    wr.writerow(header)

    for record in result['records']:
        wr.writerow([record[column] for column in header])
    return f.getvalue()


def xml_parser(result, root):

    # Obtained from https://gist.github.com/reimund/5435343/ and modified to fulfill our needs
    def xml_escape(s):
        if type(s) in (str, unicode):
            s = s.replace('&', '&amp;')
            s = s.replace('"', '&quot;')
            s = s.replace('\'', '&apos;')
            s = s.replace('<', '&lt;')
            s = s.replace('>', '&gt;')
        return s

    def key_is_valid_xml(key):
        """Checks that a key is a valid XML name"""
        test_xml = '<?xml version="1.0" encoding="UTF-8" ?><%s>foo</%s>' % (key, key)
        try:
            parseString(test_xml)
            return True
        except Exception:   # minidom does not implement exceptions well
            return False

    def dict2xml(d, root_node=None, start=False):
        wrap = True if root_node is not None or (isinstance(d, list) and start) else False
        root = 'rows' if None == root_node or not key_is_valid_xml(root_node) else root_node
        root_singular = root[:-1] if 's' == root[-1] else root
        xml = ''
        children = []

        if isinstance(d, dict):
            for key, value in dict.items(d):
                if key.startswith('__'):
                    xml = xml + ' ' + key[2:] + '="' + xml_escape(unicode(value)) + '"'
                else:
                    children.append(dict2xml(value, key))
        elif isinstance(d, list):
            for value in d:
                children.append(dict2xml(value, root_singular))
        elif type(d) in (str, int, bool, float, unicode):
            #Append strings, numbers and booleans as single nodes
            children.append(unicode(d))
        else:
            TypeError('Unsupported data type: %s (%s)' % (d, type(d).__name__))

        end_tag = '>' if len(children) > 0 else '/>'

        if wrap or isinstance(d, dict):
            xml = '<' + root + xml + end_tag

        if len(children) > 0:
            for child in children:
                xml = xml + child

            if wrap or isinstance(d, dict):
                xml = xml + '</' + root + '>'

        return xml

    # It's needed to remove accents and not ascii characters
    xml = unicodedata.normalize('NFKD', dict2xml(result, root, True)).encode('ascii', 'ignore')
    return parseString(xml).toprettyxml()
