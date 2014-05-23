import copy
import ckanext.datastore_restful.utils as utils

from mock import ANY, MagicMock
from nose_parameterized import parameterized
from nose.tools import assert_equal


JSON = 'application/json'
XML = 'application/xml'
CSV = 'text/csv'
ALL = '*/*'
JSON_XML = 'application/json,application/xml'
XML_JSON = 'application/xml,application/json'
JSON08_XML = 'application/json;q=0.8,application/xml'
XML_JSON08 = 'application/xml,application/json;q=0.8'
JSON08_XML07 = 'application/json;q=0.8,application/xml;q=0.7'
XML07_JSON08 = 'application/xml;q=0.7,application/json;q=0.8'
XML07_ALL = 'application/xml;q=0.7,*/*'
ALL_XML07 = '*/*,application/xml;q=0.7'
XML07_ALL06 = 'application/xml;q=0.7,*/*;q=0.6'
ALL06_XML07 = '*/*;q=0.6,application/xml;q=0.7'
JSON08_XML07_CSV_ACCEPTED = 'application/json;q=0.8,application/xml;q=0.7,text/csv'

CONTENT_TYPES = {
    utils.JSON: 'application/json',
    utils.XML: 'application/xml',
    utils.CSV: 'text/csv',
    utils.TEXT: 'text/plain'
}

EXAMPLE_CONTENT = {
    'fields': [{'id': 'test', 'type': 'int'}, {'id': 'test1', 'type': 'text'}],
    'records': [{'test': 'test', 'test1': 'test1'}, {'test': '_test', 'test1': '_test1'}],
    'resource_id': 'test'
}


class TestUtils(object):
    '''Tests for the module.'''

    def __init__(self):
        self.mocks = {}

    def setup(self):

        # Save some functions that will be mocked
        self._xml_parser = utils.response_parser.xml_parser
        self._csv_parser = utils.response_parser.csv_parser
        self._json_dumps = utils.helpers.json.dumps
        self._json_loads = utils.helpers.json.loads
 
        # Create mocks
        utils.response = MagicMock()
        utils.response.headers = {}     # Will be used by the finish function
        utils.request = MagicMock()
        utils.request.GET.mixed = MagicMock(return_value={'test': 'test', 'test2': 'test2', utils.CALLBACK_PARAMETER: 'callback_function'})
        utils.plugins.toolkit.c = MagicMock()
        utils.response_parser.xml_parser = MagicMock(return_value='EXAMPLE XML')
        utils.response_parser.csv_parser = MagicMock(return_value='EXAMPLE CSV')
        utils.helpers.json.dumps = MagicMock(return_value='EXAMPLE JSON')
        utils.helpers.json.loads = MagicMock(return_value={'example': 1, 'example3': 'test example'})

    def teardown(self):

        # Restore the mocks
        utils.response_parser.xml_parser = self._xml_parser
        utils.response_parser.csv_parser = self._csv_parser
        utils.helpers.json.dumps = self._json_dumps
        utils.helpers.json.loads = self._json_loads

    @parameterized.expand([
        # Specified format is acepted
        ([utils.JSON], JSON, utils.JSON),
        ([utils.JSON, utils.XML], XML, utils.XML),
        ([utils.JSON, utils.XML, utils.CSV], JSON, utils.JSON),
        # Allow all formats (the first accept_header has priority)
        ([utils.JSON, utils.XML], ALL, utils.JSON),
        ([utils.XML, utils.JSON], ALL, utils.XML),
        # Specified format not acepted
        ([utils.JSON], CSV, None, True),
        ([utils.JSON, utils.CSV], XML, None, True),
        # Two accepts. The first has prirority
        ([utils.JSON, utils.XML], JSON_XML, utils.JSON),
        ([utils.XML, utils.JSON], JSON_XML, utils.JSON),
        ([utils.XML], JSON_XML, utils.XML),
        ([utils.JSON, utils.XML], XML_JSON, utils.XML),
        ([utils.XML, utils.JSON], XML_JSON, utils.XML),
        ([utils.JSON], XML_JSON, utils.JSON),
        # Two accepts, but none of them is accepted
        ([utils.CSV], JSON_XML, None, True),
        ([utils.TEXT], JSON_XML, None, True),
        # Priorities (one priority is not specified and should be considered as 1)
        ([utils.JSON, utils.XML], JSON08_XML, utils.XML),
        ([utils.XML, utils.JSON], JSON08_XML, utils.XML),
        ([utils.JSON], JSON08_XML, utils.JSON),
        ([utils.XML], JSON08_XML, utils.XML),
        ([utils.JSON, utils.XML], XML_JSON08, utils.XML),
        ([utils.XML, utils.JSON], XML_JSON08, utils.XML),
        ([utils.JSON], XML_JSON08, utils.JSON),
        ([utils.XML], XML_JSON08, utils.XML),
        # Priorities (both priorities are included)
        ([utils.JSON, utils.XML], JSON08_XML07, utils.JSON),
        ([utils.XML, utils.JSON], JSON08_XML07, utils.JSON),
        ([utils.JSON], JSON08_XML07, utils.JSON),
        ([utils.XML], JSON08_XML07, utils.XML),
        ([utils.JSON, utils.XML], XML07_JSON08, utils.JSON),
        ([utils.XML, utils.JSON], XML07_JSON08, utils.JSON),
        ([utils.JSON], XML07_JSON08, utils.JSON),
        ([utils.XML], XML_JSON08, utils.XML),
        # When */* is included (without priority), the
        # fitst accept should be returnd as content_type
        ([utils.JSON, utils.XML], XML07_ALL, utils.JSON),
        ([utils.XML, utils.JSON], XML07_ALL, utils.XML),
        ([utils.JSON], XML07_ALL, utils.JSON),
        ([utils.XML], XML07_ALL, utils.XML),
        ([utils.JSON, utils.XML], ALL_XML07, utils.JSON),
        ([utils.XML, utils.JSON], ALL_XML07, utils.XML),
        ([utils.JSON], ALL_XML07, utils.JSON),
        ([utils.XML], ALL_XML07, utils.XML),
        # When all is included (with priority), the
        # frist accept priority should abe evaluated too
        ([utils.JSON, utils.XML], XML07_ALL06, utils.XML),
        ([utils.XML, utils.JSON], XML07_ALL06, utils.XML),
        ([utils.JSON], XML07_ALL06, utils.JSON),
        ([utils.XML], XML07_ALL06, utils.XML),
        ([utils.JSON, utils.XML], ALL06_XML07, utils.XML),
        ([utils.XML, utils.JSON], ALL06_XML07, utils.XML),
        ([utils.JSON], ALL06_XML07, utils.JSON),
        ([utils.XML], ALL06_XML07, utils.XML),
        # Three accepts
        ([utils.JSON], JSON08_XML07_CSV_ACCEPTED, utils.JSON),
        ([utils.XML], JSON08_XML07_CSV_ACCEPTED, utils.XML),
        ([utils.CSV], JSON08_XML07_CSV_ACCEPTED, utils.CSV),
        ([utils.JSON, utils.XML], JSON08_XML07_CSV_ACCEPTED, utils.JSON),
        ([utils.CSV, utils.XML], JSON08_XML07_CSV_ACCEPTED, utils.CSV),
        ([utils.JSON, utils.CSV], JSON08_XML07_CSV_ACCEPTED, utils.CSV),
        ([utils.JSON, utils.XML, utils.CSV], JSON08_XML07_CSV_ACCEPTED, utils.CSV),
        # accepted_content_types is empty
        ([], JSON, None, True),
    ])
    def test_get_contet_type(self, accepted_content_types, content_type, expected_content_type, expected_exception=False):

        utils.request.headers = {'ACCEPT': content_type}

        try:
            returned_content_type = utils.get_content_type(accepted_content_types)
            assert expected_exception is False
            assert_equal(expected_content_type, returned_content_type)

        except utils.plugins.toolkit.ValidationError as e:
            assert expected_exception is True
            error = e.error_dict
            allowed_accepts = ', '.join(CONTENT_TYPES[k] for k in accepted_content_types)
            expected_msg = 'Only %s can be placed in the \'Accept\' header for this request' % allowed_accepts
            assert_equal(expected_msg, error['message'])
            assert_equal({'Accept': content_type}, error['data'])

    @parameterized.expand([
        # JSON
        (utils.JSON, 'records', None, EXAMPLE_CONTENT['records']),
        (utils.JSON, 'records', 1, EXAMPLE_CONTENT['records'][1]),
        (utils.JSON, None, None, EXAMPLE_CONTENT),
        # XML
        (utils.XML, 'records', None, EXAMPLE_CONTENT['records'], 'records'),
        (utils.XML, 'records', 1, EXAMPLE_CONTENT['records'][1], 'record'),
        (utils.XML, None, None, EXAMPLE_CONTENT, None),
        # CSV
        (utils.CSV, 'records', None, EXAMPLE_CONTENT),
        (utils.CSV, 'records', 1, EXAMPLE_CONTENT),
        (utils.CSV, None, None, EXAMPLE_CONTENT),
        # No Content
        (None, None, None, None)
    ])
    def test_parse_response(self, content_type, field, entry, call_element, field_name=None):

        response = utils.parse_response(EXAMPLE_CONTENT, content_type, field, entry)

        if content_type == utils.JSON:
            utils.helpers.json.dumps.assert_called_once_with(call_element)
            assert_equal(utils.helpers.json.dumps.return_value, response)
            # Check that the other parses has not been called
            assert_equal(0, utils.response_parser.xml_parser.called)
            assert_equal(0, utils.response_parser.csv_parser.called)
        elif content_type == utils.XML:
            utils.response_parser.xml_parser.assert_called_once_with(call_element, field_name)
            assert_equal(utils.response_parser.xml_parser.return_value, response)
            # Check that the other parses has not been called
            assert_equal(0, utils.helpers.json.dumps.called)
            assert_equal(0, utils.response_parser.csv_parser.called)
        elif content_type == utils.CSV:
            utils.response_parser.csv_parser.assert_called_once_with(EXAMPLE_CONTENT)
            assert_equal(utils.response_parser.csv_parser.return_value, response)
            # Check that the other parses has not been called
            assert_equal(0, utils.helpers.json.dumps.called)
            assert_equal(0, utils.response_parser.xml_parser.called)
        else:
            # Check that the parses haven't been called
            assert_equal(0, utils.helpers.json.dumps.called)
            assert_equal(0, utils.response_parser.xml_parser.called)
            assert_equal(0, utils.response_parser.csv_parser.called)

    def test_parse_get_parameters(self):
        # Get parameters
        result_parameters = utils.parse_get_parameters()

        # Assert that the GET.mixed() function has been called
        utils.request.GET.mixed.assert_called_once_with()

        # Check the parameters
        expected_parameters = copy.deepcopy(utils.request.GET.mixed.return_value)
        if utils.CALLBACK_PARAMETER in expected_parameters:
            del expected_parameters[utils.CALLBACK_PARAMETER]
        assert_equal(expected_parameters, result_parameters)

    @parameterized.expand([
        ('EXAMPLE CONTENT'),
        ('EXAMPLE CONTENT', True),
    ])
    def test_parse_body(self, content, throw_exception=False):

        # Set up the content
        utils.request.body = content

        if throw_exception:
            utils.helpers.json.loads.side_effect = ValueError

        # Assert that the content is parsed
        try:
            response = utils.parse_body()
            assert throw_exception is False
            assert_equal(utils.helpers.json.loads.return_value, response)
        except ValueError as e:
            assert throw_exception is True
            assert str(e).startswith('JSON Error: Error decoding JSON data. Error:')

        utils.helpers.json.loads.assert_called_once_with(content, encoding=ANY)

    @parameterized.expand([
        (200, 'EXAMPLE TEST'),
        (200, 'EXAMPLE TEST', utils.JSON),
        (404, 'EXAMPLE TEST'),
        (500, 'EXAMPLE TEST', utils.XML),
        # Error
        ('200', 'EXAMPLE_TEST'),
        # JSONP
        (200, 'EXAMPLE TEST', utils.JSON, True, True),
        (200, 'EXAMPLE TEST', utils.XML, True, False),              # JSONP cannot be returned when content_type != JSON
        (404, 'EXAMPLE TEST', utils.JSON, True, False),             # JSONP cannot be returned when status != 500
        (200, 'EXAMPLE TEST', utils.JSON, True, False, 'POST'),     # JSONP cannot be returned when method != GET

    ])
    def test_finish(self, status, content, content_type=None, jsonp=False, expected_jsonp=False, method='GET'):

        callback_function = 'example_function'

        if jsonp:
            utils.request.params = {}
            utils.request.params[utils.CALLBACK_PARAMETER] = callback_function
            utils.request.method = method

        # Get the response
        try:
            if content_type:
                response = utils.finish(status, content, content_type)
            else:
                response = utils.finish(status, content)
                content_type = utils.TEXT

            assert isinstance(status, int)

            # Check HTTP Status
            assert_equal(status, utils.response.status_int)
            # Check headers
            assert 'Content-Type' in utils.response.headers
            assert CONTENT_TYPES[content_type] in utils.response.headers['Content-Type']
            #Check response
            if expected_jsonp:
                assert_equal('%s(%s);' % (callback_function, content), response)
            else:
                assert_equal(content, response)

        except AssertionError:
            assert not isinstance(status, int)

    @parameterized.expand([
        ('EXAMPLE TEST'),
        ('EXAMPLE TEST', utils.JSON),
        ('EXAMPLE TEST'),
        ('EXAMPLE TEST', utils.XML),
        ('EXAMPLE TEST', utils.CSV, 'test')
    ])
    def test_finish_ok(self, content, content_type=utils.JSON, resource_location=None):

        _finish = utils.finish
        utils.finish = MagicMock(return_value='TEST')

        # Expected status depends on resource_location
        if resource_location:
            expected_status = 201
        else:
            expected_status = 200

        # Call the function
        response = utils.finish_ok(content, content_type, resource_location)

        # Check that finish function has been called
        utils.finish.assert_called_once_with(expected_status, content, content_type)

        # Check the response
        assert_equal(utils.finish.return_value, response)

        # Check location header
        if resource_location is not None:
            assert 'Location' in utils.response.headers
            assert_equal(resource_location, utils.response.headers['Location'])

        utils.finish = _finish

    @parameterized.expand([
        (400, 'EXAMPLE TEST'),
        (401, 'EXAMPLE TEST', 'EXTRA MSG')
    ])
    def test_finish_error(self, error_code, error_type, extra_msg=None):

        _finish = utils.finish
        _pase_response = utils.parse_response
        utils.finish = MagicMock(return_value='TEST')
        utils.parse_response = MagicMock(return_value='PARSED DATA')

        # Call the function
        response = utils.finish_error(error_code, error_type, extra_msg)

        # Expected object to parse
        response_data = {}
        response_data['error'] = {}
        response_data['error']['__type'] = error_type

        if extra_msg:
            response_data['error']['message'] = extra_msg

        # Check that the parse function has been called properly
        utils.parse_response.assert_called_once_with(response_data, utils.JSON)

        # Check that finish function has been called
        utils.finish.assert_called_once_with(error_code, utils.parse_response.return_value, utils.JSON)

        # Check the response
        assert_equal(utils.finish.return_value, response)

        utils.finish = _finish
        utils.parse_response = _pase_response

    @parameterized.expand([
        (utils.finish_not_authz, 403, 'Access denied'),
        (utils.finish_not_authz, 403, 'Access denied', 'EXTRA'),
        (utils.finish_not_found, 404, 'Not found'),
        (utils.finish_not_found, 404, 'Not found', 'EXTRA'),
        (utils.finish_bad_request, 400, 'Bad request'),
        (utils.finish_bad_request, 400, 'Bad request', 'EXTRA')
    ])
    def test_finish_functions(self, function, function_status, error_type, extra_msg=None):

        _finish_error = utils.finish_error
        utils.finish_error = MagicMock(return_value='ERROR')

        # Call the function
        response = function()

        # Check the response
        assert_equal(utils.finish_error.return_value, response)

        # Assert that finish_error is called
        utils.finish_error(function_status, error_type, extra_msg)

        utils.finish_error = _finish_error




