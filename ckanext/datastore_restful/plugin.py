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
        #Dump a resource
        m.connect('/resource/{resource_id}/dump',
                  controller='ckanext.datastore.controller:DatastoreController',
                  action='dump', conditions=GET)

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


