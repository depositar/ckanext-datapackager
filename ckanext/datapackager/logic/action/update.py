import ckan.plugins.toolkit as toolkit

from ckanext.datapackager import jobs
from ckanext.datapackager.lib import util


def datapackage_update(context, data_dict):
    '''Update the Data Package zip file for the given dataset.

    '''
    try:
        dataset_id = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': toolkit._('Missing id')})

    try:
        toolkit.check_access('package_update', context, data_dict)
    except toolkit.NotAuthorized:
        return {
            'success': False,
            'msg': toolkit._(
                'Not authorized to update the Data Package')}

    dataset_dict = toolkit.get_action('package_show')(context,
                                                      {'id': dataset_id})

    # Exclude existing Data Package zip and linked resources
    dataset, resources_to_include, existing_zip_resource = \
        util.remove_resources_that_should_not_be_included_in_the_datapackage(
            dataset_dict)

    if not resources_to_include:
        if existing_zip_resource:
            toolkit.enqueue_job(jobs.delete_zip,
                                [dataset, existing_zip_resource])
        raise toolkit.ValidationError(
            {'message': toolkit._('Data Package: At least one resource '
                                  'with URL is required to create a Data '
                                  'Package. The Data Package will be '
                                  'deleted if it exists.')})

    # Check if the total resource size is over the limit
    total_size_of_resources = sum(res['size'] for res in resources_to_include
                                  if res['size'] is not None)
    max_size = util.get_max_dataset_size()
    if total_size_of_resources > max_size * 1 << 20:
        if existing_zip_resource:
            toolkit.enqueue_job(jobs.delete_zip,
                                [dataset, existing_zip_resource])
        raise toolkit.ValidationError(
            {'message': toolkit._('Data Package: Only datasets with a total '
                                  'resource size of {0} MB or less are '
                                  'supported to create a Data Package. The '
                                  'Data Package will be deleted if it exists.')
                               .format(max_size)})

    datapackage = util.generate_datapackage_json(dataset)

    hash_metadata_modified_in_resources = \
        util.get_hash_in_datapackage_and_resources(
            datapackage, resources_to_include)

    # Check if the Data Package zip needs an update
    if existing_zip_resource:
        if hash_metadata_modified_in_resources == \
                existing_zip_resource.get('datapackage_hash'):
            raise toolkit.ValidationError(
                {'message': toolkit._("The Data Package doesn't need an "
                                      "update as its metadata and resources "
                                      "haven't changed: {}")
                                   .format(dataset_dict['name'])})

    toolkit.enqueue_job(jobs.update_zip,
                        [dataset, datapackage, existing_zip_resource])
