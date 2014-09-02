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

'''
Tests for the ckanext.datastore_restful extension.
This tests require nose_parameterized to run.
'''
import ckanext.datastore_restful.controller as controller
import ckanext.datastore_restful.utils as utils
import json
import re
import copy
from mock import MagicMock, Mock
from nose_parameterized import parameterized
from nose.tools import assert_equal
from nose.tools import assert_not_equal

DEFAULT_FIELDS = [{'id': 'test', 'type': 'int'}, {'id': 'test1', 'type': 'text'}]
DEFAULT_RECORDS = [{'test': 'test', 'test1': 'test1'}, {'test': '_test', 'test1': '_test1', controller.IDENTIFIER: 1}]
INVALID_FIELDS = [{'_id': 'test', 'type': 'int'}, {'id': 'test1', '_type': 'text'}]
FIELDS_PK = [{'id': controller.IDENTIFIER, 'type': 'int'}, {'id': 'test1', 'type': 'text'}]


DEFAULT_LOGIC_FUNCTION_RES = {
    'fields': DEFAULT_FIELDS,
    'records': DEFAULT_RECORDS,
    'resource_id': 'test'
}

DEFAULT_SEARCH = {
    '$q': 'full_text',
    '$plain': 'text',
    '$language': 'es',
    '$limit': 1,
    '$offset': 3,
    '$fields': 'test, test1',
    '$sort': 'test ASC',
    'test': 'a value',
    'test1': 'another value'
}

MALIGN_SEARCH = {
    'filters': {
        'test': 'not valid',
        'test1': 'not valid'
    },
    '$q': 'full_text',
    '$plain': 'text',
    '$language': 'es',
    '$limit': 1,
    '$offset': 3,
    '$fields': 'test, test1',
    '$sort': 'test ASC',
}

##### SIDE EFFECTS #####
VALUE_ERROR = {
    'type': 'Bad request',
    'exception': ValueError('Value Error Example'),
    'status': 400
}

DATA_ERROR = {
    'type': 'Integrity Error',
    'exception': controller.dictization_functions.DataError('Example Data Error'),
    'status': 400
}

NOT_AUTHORIZED = {
    'type': 'Access denied',
    'exception': controller.plugins.toolkit.NotAuthorized('Access to this resouce is not allowed'),
    'status': 403
}

NOT_FOUND = {
    'type': 'Not found',
    'exception': controller.plugins.toolkit.ObjectNotFound('Object Not Found'),
    'status': 404
}

VALIDATION_ERROR = {
    'type': 'Validation Error',
    'exception': controller.plugins.toolkit.ValidationError('Validation Error Found'),
    'status': 409
}

SEARCH_QUERY_ERROR = {
    'type': 'Search Query Error',
    'exception': controller.search.SearchQueryError('Query Error'),
    'status': 400
}

SEARCH_ERROR = {
    'type': 'Search Error',
    'exception': controller.search.SearchError('Error SQL'),
    'status': 409
}

SEARCH_INDEX_ERROR = {
    'type': 'Search Index Error',
    'exception': controller.search.SearchIndexError('Index Error'),
    'status': 500
}

##### ACCEPT TYPE AND THE EXPECTED RESPONSE FOR THIS TYPE #####
JSON = {'type': utils.JSON, 'expected': 'application/json', 'response': 'JSON CONTENT', }
XML = {'type': utils.XML, 'expected': 'application/xml', 'response': 'XML CONTENT'}
CSV = {'type': utils.CSV, 'expected': 'text/csv', 'response': 'CSV CONTENT'}

CONTENT_TYPES = {JSON['expected']: utils.JSON, XML['expected']: utils.XML, CSV['expected']: utils.CSV}

##### EXCEPTED ERRORS #####
NOT_FOUND_ENTRY = {
    'status': 404,
    'type': 'Not found',
    'message': 'The element .+ does not exist in the resource .+'
}

ENTRY_PK_MISMATCH = {
    'status': 409,
    'type': 'Validation Error',
    'message': 'The entry identifier cannot be changed'
}

INVALID_CONTENT_CREATE_RESOURCE = {
    'status': 409,
    'type': 'Validation Error',
    'message': 'Only lists of dicts can be placed to create resources'
}

PK_CANNOT_BE_INCLUDED = {
    'status': 409,
    'type': 'Validation Error',
    'message': 'The field \'%s\' cannot be used since it\'s used internally' % controller.IDENTIFIER
}

INVALID_CONTENT_UPSERT_ENTRY = {
    'status': 409,
    'type': 'Validation Error',
    'message': 'Only dicts can be placed to create/modify an entry'
}

INVALID_CONTENT_CREATE_ENTRY = {
    'status': 409,
    'type': 'Validation Error',
    'message': 'Only lists of dicts can be placed to create entries'
}

AUTOMATIC_PK = {
    'status': 409,
    'type': 'Validation Error',
    'message': 'The field \'%s\' is asigned automatically' % controller.IDENTIFIER
}


class TestDataStoreController(object):
    '''Tests for the module.'''

    def __init__(self):
        self.restController = controller.RestfulDatastoreController()

    def setup(self):

        # Save some functions that will be mocked to unmock them later
        self._get_content_type = utils.get_content_type
        self._xml_parser = utils.response_parser.xml_parser
        self._csv_parser = utils.response_parser.csv_parser
        self._json_dumps = utils.helpers.json.dumps
        self._json_loads = utils.helpers.json.loads
        self._finish = utils.finish
        self._parse_response = utils.parse_response

        # Create mocks
        utils.finish = MagicMock(return_value='FINISH FUNCTION')
        utils.parse_response = MagicMock(return_value='PARSED CONTENT')
        utils.get_content_type = MagicMock()
        controller.response = MagicMock()
        controller.request = MagicMock()
        controller.plugins.toolkit.c = MagicMock()
        utils.response = controller.response
        utils.request = controller.request
        utils.plugins.toolkit.c = controller.plugins.toolkit.c
        utils.response_parser.xml_parser = MagicMock(return_value=XML['response'])
        utils.response_parser.csv_parser = MagicMock(return_value=CSV['response'])
        utils.helpers.json.dumps = MagicMock(return_value=JSON['response'])

    def teardown(self):
        # Restore the mocks
        utils.get_content_type = self._get_content_type
        utils.response_parser.xml_parser = self._xml_parser
        utils.response_parser.csv_parser = self._csv_parser
        utils.helpers.json.dumps = self._json_dumps
        utils.helpers.json.loads = self._json_loads
        utils.finish = self._finish
        utils.parse_response = self._parse_response

    def set_side_effect(self, logic_function, side_effect):
        logic_function.side_effect = side_effect['exception']

    def _generic_test(self, function, logic_functions_prop, content_type, resource_id=None, entry_id=None,
                      get_content=None, post_content=None, fields=None, expected_error=None):

        # Set the get_content_type function to return the type
        utils.get_content_type.return_value = content_type['type']

        # Set the content that will be read from the request
        controller.request.headers = {'host': 'localhost'}                                  # This object will be readed to decide the return content-type
        if post_content is not None:
            controller.request.body = json.dumps(post_content)                              # HTTP receives the content as JSON
        if get_content is not None:
            get_params = copy.deepcopy(get_content)
            controller.request.GET.mixed = Mock(return_value=get_params)                    # Set GET content
        controller.response.headers = {}                                                    # This object will be used by _finish function

        logic_functions = {}
        side_effect = None

        # Build the logic functions that will be returned by the get_action function
        # Additional information is set to check that logic functions are called properly
        for function_prop in logic_functions_prop:
            return_value = function_prop['return_value'] if 'return_value' in function_prop else copy.deepcopy(DEFAULT_LOGIC_FUNCTION_RES)

            # Include '_id' field, that is usually returned by CKAN
            if 'records' in return_value:
                _id = 0
                for record in return_value['records']:
                    _id += 1
                    record['_id'] = _id

            # Include '_id' in the fields field
            if 'fields' in return_value and isinstance(return_value['fields'], list):
                return_value['fields'].append({'id': '_id', 'type': 'int4'})

            logic_function = Mock(return_value=return_value)

            if 'side_effect' in function_prop and function_prop['side_effect'] is not None:
                self.set_side_effect(logic_function, function_prop['side_effect'])
                if not side_effect:
                    side_effect = function_prop['side_effect']

            logic_functions[function_prop['name']] = {}
            logic_functions[function_prop['name']]['function'] = logic_function
            logic_functions[function_prop['name']]['expected_call'] = function_prop['expected_call']

        def return_logic_function(*args, **kwargs):
            return logic_functions[args[0]]['function']

        controller.plugins.toolkit.get_action = Mock(side_effect=return_logic_function)

        # Define context to return
        expected_context = {}
        expected_context['model'] = MagicMock()
        expected_context['session'] = MagicMock()
        expected_context['user'] = MagicMock()

        controller.plugins.toolkit.c.user = expected_context['user']
        controller.model = expected_context['model']
        controller.model.Session = expected_context['session']

        # Call the function
        if entry_id and resource_id:
            response = function(resource_id, entry_id)
        elif resource_id:
            response = function(resource_id)
        else:
            response = function()

        if not expected_error:

            # Check that get_action has been called correctly
            assert_equal(len(logic_functions_prop), controller.plugins.toolkit.get_action.call_count)
            for function_prop, actual_call in zip(logic_functions_prop, controller.plugins.toolkit.get_action.call_args_list):
                assert_equal(function_prop['name'], actual_call[0][0])

            # Check that logic_function hass been called correctly
            for name in logic_functions:
                logic_function = logic_functions[name]['function']
                logic_function.assert_called_once_with(expected_context, logic_functions[name]['expected_call'])

        if not side_effect and not expected_error:
            # Check that the proper parser has been called

            if fields:  # Fields are included in all the request except for 'DEL' requests
                expected_object_to_parse = copy.deepcopy(return_value)
                field_name = fields if not entry_id else fields[:-1]

                # URLs are included in XMLs
                if fields == 'records' and 'resource_id' in expected_object_to_parse:
                    for k in expected_object_to_parse['records']:
                        if controller.IDENTIFIER in k:
                            k['__url'] = 'http://localhost/resource/%s/entry/%s' % (expected_object_to_parse['resource_id'], k[controller.IDENTIFIER])

                utils.parse_response.assert_called_once(expected_object_to_parse, content_type, field_name, entry_id)
            else:
                assert_equal(0, utils.parse_response.call_count)    # On delete, parse function mustn't be called

            expected_status = 200
            expected_response = utils.parse_response.return_value if fields else ''
            expected_content_type = content_type['type']
        else:
            utils.parse_response.assert_called_once(content_type=utils.JSON)
            error = utils.parse_response.call_args_list[0][0][0]

            assert 'error' in error
            assert '__type' in error['error']
            assert 'message' in error['error']

            if expected_error:
                exception_text = expected_error['message']
                exception_type = expected_error['type']
            else:
                exception_type = side_effect['type']
                if side_effect == VALIDATION_ERROR:
                    exception_text = side_effect['exception'].error_dict['message']
                elif side_effect == DATA_ERROR:
                    exception_text = side_effect['exception'].error
                elif side_effect == SEARCH_QUERY_ERROR:
                    exception_text = 'Search Query is invalid: %r' % str(side_effect['exception'])
                elif side_effect == SEARCH_ERROR:
                    exception_text = 'Search error: %r' % str(side_effect['exception'])
                elif side_effect == SEARCH_INDEX_ERROR:
                    exception_text = 'Unable to add package to search index: %s' % str(side_effect['exception'])
                else:
                    exception_text = str(side_effect['exception'])

            if isinstance(exception_text, dict) and 'message' in exception_text:
                exception_text = exception_text['message']

            assert_equal(exception_type, error['error']['__type'])
            assert_not_equal(re.match('^' + exception_text + '$', error['error']['message']), None)

            expected_status = expected_error['status'] if expected_error else side_effect['status']
            expected_response = utils.parse_response.return_value
            expected_content_type = JSON['type']

        utils.finish.assert_called_once_with(expected_status, expected_response, expected_content_type)
        assert_equal(utils.finish.return_value, response)

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', DEFAULT_FIELDS, JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', DEFAULT_FIELDS, XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', DEFAULT_FIELDS, CSV),
        # # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', DEFAULT_FIELDS, JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', DEFAULT_FIELDS, XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', DEFAULT_FIELDS, CSV, VALUE_ERROR,),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', DEFAULT_FIELDS, JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', DEFAULT_FIELDS, XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', DEFAULT_FIELDS, CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', DEFAULT_FIELDS, JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', DEFAULT_FIELDS, XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', DEFAULT_FIELDS, CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', DEFAULT_FIELDS, JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', DEFAULT_FIELDS, XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', DEFAULT_FIELDS, CSV, NOT_FOUND),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', DEFAULT_FIELDS, JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', DEFAULT_FIELDS, XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', DEFAULT_FIELDS, CSV, VALIDATION_ERROR),
        ('6cdbf349-2dff-4003-b0c5-76b63809d329', {}, JSON, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('70f809b1-0503-4e79-9c74-d87767bd9d60', {}, XML, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('3ecfef11-ffb7-41bb-99aa-88cd76d0cb95', {}, CSV, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('0101c6c7-ec62-40d4-80f0-ad26895879e3', 'test1', JSON, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('c82f424b-2dbe-4a7a-b386-0ac08c3f25eb', 'test1', XML, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('f5e46a31-e9e9-40a8-b655-6368b5a04e1c', 'test1', CSV, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('35db5c43-22f0-449e-8be3-477ddbf4f30a', 1, JSON, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('770db970-ad4a-413e-9f2d-f98208da473d', 1, XML, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('19b55ee8-45f9-4b8f-8a5d-07d7f83d1e47', 1, CSV, None, INVALID_CONTENT_CREATE_RESOURCE),
        # When an invalid field is included (missing _id), fields will be relayed to CKAN and it will be
        # its responsability to return the proper error
        ('5829f160-e00c-11e3-8b68-0800200c9a66', INVALID_FIELDS, JSON),
        ('e9c48879-7520-44dc-9264-b1b51558670c', INVALID_FIELDS, XML),
        ('b6da5c9c-6dbf-46f8-b8a6-859116c59ae4', INVALID_FIELDS, CSV),
        # Lists of strings or other object different from dicts are invalid
        ('40586a73-e2ce-4c64-8900-cf328526fa1d', ["test", 1], JSON, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('837bcede-e29d-4315-9624-517d6f5ae741', [2, "test"], XML, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('57d876f0-30b4-4acd-ab4f-3e6447683201', [3, "test"], CSV, None, INVALID_CONTENT_CREATE_RESOURCE),
        ('72e1deb4-983c-46ee-a7eb-7af8fe92a61c', FIELDS_PK, JSON, None, PK_CANNOT_BE_INCLUDED),
        ('022daa2e-8dcb-4d55-a37e-065ea699d4d5', FIELDS_PK, XML, None, PK_CANNOT_BE_INCLUDED),
        ('79118e69-49d3-456b-a451-9ecd20f1deb5', FIELDS_PK, CSV, None, PK_CANNOT_BE_INCLUDED)

    ])
    def test_upsert_resource(self, resource_id, fields, content_type, side_effect=None, expected_error=None):

        # Generate the expected_call
        expected_call = {
            'force': True,
            'resource_id': resource_id
        }

        if isinstance(fields, list):
            expected_call['fields'] = list(fields)
            expected_call['fields'].insert(0, {'id': controller.IDENTIFIER, 'type': 'int'})
            expected_call['primary_key'] = [controller.IDENTIFIER]
        else:
            expected_call['fields'] = fields

        logic_functions_prop = []

        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_create'
        logic_functions_prop[0]['side_effect'] = side_effect
        logic_functions_prop[0]['expected_call'] = expected_call

        self._generic_test(self.restController.upsert_resource, logic_functions_prop, content_type, resource_id,
                           post_content=fields, fields='fields', expected_error=expected_error)

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', CSV),
        # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', CSV, VALUE_ERROR),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', CSV, NOT_FOUND),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', CSV, VALIDATION_ERROR)
    ])
    def test_get_resource_structure(self, resource_id, content_type, side_effect=None):

        expected_call = {
            'resource_id': resource_id
        }

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_search'
        logic_functions_prop[0]['side_effect'] = side_effect
        logic_functions_prop[0]['expected_call'] = expected_call

        self._generic_test(self.restController.structure, logic_functions_prop, content_type,
                           resource_id, fields='fields')

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', {}, JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', {}, XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', {}, CSV),
        # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', {}, JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', {}, XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', {}, CSV, VALUE_ERROR),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', {}, JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', {}, XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', {}, CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', {}, JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', {}, XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', {}, CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', {}, JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', {}, XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', {}, CSV, NOT_FOUND),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', {}, JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', {}, XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', {}, CSV, VALIDATION_ERROR),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', {'filters': {'test': 'a', 'test1': 'b'}}, JSON),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', {'filters': {'test': 'a', 'test1': 'b'}}, XML),
        ('2450063c-3085-415e-aab5-516d534e0c85', {'filters': {'test': 'a', 'test1': 'b'}}, CSV),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', {'test': 'test'}, JSON),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', {'test': 'test'}, XML),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', {'test': 'test'}, CSV)
    ])
    def test_delete_resource(self, resource_id, get_parameters, content_type, side_effect=None):

        # Filters cannot be included in the petition. Otherwise, only the elements that match the filters
        # will be deleted instead of deleting the full resource

        expected_call = {}
        expected_call['resource_id'] = resource_id
        expected_call['force'] = True

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_delete'
        logic_functions_prop[0]['side_effect'] = side_effect
        logic_functions_prop[0]['expected_call'] = expected_call

        self._generic_test(self.restController.delete_resource, logic_functions_prop, content_type,
                           resource_id, get_content=get_parameters)

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', DEFAULT_SEARCH, JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', DEFAULT_SEARCH, XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', DEFAULT_SEARCH, CSV),
        # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', DEFAULT_SEARCH, JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', DEFAULT_SEARCH, XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', DEFAULT_SEARCH, CSV, VALUE_ERROR),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', DEFAULT_SEARCH, JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', DEFAULT_SEARCH, XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', DEFAULT_SEARCH, CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', DEFAULT_SEARCH, JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', DEFAULT_SEARCH, XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', DEFAULT_SEARCH, CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', DEFAULT_SEARCH, JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', DEFAULT_SEARCH, XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', DEFAULT_SEARCH, CSV, NOT_FOUND),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', DEFAULT_SEARCH, JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', DEFAULT_SEARCH, XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', DEFAULT_SEARCH, CSV, VALIDATION_ERROR),
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', MALIGN_SEARCH, JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', MALIGN_SEARCH, XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', MALIGN_SEARCH, CSV)
    ])
    def test_search_resource(self, resource_id, get_parameters, content_type, side_effect=None):

        expected_call = {}
        expected_call['resource_id'] = resource_id
        expected_call['filters'] = {}

        # Transform the get_parameters
        TRANSFORMED_PARAMETERS = ['$q', '$plain', '$language', '$limit', '$offset', '$fields', '$sort']

        for parameter in get_parameters:
            if parameter in TRANSFORMED_PARAMETERS:
                # 1: will remove the dollar symbol
                expected_call[parameter[1:]] = get_parameters[parameter]
            elif parameter != 'filters':
                expected_call['filters'][parameter] = get_parameters[parameter]

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_search'
        logic_functions_prop[0]['side_effect'] = side_effect
        logic_functions_prop[0]['expected_call'] = expected_call

        self._generic_test(self.restController.search_entries, logic_functions_prop, content_type, resource_id,
                           get_content=get_parameters, fields='records')

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', 1, JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', 2, XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', 3, CSV),
        # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', 1, JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', 2, XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', 3, CSV, VALUE_ERROR),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', 1, JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', 2, XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', 3, CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', 1, JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', 2, XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', 3, CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', 1, JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', 2, XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', 3, CSV, NOT_FOUND),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', 1, JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', 2, XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', 3, CSV, VALIDATION_ERROR),
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', 1, JSON, None, NOT_FOUND_ENTRY, []),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', 2, XML, None, NOT_FOUND_ENTRY, []),
        ('7b98539d-57f8-466d-9810-91cff04848ff', 3, CSV, None, NOT_FOUND_ENTRY, [])
    ])
    def test_get_entry(self, resource_id, entry_id, content_type, side_effect=None, expected_error=None, returned_records=None):

        expected_call = {}
        expected_call['resource_id'] = resource_id
        expected_call['filters'] = {}
        expected_call['filters'][controller.IDENTIFIER] = entry_id

        return_value = copy.deepcopy(DEFAULT_LOGIC_FUNCTION_RES)
        return_value['records'] = returned_records if returned_records is not None else [return_value['records'][0]]

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_search'
        logic_functions_prop[0]['side_effect'] = side_effect
        logic_functions_prop[0]['expected_call'] = expected_call
        logic_functions_prop[0]['return_value'] = return_value

        self._generic_test(self.restController.get_entry, logic_functions_prop, content_type, resource_id,
                           entry_id, fields='records', expected_error=expected_error)

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', 1, DEFAULT_RECORDS[0], JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', 2, DEFAULT_RECORDS[0], XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', 3, DEFAULT_RECORDS[0], CSV),
        # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', 1, DEFAULT_RECORDS[0], JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', 2, DEFAULT_RECORDS[0], XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', 3, DEFAULT_RECORDS[0], CSV, VALUE_ERROR),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', 1, DEFAULT_RECORDS[0], JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', 2, DEFAULT_RECORDS[0], XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', 3, DEFAULT_RECORDS[0], CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', 1, DEFAULT_RECORDS[0], JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', 2, DEFAULT_RECORDS[0], XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', 3, DEFAULT_RECORDS[0], CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', 1, DEFAULT_RECORDS[0], JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', 2, DEFAULT_RECORDS[0], XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', 3, DEFAULT_RECORDS[0], CSV, NOT_FOUND),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', 1, DEFAULT_RECORDS[0], JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', 2, DEFAULT_RECORDS[0], XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', 3, DEFAULT_RECORDS[0], CSV, VALIDATION_ERROR),
        # DEFAULT_RECORDS[1] includes 'pk'. If the pk included in the object match with the pk from the URL,
        # the operation must continue, otherwise, the operartion will fail.
        ('737d6f99-4a8a-42c2-8205-6907be05f103', 1, DEFAULT_RECORDS[1], JSON),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', 1, DEFAULT_RECORDS[1], XML),
        ('2450063c-3085-415e-aab5-516d534e0c85', 1, DEFAULT_RECORDS[1], CSV),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', 2, DEFAULT_RECORDS[1], JSON, None, ENTRY_PK_MISMATCH),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', 2, DEFAULT_RECORDS[1], XML, None, ENTRY_PK_MISMATCH),
        ('2450063c-3085-415e-aab5-516d534e0c85', 2, DEFAULT_RECORDS[1], CSV, None, ENTRY_PK_MISMATCH),
        # Operation mustn't accept other things different from an object (for example a list)
        ('737d6f99-4a8a-42c2-8205-6907be05f103', 3, DEFAULT_RECORDS, JSON, None, INVALID_CONTENT_UPSERT_ENTRY),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', 3, DEFAULT_RECORDS, XML, None, INVALID_CONTENT_UPSERT_ENTRY),
        ('2450063c-3085-415e-aab5-516d534e0c85', 3, DEFAULT_RECORDS, CSV, None, INVALID_CONTENT_UPSERT_ENTRY)
    ])
    def test_upsert_entry(self, resource_id, entry_id, record, content_type, side_effect=None, expected_error=None):

        records = [copy.deepcopy(record)] if isinstance(record, dict) else copy.deepcopy(record)

        expected_call = {}
        expected_call['resource_id'] = resource_id
        expected_call['records'] = records
        expected_call['records'][0][controller.IDENTIFIER] = entry_id
        expected_call['force'] = True
        expected_call['method'] = 'upsert'

        return_value = copy.deepcopy(DEFAULT_LOGIC_FUNCTION_RES)
        return_value['records'] = [return_value['records'][0]]

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_upsert'
        logic_functions_prop[0]['side_effect'] = side_effect
        logic_functions_prop[0]['expected_call'] = expected_call
        logic_functions_prop[0]['return_value'] = return_value

        self._generic_test(self.restController.upsert_entry, logic_functions_prop, content_type, resource_id,
                           entry_id, post_content=record, fields='records', expected_error=expected_error)

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', DEFAULT_RECORDS, JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', DEFAULT_RECORDS, XML),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', DEFAULT_RECORDS, XML, None, None, True),
        ('7b98539d-57f8-466d-9810-91cff04848ff', DEFAULT_RECORDS, CSV),
        # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', DEFAULT_RECORDS, JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', DEFAULT_RECORDS, XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', DEFAULT_RECORDS, CSV, VALUE_ERROR),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', DEFAULT_RECORDS, JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', DEFAULT_RECORDS, XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', DEFAULT_RECORDS, CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', DEFAULT_RECORDS, JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', DEFAULT_RECORDS, XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', DEFAULT_RECORDS, CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', DEFAULT_RECORDS, JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', DEFAULT_RECORDS, XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', DEFAULT_RECORDS, CSV, NOT_FOUND),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', DEFAULT_RECORDS, JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', DEFAULT_RECORDS, XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', DEFAULT_RECORDS, CSV, VALIDATION_ERROR),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', DEFAULT_RECORDS, JSON, None, AUTOMATIC_PK, False),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', DEFAULT_RECORDS, XML, None, AUTOMATIC_PK, False),
        ('2450063c-3085-415e-aab5-516d534e0c85', DEFAULT_RECORDS, CSV, None, AUTOMATIC_PK, False),
        # Dicts are not allowed to create entries
        ('737d6f99-4a8a-42c2-8205-6907be05f103', DEFAULT_RECORDS[0], JSON, None, INVALID_CONTENT_CREATE_ENTRY),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', DEFAULT_RECORDS[0], XML, None, INVALID_CONTENT_CREATE_ENTRY),
        ('2450063c-3085-415e-aab5-516d534e0c85', DEFAULT_RECORDS[0], CSV, None, INVALID_CONTENT_CREATE_ENTRY),
        # Numbers are not allowed to create entries
        ('737d6f99-4a8a-42c2-8205-6907be05f103', 0, JSON, None, INVALID_CONTENT_CREATE_ENTRY),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', 0, XML, None, INVALID_CONTENT_CREATE_ENTRY),
        ('2450063c-3085-415e-aab5-516d534e0c85', 0, CSV, None, INVALID_CONTENT_CREATE_ENTRY),
        # List of objects different to dicts are not allowed to create entries
        ('737d6f99-4a8a-42c2-8205-6907be05f103', ["test", 3, "test2"], JSON, None, INVALID_CONTENT_CREATE_ENTRY),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', [8, "test", "test2"], XML, None, INVALID_CONTENT_CREATE_ENTRY),
        ('2450063c-3085-415e-aab5-516d534e0c85', ["test", 1, 3], CSV, None, INVALID_CONTENT_CREATE_ENTRY)
    ])
    def test_create_entries(self, resource_id, records, content_type, side_effect=None, expected_error=None, remove_pk=True, max_pk_exists=True, jsonp=False):

        max_pk = 8 if max_pk_exists else None

        expected_call_max = {}
        expected_call_max['sql'] = 'SELECT MAX(pk) AS max FROM \"%s\";' % resource_id

        records = copy.deepcopy(records)

        # Remove 'pk' from the records that will be used to call the function
        if remove_pk and isinstance(records, list):
            for record in records:
                if isinstance(record, dict):
                    if controller.IDENTIFIER in record:
                        del record[controller.IDENTIFIER]

        # The records included in the upsert method should include a 'pk' field
        # set automatically by the API
        expected_records = copy.deepcopy(records)
        if isinstance(records, list):
            pk = max_pk if max_pk else 0
            for record in expected_records:
                if isinstance(record, dict):
                    pk += 1
                    record[controller.IDENTIFIER] = pk

        expected_call_upsert = {}
        expected_call_upsert['resource_id'] = resource_id
        expected_call_upsert['records'] = expected_records
        expected_call_upsert['force'] = True
        expected_call_upsert['method'] = 'upsert'

        return_value_max = {}
        return_value_max['records'] = []
        return_value_max['records'].append({'max': max_pk})

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_search_sql'
        logic_functions_prop[0]['side_effect'] = None
        logic_functions_prop[0]['expected_call'] = expected_call_max
        logic_functions_prop[0]['return_value'] = return_value_max

        logic_functions_prop.append({})     # 1
        logic_functions_prop[1]['name'] = 'datastore_upsert'
        logic_functions_prop[1]['side_effect'] = side_effect
        logic_functions_prop[1]['expected_call'] = expected_call_upsert

        self._generic_test(self.restController.create_entries, logic_functions_prop, content_type, resource_id,
                           post_content=records, fields='records', expected_error=expected_error)

    @parameterized.expand([
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', 1, JSON),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', 2, XML),
        ('7b98539d-57f8-466d-9810-91cff04848ff', 3, CSV),
        # Test side_effects returned by the logic function
        ('8fa623dc-1368-4756-a741-15bba0b16fc9', 1, JSON, VALUE_ERROR),
        ('cad79527-a74f-49b9-93af-53cddad4f043', 2, XML, VALUE_ERROR),
        ('5f86ad82-ebf5-4352-bb57-da647b3c14ea', 3, CSV, VALUE_ERROR),
        ('a3bfd43b-6fa6-4baf-963b-67d5d796299b', 1, JSON, DATA_ERROR),
        ('1ba7d819-1d0e-43b1-93de-45afe000695d', 2, XML, DATA_ERROR),
        ('7c301e62-f302-4475-abe9-9411e3638118', 3, CSV, DATA_ERROR),
        ('a04bf1c0-7b25-4e18-82a2-545741dacdf4', 1, JSON, NOT_AUTHORIZED),
        ('586330ce-b4f7-4160-b0d3-7c19dd59cd14', 2, XML, NOT_AUTHORIZED),
        ('90744193-ba50-4388-b6a8-e1eda0133808', 3, CSV, NOT_AUTHORIZED),
        ('7445f342-c1fa-407c-8482-a03ca972d621', 1, JSON, NOT_FOUND),
        ('b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', 2, XML, NOT_FOUND),
        ('0f390067-ee5e-43ba-b314-2bfdb18aa90e', 3, CSV, NOT_FOUND,),
        ('737d6f99-4a8a-42c2-8205-6907be05f103', 1, JSON, VALIDATION_ERROR),
        ('3137df0f-4304-4166-a7a6-f0aa9b9ef13e', 2, XML, VALIDATION_ERROR),
        ('2450063c-3085-415e-aab5-516d534e0c85', 3, CSV, VALIDATION_ERROR),
        ('71bba7b5-6882-4099-88b3-4ca9a7468b38', 1, JSON, None, NOT_FOUND_ENTRY, []),
        ('ddddbeab-d0e0-417a-9582-c7b02dd858da', 2, XML, None, NOT_FOUND_ENTRY, []),
        ('7b98539d-57f8-466d-9810-91cff04848ff', 3, CSV, None, NOT_FOUND_ENTRY, []),
    ])
    def test_delete_entry(self, resource_id, entry_id, content_type, side_effect=None, expected_error=None, returned_records=None):

        expected_call_search = {}
        expected_call_search = {}
        expected_call_search['filters'] = {controller.IDENTIFIER: entry_id}
        expected_call_search['resource_id'] = resource_id

        expected_call_del = {}
        expected_call_del['resource_id'] = resource_id
        expected_call_del['filters'] = {}
        expected_call_del['filters'][controller.IDENTIFIER] = entry_id
        expected_call_del['force'] = True

        return_value_search = copy.deepcopy(DEFAULT_LOGIC_FUNCTION_RES)
        return_value_search['records'] = returned_records if returned_records is not None else [return_value_search['records'][0]]

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_search'
        logic_functions_prop[0]['side_effect'] = None
        logic_functions_prop[0]['expected_call'] = expected_call_search
        logic_functions_prop[0]['return_value'] = return_value_search

        logic_functions_prop.append({})     # 1
        logic_functions_prop[1]['name'] = 'datastore_delete'
        logic_functions_prop[1]['side_effect'] = side_effect
        logic_functions_prop[1]['expected_call'] = expected_call_del

        self._generic_test(self.restController.delete_entry, logic_functions_prop, content_type,
                           resource_id, entry_id, expected_error=expected_error)

    @parameterized.expand([
        ('select * from 71bba7b5-6882-4099-88b3-4ca9a7468b38', JSON),
        ('select * from ddddbeab-d0e0-417a-9582-c7b02dd858da', XML),
        ('select * from 7b98539d-57f8-466d-9810-91cff04848ff', CSV),
        # Test side_effects returned by the logic function
        ('select * from 8fa623dc-1368-4756-a741-15bba0b16fc9', JSON, VALUE_ERROR),
        ('select * from cad79527-a74f-49b9-93af-53cddad4f043', XML, VALUE_ERROR),
        ('select * from 5f86ad82-ebf5-4352-bb57-da647b3c14ea', CSV, VALUE_ERROR),
        ('select * from a3bfd43b-6fa6-4baf-963b-67d5d796299b', JSON, DATA_ERROR),
        ('select * from 1ba7d819-1d0e-43b1-93de-45afe000695d', XML, DATA_ERROR),
        ('select * from 7c301e62-f302-4475-abe9-9411e3638118', CSV, DATA_ERROR),
        ('select * from a04bf1c0-7b25-4e18-82a2-545741dacdf4', JSON, NOT_AUTHORIZED),
        ('select * from 586330ce-b4f7-4160-b0d3-7c19dd59cd14', XML, NOT_AUTHORIZED),
        ('select * from 90744193-ba50-4388-b6a8-e1eda0133808', CSV, NOT_AUTHORIZED),
        ('select * from 7445f342-c1fa-407c-8482-a03ca972d621', JSON, NOT_FOUND),
        ('select * from b8b05f9c-fbb3-480a-bdce-4edd0bab1c51', XML, NOT_FOUND),
        ('select * from 0f390067-ee5e-43ba-b314-2bfdb18aa90e', CSV, NOT_FOUND),
        ('select * from 737d6f99-4a8a-42c2-8205-6907be05f103', JSON, VALIDATION_ERROR),
        ('select * from 3137df0f-4304-4166-a7a6-f0aa9b9ef13e', XML, VALIDATION_ERROR),
        ('select * from 2450063c-3085-415e-aab5-516d534e0c85', CSV, VALIDATION_ERROR),
        ('select * from 6cdbf349-2dff-4003-b0c5-76b63809d329', JSON, SEARCH_QUERY_ERROR),
        ('select * from 70f809b1-0503-4e79-9c74-d87767bd9d60', XML, SEARCH_QUERY_ERROR),
        ('select * from 3ecfef11-ffb7-41bb-99aa-88cd76d0cb95', CSV, SEARCH_QUERY_ERROR),
        ('select * from ca05c71e-c34c-45d5-aa6c-19909aa66440', JSON, SEARCH_ERROR),
        ('select * from e5d0c26d-9fa0-41af-8edb-ab61fbdf3dfd', XML, SEARCH_ERROR),
        ('select * from dc141753-7d33-4d3f-935f-b3f88bfedc81', CSV, SEARCH_ERROR),
        ('select * from 0101c6c7-ec62-40d4-80f0-ad26895879e3', JSON, SEARCH_INDEX_ERROR),
        ('select * from c82f424b-2dbe-4a7a-b386-0ac08c3f25eb', XML, SEARCH_INDEX_ERROR),
        ('select * from f5e46a31-e9e9-40a8-b655-6368b5a04e1c', CSV, SEARCH_INDEX_ERROR)
    ])
    def test_sql(self, sql, content_type, side_effect=None):

        get_parameters = {}
        get_parameters['sql'] = sql

        expected_call = copy.deepcopy(get_parameters)

        logic_functions_prop = []
        logic_functions_prop.append({})     # 0
        logic_functions_prop[0]['name'] = 'datastore_search_sql'
        logic_functions_prop[0]['side_effect'] = side_effect
        logic_functions_prop[0]['expected_call'] = expected_call

        self._generic_test(self.restController.sql, logic_functions_prop, content_type,
                           get_content=get_parameters, fields='records')
