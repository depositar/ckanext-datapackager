# -*- coding: utf-8 -*-

import unittest
import responses

import frictionless

from dplib.models import Package
from dplib.plugins.ckan.models import CkanPackage

class TestConvertToDict(unittest.TestCase, object):
    def setUp(self):
        self.resource_dict = {
            "id": "1234",
            "name": "data.csv",
            "url": "http://someplace.com/data.csv",
        }
        self.dataset_dict = {
            "name": "gdp",
            "title": "Countries GDP",
            "version": "1.0",
            "resources": [self.resource_dict],
            "license_id": "",
            "license_title": ""
        }

    def test_basic_dataset_in_setup_is_valid(self):
        CkanPackage.from_dict(self.dataset_dict).to_dp()

    def test_dataset_name_title_and_version(self):
        self.dataset_dict.update(
            {
                "name": "gdp",
                "title": "Countries GDP",
                "version": "1.0",
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        assert result["title"] == self.dataset_dict["title"]
        assert result["name"] == self.dataset_dict["name"]
        assert result["version"] == self.dataset_dict["version"]

    def test_dataset_notes(self):
        self.dataset_dict.update(
            {"notes": "Country, regional and world GDP in current US Dollars."}
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        assert result.get("description") == self.dataset_dict["notes"]

    def test_dataset_license(self):
        license = {
            "name": "cc-zero",
            "title": "Creative Commons CC Zero License (cc-zero)",
            "path": "http://opendefinition.org/licenses/cc-zero/",
        }
        self.dataset_dict.update(
            {
                "license_id": license["name"],
                "license_title": license["title"],
                "license_url": license["path"],
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        assert result.get("licenses")[0] == license

    def test_dataset_maintainer(self):
        author = {"title": "John Smith", "email": "jsmith@email.com", "roles": ["maintainer"]}
        self.dataset_dict.update(
            {
                "maintainer": author["title"],
                "maintainer_email": author["email"],
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        assert result.get("contributors")[0] == author

    def test_dataset_tags(self):
        keywords = ["economy", "worldbank"]
        self.dataset_dict.update(
            {
                "tags": [
                    {
                        "display_name": "economy",
                        "id": "9d602a79-7742-44a7-9029-50b9eca38c90",
                        "name": "economy",
                        "state": "active",
                    },
                    {
                        "display_name": "worldbank",
                        "id": "3ccc2e3b-f875-49ef-a39d-6601d6c0ef76",
                        "name": "worldbank",
                        "state": "active",
                    },
                ]
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        assert result.get("keywords") == keywords

    def test_resource_url(self):
        self.resource_dict.update(
            {
                "url": "http://www.somewhere.com/data.csv",
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        resource = result.get("resources")[0]
        assert resource.get("path") == self.resource_dict["url"]

    def test_resource_path_is_set_even_for_uploaded_resources(self):
        self.resource_dict.update(
            {
                "id": "foo",
                "url": "http://www.somewhere.com/data.csv",
                "url_type": "upload",
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        resource = result.get("resources")[0]
        assert resource.get("path") == self.resource_dict["url"]

    def test_resource_description(self):
        self.resource_dict.update(
            {
                "description": "GDPs list",
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        resource = result.get("resources")[0]
        assert resource.get("description") == self.resource_dict["description"]

    def test_resource_format(self):
        self.resource_dict.update(
            {
                "format": "csv",
            }
        )
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        resource = result.get("resources")[0]
        assert resource.get("format") == self.resource_dict["format"]

    def test_resource_name_lowercases_the_name(self):
        self.resource_dict.update(
            {
                "name": "ThE-nAmE",
            }
        )
        expected_name = "the_name"
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        resource = result.get("resources")[0]
        assert resource.get("name") == expected_name

    def test_resource_name_slugifies_the_name(self):
        self.resource_dict.update(
            {
                "name": u"Lista de PIBs dos países!   51",
            }
        )
        expected_name = "lista_de_pibs_dos_paises_51"
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        resource = result.get("resources")[0]
        assert resource.get("name") == expected_name

    def test_resource_name_converts_unicode_characters(self):
        self.resource_dict.update(
            {
                "name": u"万事开头难",
            }
        )
        expected_name = "mo_shi_kai_tou_nan"
        result = CkanPackage.from_dict(self.dataset_dict).to_dp().to_dict()
        resource = result.get("resources")[0]
        assert resource.get("name") == expected_name


class TestDataPackageToDatasetDict(unittest.TestCase, object):
    def setUp(self):
        datapackage_dict = {
            "name": "gdp",
            "title": "Countries GDP",
            "version": "1.0",
            "resources": [{"name": "datetimes.csv", "path": "test-data/datetimes.csv"}],
        }

        self.datapackage = CkanPackage.from_dp(
            Package.from_dict(datapackage_dict)).to_dict()

    def test_basic_datapackage_in_setup_is_valid(self):
        CkanPackage.from_dp(Package.from_dict(self.datapackage)).to_dict()

    def test_datapackage_only_requires_some_fields_to_be_valid(self):
        valid_datapackage = frictionless.Package(
            {
                "name": "gdp",
                "resources": [
                    {"name": "the-resource", "path": "http://example.com/some-data.csv"}
                ],
            }
        )

        CkanPackage.from_dp(Package.from_dict(
            valid_datapackage.to_dict())).to_dict()

    def test_datapackage_name_title_and_version(self):
        self.datapackage.update(
            {
                "name": "gdp",
                "title": "Countries GDP",
                "version": "1.0",
            }
        )
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        datapackage_dict = self.datapackage
        assert result["name"] == datapackage_dict["name"]
        assert result["title"] == datapackage_dict["title"]
        assert result["version"] == datapackage_dict["version"]

    def test_datapackage_description(self):
        self.datapackage.update(
            {"description": "Country, regional and world GDP in current USD."}
        )
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        assert result.get("notes") == self.datapackage["description"]

    def test_datapackage_licenses(self):
        license = {
            "name": "cc-zero",
            "title": "Creative Commons CC Zero License (cc-zero)",
            "path": "http://opendefinition.org/licenses/cc-zero/",
        }
        self.datapackage.update({"licenses": [license]})
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        assert result.get("license_id") == license["name"]
        assert result.get("license_title") == license["title"]
        assert result.get("license_url") == license["path"]

    # TODO: Check how author email is written in CKAN
    def test_datapackage_author_as_string(self):
        author = {"name": "John Smith", "email": "jsmith@email.com"}
        self.datapackage.update({
            'contributors': [{
                "title": author["name"],
                "email": author["email"],
                "role": "author"
            }]
        })
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()

        assert result.get("author") == author["name"]
        assert result.get("author_email") == author["email"]

    def test_datapackage_author_as_dict(self):
        author = {"title": "John Smith", "email": "jsmith@email.com", "role": "author"}
        self.datapackage.update({
            "contributors": [author]
        })
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        assert result.get("author") == author["title"]
        assert result.get("author_email") == author["email"]

    # TODO: Check if the tag convertion to CKAN is valid
    def test_datapackage_keywords(self):
        keywords = [
            "economy!!!",
            "world bank",
        ]
        self.datapackage.update({"keywords": keywords})
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        result_tags = [ t["name"] for t in result.get("tags") ]
        assert "economy!!!" in result_tags
        assert "world bank" in result_tags

    def test_resource_name_is_used_if_theres_no_title(self):
        resource = {
            "name": "gdp",
            "title": None,
        }
        self.datapackage['resources'][0].update(resource)
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        resource = result.get("resources")[0]
        assert result.get("resources")[0].get("name") == resource["name"]

    @responses.activate
    def test_resource_url(self):
        url = "http://www.somewhere.com/data.csv"
        datapackage_dict = {
            "name": "gdp",
            "title": "Countries GDP",
            "version": "1.0",
            "resources": [{"name": "gdp", "path": url}],
        }
        responses.add(responses.GET, url, body='')

        dp = frictionless.Package(datapackage_dict).to_dict()
        result = CkanPackage.from_dp(Package.from_dict(dp)).to_dict()
        assert (
            result.get("resources")[0].get("url")
            == datapackage_dict["resources"][0]["path"]
        )

    @responses.activate
    def test_resource_url_is_set_to_its_remote_data_path(self):
        url = "http://www.somewhere.com/data.csv"
        datapackage_dict = {
            "name": "gdp",
            "title": "Countries GDP",
            "version": "1.0",
            "resources": [{"name": "gdp", "path": "data.csv"}],
        }
        responses.add(responses.GET, url, body="")
        dp = frictionless.Package(
            datapackage_dict, basepath="http://www.somewhere.com"
        ).to_dict()
        result = CkanPackage.from_dp(Package.from_dict(dp)).to_dict()
        assert result.get("resources")[0].get("url") == dp['resources'][0]['path']

    def test_resource_description(self):
        resource = {"description": "GDPs list"}

        self.datapackage['resources'][0].update(resource)
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        assert result.get("resources")[0].get("description") == resource["description"]

    def test_resource_format(self):
        resource = {
            "format": "CSV",
        }

        self.datapackage['resources'][0].update(resource)
        result = CkanPackage.from_dp(Package.from_dict(
            self.datapackage)).to_dict()
        assert result.get("resources")[0].get("format") == resource["format"]

    def test_resource_path_is_set_to_its_local_data_path(self):
        resource = {
            "name": "datetimes",
            "path": "test-data/datetimes.csv",
        }
        dp = frictionless.Package(
            {
                "name": "datetimes",
                "resources": [resource],
            }
        ).to_dict()

        result = CkanPackage.from_dp(Package.from_dict(dp)).to_dict()
        assert result.get("resources")[0].get("url") == dp['resources'][0]['path']
