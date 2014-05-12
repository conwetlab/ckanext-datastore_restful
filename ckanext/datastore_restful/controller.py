import cgi
import logging
import re
import operator

import ckan.plugins as plugins
import ckan.lib.base as base
import ckan.model as model
import ckan.lib.helpers as helpers
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.lib.search as search
import ckanext.datastore_restful.response_parser as response_parser

from ckan.common import _, request, response

log = logging.getLogger(__name__)

TEXT = 'text'
HTML = 'html'
JSON = 'json'
XML = 'xml'
CSV = 'csv'

CONTENT_TYPES = {
    TEXT: 'text/plain;charset=utf-8',
    HTML: 'text/html;charset=utf-8',
    JSON: 'application/json;charset=utf-8',
    XML: 'application/xml;charset=utf-8',
    CSV: 'text/csv;charset=utf-8'
}

IDENTIFIER = 'pk'
IDENTIFIER_POS = 0
CKAN_IDENTIFIER = '_id'
DEFAULT_ACCEPT = '*/*'

CALLBACK_PARAMETER = 'callback'
RESOURCE_ID = 'resource_id'
RECORDS = 'records'


class RestfulDatastoreController(base.BaseController):

    def __call__(self, environ, start_response):
        # avoid status_code_redirect intercepting error responses
        environ['pylons.status_code_redirect'] = True
        return base.BaseController.__call__(self, environ, start_response)

    ###############################################################################################
    ##########################################  FINISH  ###########################################
    ###############################################################################################

    def _finish(self, status_int, response_data=None,
                content_type='text'):
        '''When a controller method has completed, call this method
        to prepare the response.
        @return response message - return this value from the controller
                                   method
                 e.g. return self._finish(404, 'Package not found')
        '''
        assert(isinstance(status_int, int))
        response.status_int = status_int
        response.headers['Content-Type'] = CONTENT_TYPES[content_type]
        
        # Support "JSONP" callback
        if content_type == JSON and status_int == 200 and CALLBACK_PARAMETER in request.params and \
                request.method == 'GET':
                callback = cgi.escape(request.params[CALLBACK_PARAMETER])
                response_data = self._wrap_jsonp(callback, response_data)

        return response_data

    def _parse_and_finish(self, status_int, response_data, content_type=JSON):
        parsed_data = self._parse_response(response_data, content_type)
        return self._finish(status_int, parsed_data, content_type)

    def _finish_ok(self, response_data=None,
                   content_type='json',
                   resource_location=None):
        '''If a controller method has completed successfully then
        calling this method will prepare the response.
        @param resource_location - specify this if a new
           resource has just been created.
        @return response message - return this value from the controller
                                   method
                                   e.g. return self._finish_ok(pkg_dict)
        '''
        if resource_location:
            status_int = 201
            self._set_response_header('Location', resource_location)
        else:
            status_int = 200

        return self._finish(status_int, response_data, content_type)

    def _finish_error(self, error_code, error_type, extra_msg=None):
        
        response_data = {}
        response_data['error'] = {}
        response_data['error']['__type'] = error_type
        
        if extra_msg:
            response_data['error']['message'] = _(extra_msg)

        return self._parse_and_finish(error_code, response_data)
        
    def _finish_not_authz(self, extra_msg=None):
        return self._finish_error(403, _('Access denied'), extra_msg)

    def _finish_not_found(self, extra_msg=None):
        return self._finish_error(404, _('Not found'), extra_msg)

    def _finish_bad_request(self, extra_msg=None):
        return self._finish_error(400, _('Bad request'), extra_msg)

    ###############################################################################################
    #########################################  AUXILIAR  ##########################################
    ###############################################################################################

    def _wrap_jsonp(self, callback, response_msg):
        return '%s(%s);' % (callback, response_msg)

    def _set_response_header(self, name, value):
        try:
            value = str(value)
        except Exception, inst:
            msg = "Couldn't convert '%s' header value '%s' to string: %s" % \
                (name, value, inst)
            raise Exception(msg)
        response.headers[name] = value

    def _get_context(self):
        return {
            'model': model,
            'session': model.Session,
            'user': plugins.toolkit.c.user
        }

    def _parse_get_parameters(self):
        get_parameters = request.GET.mixed()
        if CALLBACK_PARAMETER in get_parameters:
            del get_parameters[CALLBACK_PARAMETER]
        return get_parameters

    def _parse_body(self):
        try:
            return helpers.json.loads(request.body, encoding='utf-8')
        except ValueError, e:
            raise ValueError(_('JSON Error: Error decoding JSON data. '
                        'Error: %r ' % e))

    def _parse_response(self, data, content_type, field=None, entry=None):
        
        response_msg = None
        element = data
        field_xml_name = field

        # Maybe just a part of the data is intendeed to be returned
        if field:
            if field in element:
                element = element[field]
            else:
                element = []
        
        # Maybe only just one element is intendeed to be returned
        if entry is not None:
            element = element[entry]
            field_xml_name = field_xml_name[:-1]

        # Parse based on the content-type
        if content_type == JSON:
            if element == '':       # Return an empty response when we have an empty element
                response_msg = ''
            else:
                response_msg = helpers.json.dumps(element)
        elif content_type == XML:
            # Include URL as attribute of each record
            if field == RECORDS and RESOURCE_ID in data:
                for k in data[RECORDS]:
                    k['__url'] = 'http://%s/%s/%s/%s/%s' % (request.headers['host'], 'resource', data[RESOURCE_ID], 'entry', k[IDENTIFIER])

            response_msg = response_parser.xml_parser(element, field_xml_name)
        elif content_type == CSV:
            response_msg = response_parser.csv_parser(data)
        
        return response_msg

    def _entry_not_found(self, resource_id, entry_id):
        return plugins.toolkit.ObjectNotFound(_('The element %s does not exist in the resource %s' % (entry_id, resource_id)))

    def _get_content_type(self, accepted_headers):

        def _get_quality(accept_entry):
            quality = float(1)
            
            if len(accept_entry) > 1:
                regex_result = re.findall('q\=(\d*\.?\d*)$', accept_entry[1])
                if regex_result:
                    quality = float(regex_result[0])

            return quality
        
        accept_header = request.headers['ACCEPT']
        accepts = accept_header.split(',')
        valid_accepts = {}
        content_type = None

        for accept in accepts:
            accept_entry = accept.split(';')
            accept_type = accept_entry[0].strip().lower()

            # Accept */*. JSON is tried to be returned by default
            if DEFAULT_ACCEPT in accept_type:
                if not JSON in valid_accepts:
                    valid_accepts[JSON] = _get_quality(accept_entry)
            else:
                for key in accepted_headers:
                    # Ex: "application/json" in "application/json; chatset=..."
                    if key in CONTENT_TYPES and accept_type in CONTENT_TYPES[key]:
                        valid_accepts[key] = _get_quality(accept_entry)
                        break

        if len(valid_accepts) > 0:
            max_quality = max(valid_accepts.iteritems(), key=operator.itemgetter(1))  # 0: key, 1: value

            # It's necessary to check if the highest quality is the same than the one of JSON
            # In that case, JSON will be returned
            if JSON in valid_accepts and max_quality[1] == valid_accepts[JSON]:
                content_type = JSON
            else:
                content_type = max_quality[0]

        if not content_type:
            allowed_accepts = ', '.join(CONTENT_TYPES[k].split(';')[0] for k in accepted_headers if k in CONTENT_TYPES)
            raise plugins.toolkit.ValidationError({
                'data': { 'Accept': accept_header },
                'message': 'Only %s can be placed in the \'Accept\' header for this request' % allowed_accepts
            })

        return content_type

    def _execute_logic_function(self, logic_function, get_parameters, response_parser, accepted_formats=[JSON, XML]):

        def _remove_identifier(result):
            copy = result.copy()
            if RECORDS in copy:
                for record in copy[RECORDS]:
                    if '_id' in record:
                        del record['_id']
            return copy

        context = self._get_context()
        return_dict = {}

        try:
            content_type = self._get_content_type(accepted_formats)  # Get return content-type
            request_data = get_parameters()                          # Get parameters
            function = plugins.toolkit.get_action(logic_function)    # Get logic function
            result = function(context, request_data)                 # Execute the function
            result = _remove_identifier(result)                      # Remove _id from the results
            response_data = response_parser(result, content_type)    # Parse the results
            return self._finish_ok(response_data, content_type)      # Return the response
            
        except ValueError as e:
            return self._finish_bad_request(e)
        
        except dictization_functions.DataError as e:
            return_dict['error'] = {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}
            return self._parse_and_finish(400, return_dict, content_type='json')
        
        except plugins.toolkit.NotAuthorized as e:
            return self._finish_not_authz(e.extra_msg)
        
        except plugins.toolkit.ObjectNotFound as e:
            return self._finish_not_found(e.extra_msg)
        
        except plugins.toolkit.ValidationError as e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict['error'] = error_dict
            # CS nasty_string ignore
            return self._parse_and_finish(409, return_dict)
        
        except search.SearchQueryError as e:
            return_dict['error'] = {'__type': 'Search Query Error',
                                    'message': 'Search Query is invalid: %r' %
                                    e.args}
            return self._parse_and_finish(400, return_dict)
        
        except search.SearchError as e:
            return_dict['error'] = {'__type': 'Search Error',
                                    'message': 'Search error: %r' % e.args}
            return self._parse_and_finish(409, return_dict)
        
        except search.SearchIndexError as e:
            return_dict['error'] = {'__type': 'Search Index Error',
                    'message': 'Unable to add package to search index: %s' %
                    str(e)}
            return self._parse_and_finish(500, return_dict)

        except Exception as e:
            log.exception('Unexpected exception')
            return_dict['error'] = {'__type': 'Unexpected Error',
                    'message': '%s: %s' % (type(e).__name__, str(e)) }
            return self._parse_and_finish(500, return_dict)

    ###############################################################################################
    ########################################  RESOURCES  ##########################################
    ###############################################################################################

    def upsert_resource(self, resource_id):

        def get_parameters():

            request_data = {}
            request_data['fields'] = self._parse_body()
            request_data['force'] = True
            request_data[RESOURCE_ID] = resource_id

            for field in request_data['fields']:
                if field['id'] == IDENTIFIER:
                    raise plugins.toolkit.ValidationError(_('The field \'%s\' cannot be used since it\'s used internally' % IDENTIFIER))

            if isinstance(request_data['fields'], list):
                # Add the '#id' field in the fields parameter
                request_data['fields'].insert(IDENTIFIER_POS, {'type': 'int', 'id': IDENTIFIER})

                # Ignore primary_key field. The primary key is automatically set by us
                request_data['primary_key'] = [IDENTIFIER]

            return request_data

        def response_parser(result, content_type):
            return self._parse_response(result, content_type, 'fields')

        return self._execute_logic_function('datastore_create', get_parameters, response_parser)

    def structure(self, resource_id):

        def get_parameters():
            request_data = {}
            request_data[RESOURCE_ID] = resource_id
            return request_data

        def response_parser(result, content_type):
            fields_name = 'fields'

            #Avoid returning the _id field introduced by CKAN DataStore
            for f in result[fields_name]:
                if f['id'] == CKAN_IDENTIFIER:
                    result[fields_name].remove(f)
                    break

            return self._parse_response(result, content_type, fields_name)

        return self._execute_logic_function('datastore_search', get_parameters, response_parser)

    def delete_resource(self, resource_id):

        def get_parameters():
            request_data = self._parse_get_parameters()
            request_data[RESOURCE_ID] = resource_id
            request_data['force'] = True

            # If the filters parameter is set, the resource won't be deleted. Only the elements that
            # match this filter will be deleted so for this reason, it's necessary to remove this parameter
            if 'filters' in request_data:
                del request_data['filters']

            return request_data

        def response_parser(result, content_type):
            return ''

        return self._execute_logic_function('datastore_delete', get_parameters, response_parser)

    ###############################################################################################
    #########################################  ENTRIES  ###########################################
    ###############################################################################################

    def search_entries(self, resource_id):

        def get_parameters():
            PARAMETERS_TO_TRANSFORM = ['q', 'plain', 'language', 'limit', 'offset', 'fields', 'sort']
            DEFAULT_PARAMETERS = [RESOURCE_ID, 'filters'] + PARAMETERS_TO_TRANSFORM

            request_data = self._parse_get_parameters()

            #Append resource_id
            request_data[RESOURCE_ID] = resource_id

            #Convert from '$parameter' to 'parameter' (ex: '$offset' -> 'offset')
            for parameter in PARAMETERS_TO_TRANSFORM:
                modified_parameter = '$' + parameter
                if modified_parameter in request_data:
                    request_data[parameter] = request_data[modified_parameter]
                    del request_data[modified_parameter]

            #Push all the request parameters (except for the default ones) in the filters list
            filters = {}
            for parameter in request_data:
                if parameter not in DEFAULT_PARAMETERS:
                    filters[parameter] = request_data[parameter]

            request_data['filters'] = {}
            for filt in filters:
                request_data['filters'][filt] = filters[filt]
                del request_data[filt]

            return request_data

        def response_parser(result, content_type):
            return self._parse_response(result, content_type, RECORDS)

        return self._execute_logic_function('datastore_search', get_parameters, response_parser, [XML, JSON, CSV])
        
    def create_entries(self, resource_id):

        def get_parameters():

            request_data = {}
            request_data[RECORDS] = self._parse_body()
            request_data[RESOURCE_ID] = resource_id
            request_data['method'] = 'upsert'
            request_data['force'] = True

            # Get the max identifier used until now
            MAX_NAME = 'max'
            function = plugins.toolkit.get_action('datastore_search_sql')
            own_req = {}
            own_req['sql'] = 'SELECT MAX(pk) AS %s FROM \"%s\";' % (MAX_NAME, resource_id)
            max_id = function(self._get_context(), own_req)[RECORDS][0][MAX_NAME]

            if not max_id:
                max_id = 0

            #Asign pk to each record
            #The value specified by the user in the ID will be overwritten by our value
            for record in request_data[RECORDS]:
                if IDENTIFIER in record:
                    raise plugins.toolkit.ValidationError(_('The field \'%s\' is asigned automatically' % IDENTIFIER))
                else:
                    max_id += 1
                    record[IDENTIFIER] = max_id

            return request_data

        def response_parser(result, content_type):
            return self._parse_response(result, content_type, RECORDS)

        return self._execute_logic_function('datastore_upsert', get_parameters, response_parser)

    def upsert_entry(self, resource_id, entry_id):

        def get_parameters():

            request_data = {}
            request_data[RECORDS] = self._parse_body()
            request_data[RESOURCE_ID] = resource_id
            request_data['method'] = 'upsert'
            request_data['force'] = True

            if isinstance(request_data[RECORDS], dict):
                request_data[RECORDS] = [request_data[RECORDS]]
            else:
                raise plugins.toolkit.ValidationError(_('Only a single object can be inserted by request'))

            # The entry identifier cannot be changed
            if IDENTIFIER in request_data[RECORDS][0] and request_data[RECORDS][0][IDENTIFIER] != int(entry_id):
                raise plugins.toolkit.ValidationError(_('The entry identifier cannot be changed'))

            # Set entry identifier based on the URI
            if len(request_data[RECORDS][0]) > 0:
                request_data[RECORDS][0][IDENTIFIER] = int(entry_id)
            else:
                raise plugins.toolkit.ValidationError(_('Empty object received'))   # Check this error

            return request_data

        def response_parser(result, content_type):
            return self._parse_response(result, content_type, RECORDS, 0)

        return self._execute_logic_function('datastore_upsert', get_parameters, response_parser)

    def get_entry(self, resource_id, entry_id):

        def get_parameters():
            request_data = {}
            request_data['filters'] = {}
            request_data['filters'][IDENTIFIER] = entry_id
            request_data[RESOURCE_ID] = resource_id

            return request_data

        def response_parser(result, content_type):
            if len(result[RECORDS]) != 1:
                raise self._entry_not_found(resource_id, entry_id)

            return self._parse_response(result, content_type, RECORDS, 0)

        return self._execute_logic_function('datastore_search', get_parameters, response_parser)

    def delete_entry(self, resource_id, entry_id):

        def get_parameters():
            request_data = {}
            request_data['filters'] = {}
            request_data['filters'][IDENTIFIER] = entry_id
            request_data[RESOURCE_ID] = resource_id
            request_data['force'] = True

            # Does the entry exist?
            function = plugins.toolkit.get_action('datastore_search')
            own_req = {}
            own_req['filters'] = {IDENTIFIER: entry_id}
            own_req[RESOURCE_ID] = resource_id
            result = function(self._get_context(), own_req)

            if len(result[RECORDS]) != 1:
                raise self._entry_not_found(resource_id, entry_id)

            return request_data

        def response_parser(result, content_type):
            return ''

        return self._execute_logic_function('datastore_delete', get_parameters, response_parser)

    ###############################################################################################
    ############################################  SQL  ############################################
    ###############################################################################################

    def sql(self):

        def get_parameters():
            return self._parse_get_parameters()

        def response_parser(result, content_type):
            return self._parse_response(result, content_type, RECORDS)

        return self._execute_logic_function('datastore_search_sql', get_parameters, response_parser, [XML, JSON, CSV])

