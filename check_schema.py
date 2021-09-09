#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
   check_schema.py
"""

import json
import argparse
import collections
import jsonschema
import urllib

import benten_meta

def check_schema(metadata_yaml_filename, schema_path):

    def is_url(text) :
        url_param = urllib.parse.urlparse(text)
        return len(url_param.scheme) > 0

    schema = dict()
    if is_url(schema_path):
        try:
            with urllib.request.urlopen(schema_path) as f:
                schema  = json.load(f)
        except urllib.error.URLError as e:
            raise benten_meta.Error(e)
    else:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)

    benten_meta.log("... get schema from {}".format(schema_path))

       
    error_dict = collections.OrderedDict()
    error_dict["error"]   = "Invalid metadata schema"
    error_dict["details"] = collections.OrderedDict()

    for metadata_file in  [metadata_yaml_filename]:

        # ... validation check
        schema_used = schema
        
        obj = benten_meta.load_yaml(metadata_file)

        validator = jsonschema.Draft7Validator(schema_used)
        validation_errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
            
        errors = []

        for error in validation_errors:
            message = error.message
            if error.path:
                message = "[{}] {}".format(
                    ".".join(str(x) for x in error.absolute_path), message
                )
                errors.append(message)

        status = "OK"
        if len(errors)>0:
            status = "NG"
            error_dict["details"][metadata_file] = errors

        benten_meta.log("... check {}: {}".format(metadata_file, status))


    error_list = list(error_dict["details"].keys())
    if len(error_list)>0:
        message = json.dumps(error_dict, indent=4)
        benten_meta.Error(message)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='check chema for metadata with yaml') 
    parser.add_argument('metadata_yaml_filename', help='metadata yaml filename')

    args = parser.parse_args()
    metadata_yaml_filename = args.metadata_yaml_filename

    config_dict = benten_meta.load_yaml("config.yml")
    schema_path = config_dict.get("schema_path", "./schema/schema.json")

    benten_meta.log("... input metadata: {}".format(metadata_yaml_filename))
    benten_meta.log("... schema path: {}".format(schema_path))

    check_schema(metadata_yaml_filename, schema_path)
