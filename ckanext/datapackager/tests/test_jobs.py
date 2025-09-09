'''Functional tests for jobs.py.

'''

import pytest
import requests

from ckanext.datapackager import jobs


@pytest.mark.ckan_config('ckan.plugins', 'datapackager')
@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestJobs:
    def test_download_resource_into_zip_error(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = requests.ConnectionError
        mocker.patch('ckanext.datapackager.jobs.requests.get',
                     return_value=mock_response)

        with pytest.raises(jobs.DownloadError):
            jobs._download_resource_into_zip(
                'http://example.com',
                'file.txt',
                None
            )
