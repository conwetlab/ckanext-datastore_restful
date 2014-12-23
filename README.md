CKAN DataStore Restful [![Build Status](https://build.conwet.fi.upm.es/jenkins/buildStatus/icon?job=ckan_datastore_restful)](https://build.conwet.fi.upm.es/jenkins/job/ckan_datastore_restful/)
======================

CKAN is a powerful tool that allows users to publish data in different formats. In addition, CKAN offers extensions that transform this datasets into HTTP APIs to ease the access to them. Nevertheless, this API is not REST since it only uses GET and POST verbs. For this reason we have created this extenion that you can easily install in your CKAN instance. 

Installation
------------
Install this extension in your CKAN is instance is as easy as intall any other CKAN extension.
* Download the source from this GitHub repo.
* Install the extension by running `python setup.py develop`
* Modify your configuration file (generally in `/etc/ckan/default/production.ini`) and add `datastore_restful` in the `ckan.plugins` setting.
* Restart your apache2 reserver (`sudo service apache2 restart`)
* That's All!

Tests
-----
This sofware contains a set of test to detect errors and failures. You can run this tests by running the following command:
```
nosetests --ckan --with-pylons=test.ini ckanext/datastore_restful/tests/
```
**Note:** The `test.ini` file contains a link to the CKAN `test-core.ini` file. You will need to change that link to the real path of the file in your system (generally `/usr/lib/ckan/default/src/ckan/test-core.ini`). 

You can also generate coverage reports by running:
```
nosetests --ckan --with-pylons=test.ini --with-coverage --cover-package=ckanext.datastore_restful --cover-inclusive --cover-erase . --cover-xml
```

API Specification
-----------------
[Acess the DataStore Restful API specification by clicking here.](https://github.com/conwetlab/ckanext-datastore_restful/wiki)