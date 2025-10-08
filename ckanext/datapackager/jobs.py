from datetime import datetime
import json
import os
import tempfile
from urllib.parse import urlparse
import zipfile

import ckanapi
import requests

from ckanext.datapackager.lib import util


log = __import__('logging').getLogger(__name__)


class DownloadError(Exception):
    pass


def update_zip(dataset, datapackage, existing_zip_resource):
    ckan_and_datapackage_resources = list(zip(dataset['resources'],
                                          datapackage['resources']))

    hash_in_datapackage_and_resources = \
        util.get_hash_in_datapackage_and_resources(
            datapackage, dataset['resources'])

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, 'datapackage.zip')

        _write_zip(zip_path, datapackage, ckan_and_datapackage_resources)

        # Upload the resource to CKAN as a new/updated resource
        local_ckan = ckanapi.LocalCKAN()

        with open(zip_path, 'rb') as f:
            resource = dict(
                package_id=dataset['id'],
                url='dummy-value',
                upload=f,
                name='Data Package',
                format='ZIP',
                datapackage_metadata_modified=dataset['metadata_modified'],
                datapackage_hash=hash_in_datapackage_and_resources
            )

            if not existing_zip_resource:
                log.debug('Writing new zip resource - {}'
                          .format(dataset['name']))
                local_ckan.action.resource_create(**resource)
            else:
                log.debug('Updating zip resource - {}'.format(dataset['name']))
                local_ckan.action.resource_patch(
                    id=existing_zip_resource['id'],
                    **resource)


def delete_zip(dataset, existing_zip_resource):
    local_ckan = ckanapi.LocalCKAN()

    log.debug('Deleting zip resource - {}'.format(dataset['name']))
    local_ckan.action.resource_delete(id=existing_zip_resource['id'])


def _write_zip(fp, datapackage, ckan_and_datapackage_resources):
    with zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) \
            as zipf:
        i = 0
        for res, dres in ckan_and_datapackage_resources:
            i += 1

            # Only include resources uploaded to the CKAN site
            if res['url_type'] != 'upload':
                log.debug('Resource {}/{} skipped - is not uploaded to '
                          'this site'
                          .format(i, len(ckan_and_datapackage_resources)))
                continue

            log.debug('Downloading resource {}/{}: {}'
                      .format(i, len(ckan_and_datapackage_resources),
                              res['url']))
            filename = os.path.basename(urlparse(res['url']).path)
            try:
                _download_resource_into_zip(res['url'], filename, zipf)
            except DownloadError:
                continue

            # Save path in datapackage.json - i.e. now pointing at the file
            # bundled in the Data Package zip
            dres['path'] = filename

        # Add the datapackage.json
        _write_datapackage_json(datapackage, zipf)

    log.info('Zip created')


def _download_resource_into_zip(url, filename, zipf):
    # If the site_url differs from this url, rewrite this url to the
    # site_url. This can be useful if CKAN is behind a firewall.
    site_url = util.get_site_url()
    if site_url and not url.startswith(site_url):
        new_url = urlparse(url)
        rewrite_url = urlparse(site_url)
        new_url = new_url._replace(
            scheme=rewrite_url.scheme,
            netloc=rewrite_url.netloc)
        url = new_url.geturl()
        log.info('Rewrote resource url to: {0}'.format(url))

    try:
        headers = {'Authorization': util.get_api_token()}
        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', 'N/A')
        log.error('URL {url} download failed: {error_class}, \
                  status={status}, error={error}'
                  .format(url=url,
                          error_class=e.__class__.__name__,
                          status=status,
                          error=str(e)))
        raise DownloadError()

    zip_info = zipfile.ZipInfo(filename)
    zip_info.date_time = datetime.now().timetuple()[:6]

    with zipf.open(zip_info, 'w') as zf:
        for chunk in r.iter_content(chunk_size=128):
            zf.write(chunk)

    log.debug('URL {url} is downloaded'.format(url=url))


def _write_datapackage_json(datapackage, zipf):
    with tempfile.NamedTemporaryFile('w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(datapackage, ensure_ascii=False))
        json_file.flush()
        zipf.write(json_file.name, arcname='datapackage.json')
        log.debug('Added datapackage.json from {}'.format(json_file.name))
