[![Tests](https://github.com/frictionlessdata/ckanext-datapackager/actions/workflows/test.yml/badge.svg)](https://github.com/frictionlessdata/ckanext-datapackager/actions/workflows/test.yml)
[![Coverage Status](https://coveralls.io/repos/github/frictionlessdata/ckanext-datapackager/badge.svg?branch=master)](https://coveralls.io/github/frictionlessdata/ckanext-datapackager?branch=master)

# CKAN Data Packager

This extension adds importing and exporting of [Data Packages][data-packages] to [CKAN][ckan] datasets.

## Requirements

* CKAN >= 2.10

## Installing

To install `ckanext-datapackager` into a CKAN instance, do:

1. If you're using a virtual environment for CKAN, activate it doing, for example:

        source /usr/lib/ckan/default/bin/activate

2. Install the extension:

        git clone https://github.com/frictionlessdata/ckanext-datapackager.git
        cd ckanext-datapackager
        python setup.py develop
        pip install -r requirements.txt


3. Add `datapackager` to the `ckan.plugins` setting in your CKAN config file;
4. Restart CKAN.

## Using

### Web Interface

#### Importing

![Importing Data Package](doc/images/ckanext-datapackager-import-demo.gif)

1. Visit the Dataset list page (e.g. `http://your-ckan-address.com/dataset`)
2. Click on `Import Data Package` button;
3. Upload or link to a Data Package JSON or ZIP file;
  * Depending on your CKAN configuration, you might also need to define
    the dataset's organization and visibility here.
4. Review the created dataset.

#### Exporting

![Exporting CKAN Dataset as Data Package](doc/images/ckanext-datapackager-export-link.png)

1. Go to the dataset's page;
2. Click on `Download Data Package` button.

### Automatic Data Package Generation

When a dataset is created or edited, and the total size of the resources
in the dataset is 10 MB
(this can be configured via `ckanext.datapackager.max_dataset_size` config)
or less, a Data Package will be generated
automatically and uploaded as a resource for the dataset:

* The Data Package file is named `datapackage.zip`.
* The Data Package resource is NOT LISTED in the resource list
  on the dataset page and the edit dataset page.
* The Data Package resource is LISTED in the API results.
  You need to exclude the Data Package resource when calculating
  the resource count via the API.
* The Data Package resource only includes data files uploaded to CKAN.
  External URLs will only be listed in the `datapackage.json`
  and any resource without a URL will not be included.
* The Data Package resource will not be updated
  (and the existing one will be deleted) if the dataset’s total resource size
  exceeds 10 MB after editing, or if all resources lack a URL.
* Automatic Data Package generation is a background task.
  If the `Download Data Package` button does not appear,
  please ensure the above conditions are met and refresh the dataset page.

### API


The extension provides three API actions for importing (`package_create_from_datapackage`), exporting (`package_show_as_datapackage`) and updating (`datapackage_update`) Data Packages on CKAN.

For more information on their parameters and return values, check the
docstrings inside the files at
[ckanext/datapackager/logic/action](ckanext/datapackager/logic/action).





#### Importing

If the Data Package (either the `datapackage.json` file or a zip file with the `datapackage.json` and the data files) is reachable through an URL, you can do a request to `package_create_from_datapackage` as such:

```
curl -X POST \
     -H 'Authorization: YOUR_CKAN_API_KEY' \
     -d '{"url": "https://link.to/datapackage.json"}' \
     http://CKAN_HOST/api/action/package_create_from_datapackage
```

You can also use [ckanapi][ckanapi]:

    ckanapi action package_create_from_datapackage url=URL_TO_DATAPACKAGE owner_org=OWNER_ORGANIZATION_ID -r http://CKAN_HOST

For uploading the Data Package, check the documentation on uploading files using [ckanapi](https://github.com/ckan/ckanapi#file-uploads) or check this example using [requests](http://docs.python-requests.org/en/latest/):

```python
import requests

r = requests.post('http://CKAN_HOST/api/action/package_create_from_datapackage',
                   headers={'Authorization': YOUR_CKAN_API_KEY},
                   files=[('upload', file('/path/to/datapackage.json/or/file.zip'))])


```

#### Exporting

For exporting a dataset as a `datapackage.json` just call `package_show_as_datapackage` with the relevant dataset id:

    curl 'http://CKAN_HOST/api/action/package_show_as_datapackage?id=940a5fe0-0c72-41c4-8a28-8c794f399036'

    {"help": "http://CKAN_HOST/api/3/action/help_show?name=package_show_as_datapackage",
     "success": true,
     "result": {
        "name": "bond-yields-uk-2-7334836228",
        "title": "Test Data Package",
        "resources": [
            {"url": "http://some.file",
             "format": "CSV"}
        ]
      }
    }

Or if using ckanapi:

    ckanapi action package_show_as_datapackage id=PACKAGE_ID -r http://CKAN_URL

Note that this returns the standard CKAN API output where the `datapackage.json` file is returned under the `result` key.
If you would rather like to get the `datapackage.json` file directly you can use this direct endpoint:

    http://CKAN_HOST/dataset/DATASET_NAME_OR_ID/datapackage.json

For instance

    curl http://CKAN_HOST/dataset/bond-yields-uk-10y/datapackage.json


#### Updating

For updating the Data Package for a dataset:

```
curl -X POST \
     -H 'Authorization: YOUR_CKAN_API_KEY' \
     -d '{"id": "DATASET_NAME_OR_ID"}' \
     http://CKAN_HOST/api/action/datapackage_update
```

Or if using ckanapi:

    ckanapi action datapackage_update id=DATASET_NAME_OR_ID -r http://CKAN_HOST


## Developing ckanext-datapackager

### Running tests

You'll need to install the dev requirements to run the tests:

To run the tests, do:

    pytest --ckan-ini=test.ini ckanext/datapackager/tests

Note that ckanext-datapackager's `test.ini` file assumes that the relative path from it
to CKAN's `test-core.ini` file is `../ckan/test-core.ini`, i.e. that you have
CKAN and ckanext-datapackager installed next to each other in the same directory. This
would normally be the case if you've done development installs of CKAN and
ckanext-datapackager.

## Where is the old Open Knowledge's Data Packager?

The [Open Knowledge Data Packager](http://datapackager.okfn.org) was written for
an old CKAN version (2.2), and is now deprecated. This extension implements
parts of its functionality and improves them, supporting the current CKAN
version (2.4).

If you still need the old Data Packager, checkout this repository's commit
[57cff1f](https://github.com/frictionlessdata/ckanext-datapackager/commit/57cff1f5112504091891195a097433579275f968).

[ckan]: http://ckan.org
[data-packages]: https://datapackage.org/
[ckanapi]: https://github.com/ckan/ckanapi
