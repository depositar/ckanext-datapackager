'''Functional tests for logic/action/update.py.

'''

from io import BytesIO
import json
import re
import zipfile

import pytest
import responses

from ckan.common import config
import ckan.plugins.toolkit as toolkit
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.fixture
def mock_update_dp(mocker):
    dp_zip_file = None

    def synchronous_enqueue_job(job_func, args=None, kwargs=None, title=None):
        '''
        Synchronous mock for ``ckan.plugins.toolkit.enqueue_job``.
        '''
        args = args or []
        kwargs = kwargs or {}
        job_func(*args, **kwargs)

    def capture_upload(*args, **kwargs):
        nonlocal dp_zip_file
        upload_file = kwargs.get('files')['upload']
        dp_zip_file = BytesIO(upload_file.read())

    mocker.patch(
        'ckan.plugins.toolkit.enqueue_job',
        side_effect=synchronous_enqueue_job
    )
    mocker.patch(
        'ckanapi.localckan.LocalCKAN.call_action',
        side_effect=capture_upload
    )

    def get_file():
        dp_zip_file.seek(0)
        return dp_zip_file

    yield get_file


@pytest.mark.ckan_config('ckan.plugins', 'datapackager')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestUpdate:
    @responses.activate
    def test_update_datapackage(self, app, create_with_upload, mock_update_dp):
        responses.add_passthru(toolkit.config['solr_url'])
        content = 'hello world'

        dataset = factories.Dataset(
            maintainer='John Smith',
            maintainer_email='jsmith@email.com',
            license_id='cc-zero'
        )

        # Mocking download of resources
        responses.add(
            responses.GET,
            re.compile(r'{}/dataset/.*/download/.*'
                       .format(config["ckan.site_url"])),
            body=content
        )

        # Add a resource with an uploaded data file
        uploaded_resource = create_with_upload(
            content,
            'file.txt',
            name='test',
            package_id=dataset['id']
        )

        dp_zip_file = mock_update_dp()

        with zipfile.ZipFile(dp_zip_file, 'r') as zipf:
            assert zipf.namelist() == ['file.txt', 'datapackage.json']
            datapackage_json = zipf.read('datapackage.json')
            datapackage = json.loads(datapackage_json)
            assert datapackage['name'] == dataset['name']
            assert datapackage['title'] == dataset['title']
            assert datapackage['description'] == datapackage['description']
            assert datapackage['contributors'] == [{
                'title': 'John Smith',
                'email': 'jsmith@email.com',
                'roles': ['maintainer']
            }]
            assert datapackage['licenses'][0]['name'] == 'cc-zero'
            assert {
                'name': 'test',
                'type': 'text',
                'path': 'file.txt',
                'ckan:id': uploaded_resource['id']
            }.items() <= datapackage['resources'][0].items()
            assert datapackage['ckan:id'] == dataset['id']

    def test_update_datapackage_with_missing_id(self):
        with pytest.raises(toolkit.ValidationError):
            helpers.call_action('datapackage_update')

    @pytest.mark.ckan_config('ckanext.datapackager.max_dataset_size', '0')
    def test_update_datapackage_with_large_dataset(self, create_with_upload):
        dataset = factories.Dataset()

        # Add a resource with an uploaded data file
        create_with_upload(
            'hello world',
            'file.txt',
            name='test',
            package_id=dataset['id']
        )

        with pytest.raises(toolkit.ValidationError):
            helpers.call_action('datapackage_update', id=dataset['id'])
