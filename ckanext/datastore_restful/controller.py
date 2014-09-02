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

import logging

import ckan.plugins as plugins
import ckan.lib.base as base
import ckan.model as model
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.lib.search as search
import ckanext.datastore_restful.utils as utils

from ckan.common import _, request

log = logging.getLogger(__name__)

IDENTIFIER = 'pk'
IDENTIFIER_POS = 0
CKAN_IDENTIFIER = '_id'

RESOURCE_ID = 'resource_id'
RECORDS = 'records'


class RestfulDatastoreController(base.BaseController):

    def __call__(self, environ, start_response):
        # avoid status_code_redirect intercepting error responses
        environ['pylons.status_code_redirect'] = True
        return base.BaseController.__call__(self, environ, start_response)

    ###############################################################################################
    #########################################  AUXILIAR  ##########################################
    ###############################################################################################

    def _parse_response(self, data, content_type, field=None, entry=None):

        if content_type == utils.XML:
            # Include URL as attribute of each record
            if field == RECORDS and RESOURCE_ID in data:
                for k in data[RECORDS]:
                    if IDENTIFIER in k:
                        k['__url'] = 'http://%s/%s/%s/%s/%s' % (request.headers['host'], 'resource', data[RESOURCE_ID], 'entry', k[IDENTIFIER])

        return utils.parse_response(data, content_type, field, entry)

    def _get_context(self):
        return {
            'model': model,
            'session': model.Session,
            'user': plugins.toolkit.c.user
        }

    def _entry_not_found(self, resource_id, entry_id):
        return plugins.toolkit.ObjectNotFound(_('The element %s does not exist in the resource %s' % (entry_id, resource_id)))

    def _execute_logic_function(self, logic_function, get_parameters, response_parser, accepted_formats=[utils.JSON, utils.XML]):

        def _remove_identifier(result):
            copy = result.copy()
            if RECORDS in copy:
                for record in copy[RECORDS]:
                    if '_id' in record:
                        del record['_id']
            return copy

        return_dict = {}

        try:
            context = self._get_context()                            # Get Context
            content_type = utils.get_content_type(accepted_formats)  # Get return content-type
            request_data = get_parameters()                          # Get parameters
            function = plugins.toolkit.get_action(logic_function)    # Get logic function
            result = function(context, request_data)                 # Execute the function
            result = _remove_identifier(result)                      # Remove _id from the results
            response_data = response_parser(result, content_type)    # Parse the results
            return utils.finish_ok(response_data, content_type)      # Return the response

        except ValueError as e:
            return utils.finish_bad_request(e)

        except dictization_functions.DataError as e:
            return_dict['error'] = {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}
            return utils.parse_and_finish(400, return_dict, content_type='json')

        except plugins.toolkit.NotAuthorized as e:
            return utils.finish_not_authz(e.extra_msg)

        except plugins.toolkit.ObjectNotFound as e:
            return utils.finish_not_found(e.extra_msg)

        except plugins.toolkit.ValidationError as e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict['error'] = error_dict
            # CS nasty_string ignore
            return utils.parse_and_finish(409, return_dict)

        except search.SearchQueryError as e:
            return_dict['error'] = {'__type': 'Search Query Error',
                                    'message': 'Search Query is invalid: %r' %
                                    e.args}
            return utils.parse_and_finish(400, return_dict)

        except search.SearchError as e:
            return_dict['error'] = {'__type': 'Search Error',
                                    'message': 'Search error: %r' % e.args}
            return utils.parse_and_finish(409, return_dict)

        except search.SearchIndexError as e:
            return_dict['error'] = {'__type': 'Search Index Error',
                                    'message': 'Unable to add package to search index: %s' %
                                    str(e)}
            return utils.parse_and_finish(500, return_dict)

        except Exception as e:
            log.exception('Unexpected exception')
            return_dict['error'] = {'__type': 'Unexpected Error',
                                    'message': '%s: %s' % (type(e).__name__, str(e))}
            return utils.parse_and_finish(500, return_dict)

    ###############################################################################################
    ########################################  RESOURCES  ##########################################
    ###############################################################################################

    def upsert_resource(self, resource_id):

        def get_parameters():

            def _not_valid_input():
                raise plugins.toolkit.ValidationError({
                    'message': _('Only lists of dicts can be placed to create resources'),
                    'data': request_data['fields']
                })

            request_data = {}
            request_data['fields'] = utils.parse_body()
            request_data['force'] = True
            request_data[RESOURCE_ID] = resource_id

            # If fields is not a list, we realy on CKAN operation to return the appropiate error
            if not isinstance(request_data['fields'], list):
                _not_valid_input()
            else:
                for field in request_data['fields']:
                    if not isinstance(field, dict):
                        _not_valid_input()
                    else:
                        # If 'id' is not in fields, CKAN will return its own error
                        if 'id' in field and field['id'] == IDENTIFIER:
                            raise plugins.toolkit.ValidationError(_('The field \'%s\' cannot be used since it\'s used internally' % IDENTIFIER))

                # Add the 'pk' field in the fields parameter
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
            request_data = {}
            request_data[RESOURCE_ID] = resource_id
            request_data['force'] = True

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

            request_data = utils.parse_get_parameters()

            #Append resource_id
            request_data[RESOURCE_ID] = resource_id

            #Convert from '$parameter' to 'parameter' (ex: '$offset' -> 'offset')
            for parameter in PARAMETERS_TO_TRANSFORM:
                modified_parameter = '$' + parameter
                if modified_parameter in request_data:
                    request_data[parameter] = request_data[modified_parameter]
                    del request_data[modified_parameter]

            #Push all the request parameters (except for the default ones) in the filters list
            request_data['filters'] = {}
            for parameter in request_data:
                if parameter not in DEFAULT_PARAMETERS:
                    request_data['filters'][parameter] = request_data[parameter]

            # Remove parameters considered as filter from the request_data object since they
            # are already in the filters object
            for filt in request_data['filters']:
                del request_data[filt]

            return request_data

        def response_parser(result, content_type):
            return self._parse_response(result, content_type, RECORDS)

        return self._execute_logic_function('datastore_search', get_parameters, response_parser,
                                            [utils.JSON, utils.XML, utils.CSV])

    def create_entries(self, resource_id):

        def get_parameters():

            def _not_valid_input():
                raise plugins.toolkit.ValidationError({
                    'message': _('Only lists of dicts can be placed to create entries'),
                    'data': request_data[RECORDS]
                })

            request_data = {}
            request_data[RECORDS] = utils.parse_body()
            request_data[RESOURCE_ID] = resource_id
            request_data['method'] = 'upsert'
            request_data['force'] = True

            if not isinstance(request_data[RECORDS], list):
                _not_valid_input()

            # Get the max identifier used until now
            MAX_NAME = 'max'
            function = plugins.toolkit.get_action('datastore_search_sql')
            own_req = {}
            own_req['sql'] = 'SELECT MAX(pk) AS %s FROM \"%s\";' % (MAX_NAME, resource_id)
            max_id = function(self._get_context(), own_req)[RECORDS][0][MAX_NAME]

            if max_id is None:
                max_id = 0

            #Asign pk to each record
            #The value specified by the user in the ID will be overwritten by our value
            for record in request_data[RECORDS]:
                if not isinstance(record, dict):
                    _not_valid_input()

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
            request_data[RECORDS] = utils.parse_body()
            request_data[RESOURCE_ID] = resource_id
            request_data['method'] = 'upsert'
            request_data['force'] = True

            if isinstance(request_data[RECORDS], dict):
                request_data[RECORDS] = [request_data[RECORDS]]
            else:
                raise plugins.toolkit.ValidationError({
                    'message': _('Only dicts can be placed to create/modify an entry'),
                    'data': request_data[RECORDS]
                })

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
            return utils.parse_get_parameters()

        def response_parser(result, content_type):
            return self._parse_response(result, content_type, RECORDS)

        return self._execute_logic_function('datastore_search_sql', get_parameters, response_parser,
                                            [utils.JSON, utils.XML, utils.CSV])
