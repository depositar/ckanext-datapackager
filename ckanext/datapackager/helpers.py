def pop_datapackage_zip_res(pkg):
    '''Finds the Data Package zip resource in a package's resources, removes it
    from the package and returns it. NB the package doesn't have the zip
    resource in it any more.
    '''
    dp_zip_res = None
    non_dp_zip_res = []

    for res in pkg.get('resources', []):
        if res.get('datapackage_metadata_modified'):
            dp_zip_res = res
        else:
            non_dp_zip_res.append(res)

    pkg['resources'] = non_dp_zip_res

    return dp_zip_res
