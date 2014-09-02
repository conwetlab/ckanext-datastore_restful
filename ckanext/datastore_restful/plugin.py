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

import ckan.plugins as plugins

GET = dict(method=['GET'])
PUT = dict(method=['PUT'])
POST = dict(method=['POST'])
DELETE = dict(method=['DELETE'])

class RestfulDataStorePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IRoutes, inherit=True)

    def after_map(self, m):
        #Create/update the resource
        m.connect('/resource/{resource_id}',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='upsert_resource', conditions=PUT)
        #Get the entire resource
        m.connect('/resource/{resource_id}',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='structure', conditions=GET)
        #Delete a resource
        m.connect('/resource/{resource_id}',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='delete_resource', conditions=DELETE)

        #Get the entire collection of entries
        m.connect('/resource/{resource_id}/entry',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='search_entries', conditions=GET)
        #Insert a entry or a set of entries
        m.connect('/resource/{resource_id}/entry',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='create_entries', conditions=POST)

        #Create/update an entry 
        m.connect('/resource/{resource_id}/entry/{entry_id}',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='upsert_entry', conditions=PUT)
        #Get an entry
        m.connect('/resource/{resource_id}/entry/{entry_id}',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='get_entry', conditions=GET)
        #Delete an entry
        m.connect('/resource/{resource_id}/entry/{entry_id}',
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='delete_entry', conditions=DELETE)

        #Search SQL
        m.connect('/search_sql', 
                  controller='ckanext.datastore_restful.controller:RestfulDatastoreController',
                  action='sql', conditions=GET)
        
        return m 


