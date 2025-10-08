import datetime
import os

from ckan import model
from ckan.lib.plugins import DefaultTranslation
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from flask import has_request_context

from ckanext.datapackager import helpers
from ckanext.datapackager.controllers import datapackage
from ckanext.datapackager.logic.action.get import package_show_as_datapackage
from ckanext.datapackager.logic.action.update import datapackage_update


log = __import__('logging').getLogger(__name__)


class DataPackagerPlugin(plugins.SingletonPlugin, DefaultTranslation):
    '''Plugin that adds importing/exporting datasets as Data Packages.
    '''
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IDomainObjectModification)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)

    def update_config(self, config):
        toolkit.add_template_directory(config, '../templates')

    def get_actions(self):
        return {
            'package_show_as_datapackage': package_show_as_datapackage,
            'datapackage_update': datapackage_update,
        }

    def get_blueprint(self):
        blueprint = Blueprint("datapackager", __name__)
        # As long as the URL for import_datapackage_view and import_datapackage are the same, reverse lookups from import_datapackage will work
        blueprint.add_url_rule(
            "/dataset/<package_id>/datapackage.json",
            view_func=datapackage.export_datapackage,
            endpoint="export_datapackage",
            methods=["GET"],
        )
        return blueprint

    # A dictionary to store processed dataset ids and timestamps
    _processed_packages = {}

    def notify(self, entity, operation):
        # Only handle the events for datasets
        if not isinstance(entity, model.Package):
            return

        # Skip if there is no resources in the dataset
        # E.g. the first step in dataset creation
        if operation == 'changed' and entity.resources:
            # Skip if the dataset is going to be deleted
            if entity.state == 'deleted':
                return
            if entity.id in self._processed_packages:
                last_processed = self._processed_packages[entity.id]
                # If processed within the last second, ignore this event
                if (datetime.datetime.now() - last_processed).seconds < 1:
                    return

            update_datapackage(entity.id)

            # Record the current time to prevent duplicate events
            self._processed_packages[entity.id] = datetime.datetime.now()

    def before_dataset_index(self, pkg_dict):
        try:
            if pkg_dict['res_name'] == 'Data Package':
                # Remove the Data Package zip from the Solr facet of
                # resource formats, as it's not really a data resource
                pkg_dict['res_format'].remove('ZIP')
        except KeyError:
            # This happens when you save a new package without a resource yet
            pass
        return pkg_dict

    def before_resource_update(self, context, current, resource):
        # Allow sysadmin to update the Data Package
        user_obj = context.get('auth_user_obj')
        if user_obj and user_obj.sysadmin:
            return

        # Prevent user from updating the Data Package
        if 'datapackage_metadata_modified' in current:
            raise toolkit.ValidationError(
                {'message': toolkit._('Updating Data Package is not allowed')})

        return

    def before_resource_delete(self, context, resource, resources):
        # Allow sysadmin to delete the Data Package
        user_obj = context.get('auth_user_obj')
        if user_obj and user_obj.sysadmin:
            return

        # Prevent user from deleting the Data Package
        res_id_to_delete = resource.get('id')
        target_res = next(
            (r for r in resources if r.get('id') == res_id_to_delete),
            None
        )
        if target_res and 'datapackage_metadata_modified' in target_res:
            error_message = toolkit._('Deleting Data Package is not allowed')
            if context.get('api_version'):
                raise toolkit.ValidationError({'message': error_message})
            else:
                # Display the error page for the Web UI
                toolkit.abort(409, detail=error_message)

        return

    def get_helpers(self):
        return {
            'pop_datapackage_zip_res': helpers.pop_datapackage_zip_res,
        }

    def i18n_directory(self):
        return os.path.join(os.path.dirname(str(__file__)), '../i18n')


def update_datapackage(package_id):
    context = {
        'model': model,
        'session': model.Session,
        'ignore_auth': True
    }

    try:
        toolkit.get_action(
            'datapackage_update')(
            context,
            {'id': package_id}
        )
    except toolkit.ValidationError as e:
        error_message = e.error_dict.get('message', '')

        # Skip if the error occurs in background jobs
        if has_request_context():
            toolkit.h.flash_notice(error_message)

        log.debug(error_message)
        return
