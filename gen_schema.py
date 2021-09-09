#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
   gen_schema.py
"""

import os
import argparse
import collections
import csv
import codecs

import benten_meta


def convert_type(data_type):

    # elastic  --> jsonschema
    d = {}
    d["string"]  = "string"
    d["keyword"] = "string"
    d["text"]    = "string"
    d["boolean"] = "boolean"  # not used
    d["integer"] = "integer"
    d["double"]  = "number"  # any numeric type (integers, floading point numbers)
    d["array"]   = "array"
    d["date"]    = "string"  # need to assign "date-time" in format field
    
    return d.get(data_type)

def get_parent_key_list(key, flag_flat_key=False):

    key_list = [key]
    while 1:
        x = max(key.rfind("@"),key.rfind("."))
        if flag_flat_key:
            x = key.rfind(".")
        key_base  = key[:x]        
        if x<0 or key_base == "":
            break
        key_list.append(key_base)
        key = key_base
        
    key_list.reverse()
    return key_list

def get_key_base_and_child(key, flag_flat_key=False):

    x = max(key.rfind("@"), key.rfind("."))
    if flag_flat_key:
        x = key.rfind(".")
        
    key_base  = "root"
    key_child = key[1:]
    if flag_flat_key:
        key_child = key
    if x>0:
        key_base  = key[:x]
        key_child = key[x+1:]

    return key_base, key_child
            

def get_items_from_csv(csv_list, flag_null_allowed=True):

    col_key       = 1
    col_data_type = 3
    col_desc_ja   = 4
    col_desc      = 5
    col_example   = 6
    col_enum      = 8
    col_local     = 9
    
    required = []

    vdict = collections.OrderedDict()
    
    for row in csv_list:

        # ... check key
        key = row.get("key")
        if key is None:
            continue
    
        each_dict = collections.OrderedDict()
        each_dict["$id"] = "key:{}".format(key)

        # ... check type
        data_type           = row.get("data_type")
        data_type_converted = convert_type(data_type)
        if data_type_converted is not None:

            if flag_null_allowed:
                if data_type_converted in ["array"]:
                    each_dict["type"] = data_type_converted
                else:
                    each_dict["oneOf"] = [{"type": data_type_converted},
                                          {"type": "null"}]
            else:
                each_dict["type"] = data_type_converted

            if data_type in ["keyword", "text"]:
                data_type = "string"
            each_dict["type_db"] = data_type
            if data_type == "date":
#              each_dict["format"] = "date-time"
              each_dict["pattern"] = "^\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])( ([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?)?$"
            
        # ... check description
        value_ja = row.get("description_ja")
        value    = row.get("description")
        if value_ja or value:
            if value_ja is None:
                value_ja = ""
            if value is None:
                value = ""
            description = "{}\n{}".format(value_ja,value)
            each_dict["description"] = description

        # ... add title
        each_dict["title"] = key

        # ... add items for array
        if data_type == "array":
            each_dict["items"] = collections.OrderedDict()
            each_dict["items"]["type"] = "object"
            each_dict["items"]["properties"] = collections.OrderedDict()
            
        # ... check examples  (not used for now)
        value = row.get("example")
        if value:
            each_dict["examples"] = [value]

        # ... check enum (not used for now)
        value = row.get("enum")
        if value:
            vsplit = value.split(",")
            enum_list = []
            for v in vsplit:
                enum_list.append(v.strip())
                
            if len(enum_list)>0:
                each_dict["enum"] = enum_list

        # ... check local (not used for now)
        value = row.get("local")
        if value is None or value.lower() != "primary":
            each_dict["tag"] = "local"
        else:
            each_dict["tag"] = "primary"
            
        if data_type == "array":
            each_dict["items"]["additionalProperties"] = False

            
        vdict[key] = each_dict

    return vdict

            
    
def get_items(items_dict, required_dict, flag_flat_key=False):

    items_all_dict = collections.OrderedDict()
    key_all_list   = list(items_dict.keys())    
    key_list       = list(items_dict.keys())

    for key in key_list:

        parent_key_list = get_parent_key_list(key,
                                              flag_flat_key=flag_flat_key)
        for parent_key in parent_key_list:
            
            key_base, key_child = get_key_base_and_child(parent_key,
                                                         flag_flat_key=flag_flat_key)


            data_type = items_dict.get(key_base,{}).get("type","object")
            if key_base not in key_all_list:
                key_all_list.append(key_base)
                each_dict = collections.OrderedDict()
                if key_base == "root":
                    each_dict["$schema"] = "http://json-schema.org/draft-07/schema"
                    each_dict["type"]  = "object"
                    each_dict["title"] = "FC BENTEN schema"
                    each_dict["description"] = "FC BENTEN schema comprises the entire JSON document."
                elif data_type == "object":
                    each_dict["$id"]  = "key:{}".format(key_base)
                    each_dict["type"] = "object"
                else:
                    raise Exception("illegal format for {}".format(key_base))

                each_dict["properties"] = collections.OrderedDict()
                each_dict["additionalProperties"] = False
                
                items_all_dict[key_base] = each_dict
                
            if data_type == "object":
                items_all_dict[key_base]["title"] = key_base                
                items_all_dict[key_base]["properties"][key_child] = {"$ref": "#/definitions/{}".format(parent_key)}
            elif data_type == "array":
                items_all_dict[key_base]["title"] = key_base
                items_all_dict[key_base]["items"]["properties"][key_child] = {"$ref": "#/definitions/{}".format(parent_key)}
            else:
                raise Exception("illegal format for {}".format(key_base))

            if key_base in required_dict.keys() and \
               "required" not in items_all_dict[key_base]:
                items_all_dict[key_base]["required"] = required_dict[key_base]
                    
                parent_key_base_list = get_parent_key_list(key_base,
                                                           flag_flat_key=flag_flat_key)
                for parent_key_base in parent_key_base_list:
                    if parent_key_base == "root":
                        continue
                    
                    key_base2, key_child2 = get_key_base_and_child(parent_key_base,
                                                                   flag_flat_key=flag_flat_key)
                    if "required" not in items_all_dict[key_base2]:
                        items_all_dict[key_base2]["required"] = []
                    if key_child2 not in items_all_dict[key_base2]["required"]:
                        items_all_dict[key_base2]["required"].extend([key_child2])
            
        items_all_dict[key] = items_dict[key]
        
    # ... delete items for array with no components
    key_list_array_with_no_items = []
    for key, value in items_all_dict.items():
        v_type = value.get("type")
        if v_type != "array":
            continue
        n_properties = len(list(value.get("items",{}).get("properties",{}).keys()))
        if n_properties == 0:
            key_list_array_with_no_items.append(key) 
            
    for key in key_list_array_with_no_items:
        del items_all_dict[key]["items"]
    
    return items_all_dict


def get_schema_csv(filename_input, flag_flat_key=False,
                   flag_null_allowed=False):

    def get_csv_list(filename_input,encoding="shift_jis"):

        csv_list = []
        column_list = ["key","data_type","description_ja","description","supplement"]

        with codecs.open(filename_input,"r", encoding) as f:
            header = next(csv.reader(f))
            reader = csv.reader(f)
            for row in reader:
                if len(row[0])<=2:
                    continue
                if len(row[0].strip()) == 0:
                    continue
                v = dict()
                for i, column in enumerate(column_list):
                    try:
                        v[column] = row[i].strip()
                    except:
                        pass
                csv_list.append(v)
        return csv_list

    items_dict = collections.OrderedDict()
    required_dict = collections.OrderedDict()

    try:
        csv_list   = get_csv_list(filename_input,encoding="utf-8")
    except:
        csv_list   = get_csv_list(filename_input,encoding="shift_jis")


    items_dict = get_items_from_csv(csv_list, flag_null_allowed=flag_null_allowed)

    items_all_dict = get_items(items_dict, required_dict,
                               flag_flat_key=flag_flat_key)

    root_dict = items_all_dict["root"]
    del items_all_dict["root"]

    schema_dict = root_dict
    schema_dict["definitions"] = items_all_dict

    return schema_dict


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='generate jsonschema from schema csv file') 
    parser.add_argument('schema_csv_filename', help='schema csv filename')
    parser.add_argument("--flag_null_allowed", "-n", action="store_const",
                        const=1, help="flag for null allowed for each metadata")

    args = parser.parse_args()

    flag_flat_key = False

    schema_csv_filename = args.schema_csv_filename
    flag_null_allowed   = args.flag_null_allowed

    benten_meta.log("... input csv: {}".format(schema_csv_filename))
    benten_meta.log("... flag_null_allowed: {}".format(flag_null_allowed))

    schema_dict = get_schema_csv(schema_csv_filename,
                                 flag_flat_key=flag_flat_key,
                                 flag_null_allowed=flag_null_allowed)

    output_dir = "./schema"
    os.makedirs(output_dir, exist_ok=True)

    filename_schema      = "{}/schema.json".format(output_dir)

    benten_meta.log("... output {}".format(filename_schema))
    benten_meta.dump_json(schema_dict, filename_schema)
    
