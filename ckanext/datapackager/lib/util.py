'''Miscellaneous shared utility functions.

'''
import hashlib
import os.path

from ckan.plugins import toolkit
from dplib.plugins.ckan.models import CkanPackage

import ckanext.datapackager.exceptions as exceptions


log = __import__('logging').getLogger(__name__)


def get_path_to_resource_file(resource_dict):
    '''Return the local filesystem path to an uploaded resource file.

    The given ``resource_dict`` should be for a resource whose file has been
    uploaded to the FileStore.

    :param resource_dict: dict of the resource whose file you want
    :type resource_dict: a resource dict, e.g. from action ``resource_show``

    :rtype: string
    :returns: the absolute path to the resource file on the local filesystem

    :raises ckanext.datapackager.exceptions.ResourceFileDoesNotExistException:
        If there is no uploaded file for the given resource (e.g. if the
        resource contains a link to a remote file instead)

    '''
    # We need to do a direct import here, there's no nicer way yet.
    import ckan.lib.uploader as uploader

    upload = uploader.ResourceUpload(resource_dict)
    path = upload.get_path(resource_dict['id'])
    path = os.path.abspath(path)

    if not os.path.isfile(path):
        raise exceptions.ResourceFileDoesNotExistException

    return path


def remove_resources_that_should_not_be_included_in_the_datapackage(dataset):
    existing_zip_resource = None
    resources_to_include = []

    for i, res in enumerate(dataset['resources']):
        if res.get('datapackage_metadata_modified'):
            # This is an existing Data Package zip
            log.debug('Resource {}/{} skipped - is the zip itself'
                      .format(i + 1, len(dataset['resources'])))
            existing_zip_resource = res
            continue

        # Skip resources without url
        if res['url'] == '':
            log.debug('Resource {}/{} skipped - url is empty'
                      .format(i + 1, len(dataset['resources'])))
            continue

        resources_to_include.append(res)

    dataset = dict(dataset, resources=resources_to_include)

    return dataset, resources_to_include, existing_zip_resource


def get_hash_in_datapackage_and_resources(datapackage, resources):
    datapackage_str = str(tuple(sorted(datapackage.items())))
    metadata_modified_list = [res['metadata_modified'] for res in resources]
    hashable = datapackage_str + \
        ','.join(metadata_modified_list)

    return hashlib.md5(hashable.encode('utf-8')).hexdigest()


def get_max_dataset_size():
    return int(toolkit.config.get('ckanext.datapackager.max_dataset_size', 10))


def get_api_token():
    api_token = toolkit.config.get('ckanext.datapackager.api_token', None)
    if api_token:
        return api_token

    # Consider also the CKAN default api_token for backward compatibility
    site_user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    return site_user['apikey']


def get_site_url():
    site_url = toolkit.config.get('ckanext.datapackager.site_url', None)
    return site_url


def create_dataset_from_datapackage(dp):
    return CkanPackage.from_dp(dp).to_dict()


def generate_datapackage_json(dataset):
    return CkanPackage.from_dict(dataset).to_dp().to_dict()
