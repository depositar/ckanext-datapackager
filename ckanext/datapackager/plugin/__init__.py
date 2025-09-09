import datetime
import os

from ckan import model
from ckan.lib.plugins import DefaultTranslation
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint

from ckanext.datapackager import helpers
from ckanext.datapackager.controllers import datapackage
from ckanext.datapackager.logic.action.create import package_create_from_datapackage
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
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)

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
        log.debug(e.error_dict.get('message', ''))
        return
