from ckan import model
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from flask import has_request_context
from flask import session

from ckanext.datapackager import helpers
from ckanext.datapackager.controllers import datapackage
from ckanext.datapackager.logic.action.create import package_create_from_datapackage
from ckanext.datapackager.logic.action.get import package_show_as_datapackage
from ckanext.datapackager.logic.action.update import datapackage_update


class DataPackagerPlugin(plugins.SingletonPlugin):
    '''Plugin that adds importing/exporting datasets as Data Packages.
    '''
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    def update_config(self, config):
        toolkit.add_template_directory(config, '../templates')

    def get_actions(self):
        return {
            'package_create_from_datapackage': package_create_from_datapackage,
            'package_show_as_datapackage': package_show_as_datapackage,
            'datapackage_update': datapackage_update,
        }

    def get_blueprint(self):
        blueprint = Blueprint("datapackager", __name__)
        # As long as the URL for import_datapackage_view and import_datapackage are the same, reverse lookups from import_datapackage will work
        blueprint.add_url_rule(
            "/import_datapackage",
            view_func=datapackage.new,
            endpoint="import_datapackage",
            methods=["GET"],
        )
        blueprint.add_url_rule(
            "/import_datapackage",
            view_func=datapackage.import_datapackage,
            endpoint="import_datapackage_post",
            methods=["POST"],
        )
        blueprint.add_url_rule(
            "/dataset/<package_id>/datapackage.json",
            view_func=datapackage.export_datapackage,
            endpoint="export_datapackage",
            methods=["GET"],
        )
        return blueprint

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
        if _is_sysadmin(context):
            return

        # Prevent user from updating the Data Package
        if 'datapackage_metadata_modified' in current:
            raise toolkit.ValidationError(
                {'message': [toolkit._('Updating Data Package is not allowed')]})

        return

    def before_resource_delete(self, context, resource, resources):
        # Allow sysadmin to delete the Data Package
        if _is_sysadmin(context):
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
                raise toolkit.ValidationError({'message': [error_message]})
            else:
                # Display the error page for the Web UI
                toolkit.abort(409, detail=error_message)

        return

    def after_dataset_update(self, context, pkg_dict):
        if (pkg_dict.get('state') == 'draft'):
            return
        _update_datapackage(pkg_dict.get('id'), context)

    def get_helpers(self):
        return {
            'pop_datapackage_zip_res': helpers.pop_datapackage_zip_res,
        }


def _is_sysadmin(context):
    try:
        toolkit.check_access('sysadmin', context, {})
        return True
    except toolkit.NotAuthorized:
        return False


def _update_datapackage(package_id, context):
    # Skip redundant hook-triggered updates
    if context.get('dp_upload_local') or context.get('dp_update_processed'):
        return

    context['dp_update_processed'] = True

    try:
        toolkit.get_action(
            'datapackage_update')(
            {'model': model, 'session': model.Session, 'ignore_auth': True},
            {'id': package_id}
        )
    except toolkit.ValidationError as e:
        error_message = e.error_dict.get('message', '')

        if has_request_context() and session:
            toolkit.h.flash_notice(error_message)

        return
