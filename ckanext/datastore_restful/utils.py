import cgi
import operator
import re

import ckan.plugins as plugins
import ckan.lib.helpers as helpers
import ckanext.datastore_restful.response_parser as response_parser

from collections import OrderedDict
from ckan.common import _, request, response

DEFAULT_ACCEPT = '*/*'
CALLBACK_PARAMETER = 'callback'

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


###############################################################################################
#########################################  AUXILIAR  ##########################################
###############################################################################################

def _wrap_jsonp(callback, response_msg):
    return '%s(%s);' % (callback, response_msg)


def _set_response_header(name, value):
    try:
        value = str(value)
    except Exception, inst:
        msg = "Couldn't convert '%s' header value '%s' to string: %s" % \
            (name, value, inst)
        raise Exception(msg)
    response.headers[name] = value


###############################################################################################
###########################################  MAIN  ############################################
###############################################################################################

def parse_get_parameters():
    get_parameters = request.GET.mixed()
    if CALLBACK_PARAMETER in get_parameters:
        del get_parameters[CALLBACK_PARAMETER]
    return get_parameters


def parse_body():
    try:
        return helpers.json.loads(request.body, encoding='utf-8')
    except ValueError, e:
        raise ValueError(_('JSON Error: Error decoding JSON data. '
                         'Error: %r ' % e))


def get_content_type(accepted_headers):

    def _get_quality(accept_entry):
        quality = float(1)

        if len(accept_entry) > 1:
            regex_result = re.findall('^q\=(\d*\.?\d*)$', accept_entry[1].strip())
            if regex_result:
                quality = float(regex_result[0])

        return quality

    accept_header = request.headers['ACCEPT']
    accepts = accept_header.split(',')
    valid_accepts = OrderedDict()
    content_type = None

    for accept in accepts:
        accept_entry = accept.split(';')
        accept_type = accept_entry[0].strip().lower()

        # Accept */*. JSON is tried to be returned by default
        if DEFAULT_ACCEPT in accept_type:
            if not accepted_headers[0] in valid_accepts:
                valid_accepts[accepted_headers[0]] = _get_quality(accept_entry)
        else:
            for key in accepted_headers:
                # Ex: "application/json" in "application/json; chatset=..."
                if key in CONTENT_TYPES and accept_type in CONTENT_TYPES[key]:
                    valid_accepts[key] = _get_quality(accept_entry)
                    break

    if len(valid_accepts) > 0:
        max_quality = max(valid_accepts.iteritems(), key=operator.itemgetter(1))  # 0: key, 1: value
        content_type = max_quality[0]

        # It's necessary to check if the highest quality is the same than the one of JSON
        # In that case, JSON will be returned
        # if accepted_headers[0] in valid_accepts and max_quality[1] == valid_accepts[accepted_headers[0]]:
        #     content_type = JSON
        # else:
        #     content_type = max_quality[0]

    if not content_type:
        allowed_accepts = ', '.join(CONTENT_TYPES[k].split(';')[0] for k in accepted_headers if k in CONTENT_TYPES)
        raise plugins.toolkit.ValidationError({
            'data': {'Accept': accept_header},
            'message': 'Only %s can be placed in the \'Accept\' header for this request' % allowed_accepts
        })

    return content_type


def parse_response(data, content_type, field=None, entry=None):

    response_msg = None
    element = data
    field_xml_name = field

    # Maybe just a part of the data is intendeed to be returned
    if field:
        if field in element:
            element = element[field]

    # Maybe only just one element is intendeed to be returned
    if entry is not None:
        element = element[entry]
        field_xml_name = field_xml_name[:-1]

    # Parse based on the content-type
    if content_type == JSON:
        response_msg = helpers.json.dumps(element)
    elif content_type == XML:
        response_msg = response_parser.xml_parser(element, field_xml_name)
    elif content_type == CSV:
        response_msg = response_parser.csv_parser(data)

    return response_msg


def finish(status_int, response_data=None,
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
            response_data = _wrap_jsonp(callback, response_data)

    return response_data


def parse_and_finish(status_int, response_data, content_type=JSON):
    parsed_data = parse_response(response_data, content_type)
    return finish(status_int, parsed_data, content_type)


def finish_ok(response_data=None,
              content_type=JSON,
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
        _set_response_header('Location', resource_location)
    else:
        status_int = 200

    return finish(status_int, response_data, content_type)


def finish_error(error_code, error_type, extra_msg=None):

    response_data = {}
    response_data['error'] = {}
    response_data['error']['__type'] = error_type

    if extra_msg:
        response_data['error']['message'] = _(extra_msg)

    return parse_and_finish(error_code, response_data)


def finish_not_authz(extra_msg=None):
    return finish_error(403, _('Access denied'), extra_msg)


def finish_not_found(extra_msg=None):
    return finish_error(404, _('Not found'), extra_msg)


def finish_bad_request(extra_msg=None):
    return finish_error(400, _('Bad request'), extra_msg)
