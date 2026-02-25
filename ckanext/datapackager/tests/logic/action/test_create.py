import json
from io import BytesIO

import pytest
import responses
from werkzeug.datastructures import FileStorage

import ckan.tests.helpers as helpers
import ckanext.datapackager.tests.helpers as custom_helpers
import ckan.plugins.toolkit as toolkit
import ckan.tests.factories as factories

import re


@pytest.mark.ckan_config('ckan.plugins', 'datapackager')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestPackageCreateFromDataPackage():
    def test_it_requires_a_url_if_theres_no_upload_param(self):
        with pytest.raises(toolkit.ValidationError):
            helpers.call_action('package_create_from_datapackage')

    @responses.activate
    def test_it_raises_if_datapackage_is_invalid(self):
        responses.add_passthru(toolkit.config['solr_url'])

        url = 'http://www.example.com/datapackage.json'
        datapackage = {}
        responses.add(responses.GET, url, json=datapackage)

        with pytest.raises(toolkit.ValidationError):
            helpers.call_action('package_create_from_datapackage', url=url)

    @responses.activate
    def test_it_raises_if_datapackage_is_invalid_dplib_py(self):
        url = 'http://www.example.com/datapackage.json'
        datapackage = {
            'name': 'foo',
            'id': 1234,
            'resources': [
                {
                    'name': 'the-resource',
                    'path': 'http://www.example.com/data.csv',
                }
            ]
        }
        responses.add(responses.GET, url, json=datapackage)

        with pytest.raises(toolkit.ValidationError):
            helpers.call_action('package_create_from_datapackage', url=url)

    def test_it_raises_if_datapackage_is_unsafe(self):
        datapackage = {
            'name': 'unsafe',
            'resources': [
                {
                    'name': 'unsafe-resource',
                    'path': '/etc/shadow',
                }
            ]
        }

        upload = FileStorage(BytesIO(json.dumps(datapackage).encode('utf-8')),
                             filename='test')

        with pytest.raises(toolkit.ValidationError):
            helpers.call_action('package_create_from_datapackage', upload=upload)

    @responses.activate
    def test_it_creates_the_dataset(self):
        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.json'
        datapackage = {
            'name': 'foo',
            'resources': [
                {
                    'name': 'the-resource',
                    'path': 'http://www.example.com/data.csv',
                }
            ],
        }
        responses.add(responses.GET, url, json=datapackage)

        dataset = helpers.call_action('package_create_from_datapackage',
                                      url=url)
        assert dataset['state'] == 'active'

        resource = dataset.get('resources')[0]
        assert resource['name'] == 'data.csv'
        assert resource['url'] == datapackage['resources'][0]['path']

    @responses.activate
    def test_it_creates_a_dataset_without_resources(self):
        responses.add_passthru(toolkit.config['solr_url'])

        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.json'
        datapackage = {
            'name': 'foo',
            'resources': [
                {
                    'name': 'the-resource',
                    'data': [{'a': 1, 'b': 2}]
                }
            ]
        }
        responses.add(responses.GET, url, json=datapackage)

        helpers.call_action('package_create_from_datapackage', url=url)

        helpers.call_action('package_show', id=datapackage['name'])

    @responses.activate
    def test_it_deletes_dataset_on_error_when_creating_resources(self):
        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.zip'
        datapkg_path = custom_helpers.fixture_path(
            'datetimes-datapackage-with-inexistent-resource.zip'
        )

        original_datasets = helpers.call_action('package_list')

        with open(datapkg_path, 'rb') as f:
            responses.add(responses.GET, url,
                          content_type='application/zip', body=f.read())
            with pytest.raises(toolkit.ValidationError):
                helpers.call_action('package_create_from_datapackage', url=url)

        new_datasets = helpers.call_action('package_list')
        assert original_datasets == new_datasets

    @responses.activate
    def test_it_uploads_local_files(self):
        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.zip'
        datapkg_path = custom_helpers.fixture_path('datetimes-datapackage.zip')
        with open(datapkg_path, 'rb') as f:
            responses.add(responses.GET, url,
                          content_type='application/zip', body=f.read())

        helpers.call_action('package_create_from_datapackage', url=url)

        dataset = helpers.call_action('package_show', id='datetimes')
        resources = dataset.get('resources')

        assert resources[0]['url_type'] == 'upload'
        assert re.search(r'datetimes\.csv', resources[0]['url'])

    @responses.activate
    def test_it_allows_specifying_the_dataset_name(self):
        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.json'
        datapackage = {
            'name': 'foo',
            'resources': [
                {'name': 'bar',
                 'path': 'http://example.com/some.csv'}
            ]
        }
        responses.add(responses.GET, url, json=datapackage)

        dataset = helpers.call_action('package_create_from_datapackage',
                                      url=url,
                                      name='bar')
        assert dataset['name'] == 'bar'

    @responses.activate
    def test_it_creates_unique_name_if_name_wasnt_specified(self):
        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.json'
        datapackage = {
            'name': 'foo',
            'resources': [
                {'name': 'bar',
                 'path': 'http://example.com/some.csv'}
            ]
        }
        responses.add(responses.GET, url, json=datapackage)

        helpers.call_action('package_create', name=datapackage['name'])
        dataset = helpers.call_action('package_create_from_datapackage',
                                      url=url)
        assert dataset['name'].startswith('foo')

    @responses.activate
    def test_it_fails_if_specifying_name_that_already_exists(self):
        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.json'
        datapackage = {
            'name': 'foo',
            'resources': [
                {'name': 'bar',
                 'path': 'http://example.com/some.csv'}
            ]
        }
        responses.add(responses.GET, url, json=datapackage)

        helpers.call_action('package_create', name=datapackage['name'])

        with pytest.raises(toolkit.ValidationError):
            helpers.call_action('package_create_from_datapackage', url=url, name=datapackage['name'])

    @responses.activate
    def test_it_allows_changing_dataset_visibility(self):
        responses.add_passthru(toolkit.config['solr_url'])
        url = 'http://www.example.com/datapackage.json'
        datapackage = {
            'name': 'foo',
            'resources': [
                {'name': 'bar',
                 'path': 'http://example.com/some.csv'}
            ]
        }
        responses.add(responses.GET, url, json=datapackage)

        user = factories.Sysadmin()
        organization = factories.Organization()
        dataset = helpers.call_action('package_create_from_datapackage',
                                      context={'user': user['id']},
                                      url=url,
                                      owner_org=organization['id'],
                                      private='true')
        assert dataset['private']

    def test_it_allows_uploading_a_datapackage(self):
        responses.add_passthru(toolkit.config['solr_url'])
        datapackage = {
            'name': 'foo',
            'resources': [
                {'name': 'bar',
                 'path': 'http://example.com/some.csv'}
            ]

        }

        upload = FileStorage(BytesIO(json.dumps(datapackage).encode('utf-8')),
                     filename='test')
        dataset = helpers.call_action('package_create_from_datapackage',
                                      upload=upload)
        assert dataset['name'] == 'foo'
