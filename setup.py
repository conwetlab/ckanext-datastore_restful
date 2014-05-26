from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='ckanext-datastore_restful',
    version=version,
    description="This is a plugin to get the DataStore responses in a Restful way",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Aitor Magan',
    author_email='amagan@conwet.com',
    url='',
    license='Affero GPLv3',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.datastore_restful'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        datastore_restful=ckanext.datastore_restful.plugin:RestfulDataStorePlugin
    ''',
)
