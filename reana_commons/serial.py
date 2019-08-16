# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA Workflow Engine Serial implementation utils."""


import json
from copy import deepcopy
from string import Template

from jsonschema import ValidationError, validate

serial_workflow_schema = {
    "$schema": "http://json-schema.org/draft-06/schema#",
    "id": "serial_workflow_specification",
    "type": "object",
    "required": ["steps"],
    "properties": {
        "steps": {
            "$id": "#/properties/steps",
            "type": "array",
            "minItems": 1,
            "items": {
                "$id": "#/properties/steps/items",
                "type": "object",
                "required": [
                    "commands"
                ],
                "properties": {
                    "name": {
                        "$id": "#/properties/steps/properties/environment",
                        "type": "string",
                    },
                    "environment": {
                        "$id": "#/properties/steps/properties/environment",
                        "type": "string",
                    },
                    "compute_backend": {
                        "$id": "#/properties/steps/properties/compute_backend",
                        "type": "string",
                        "enum": ["kubernetes", "htcondorcern"],
                    },
                    "kerberos": {
                        "$id": "#/properties/steps/properties/kerberos",
                        "type": "boolean",
                        "default": "false",
                    },
                    "commands": {
                        "$id": "#/properties/steps/properties/commands",
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "$id": "#/properties/steps/items/properties/"
                                "commands/items",
                            "type": "string"
                        },
                    }
                }
            }
        }
    }
}


def serial_load(workflow_file, specification, parameters=None, original=None):
    """Validate and return a expanded REANA Serial workflow specification.

    :param workflow_file: A specification file compliant with
        REANA Serial workflow specification.
    :returns: A dictionary which represents the valid Serial workflow with all
        parameters expanded.
    """
    parameters = parameters or {}

    if not specification:
        with open(workflow_file, 'r') as f:
            specification = json.loads(f.read())

    expanded_specification = _expand_parameters(specification,
                                                parameters,
                                                original)

    validate(specification, serial_workflow_schema)

    return expanded_specification


def _expand_parameters(specification, parameters, original=None):
    """Expand parameters inside comands for Serial workflow specifications.

    :param specification: Full valid Serial workflow specification.
    :param parameters: Parameters to be extended on a Serial specification.
    :param original: Flag which, determins type of specifications to return.
    :returns: If 'original' parameter is set, a copy of the specification
        whithout expanded parametrers will be returned. If 'original' is not
        set, a copy of the specification with expanded parameters (all $varname
        and ${varname} will be expanded with their value). Otherwise an error
        will be thrown if the parameters can not be expanded.
    :raises: jsonschema.ValidationError
    """
    expanded_specification = deepcopy(specification)

    try:
        for step_num, step in enumerate(expanded_specification['steps']):
            current_step = expanded_specification['steps'][step_num]
            for command_num, command in enumerate(step['commands']):
                current_step['commands'][command_num] = \
                    Template(command).substitute(parameters)
        # if call is done from client, original==True and original
        # specifications withtout applied parameters are returned.
        if original:
            return specification
        else:
            return expanded_specification
    except KeyError as e:
        raise ValidationError('Workflow parameter(s) could not '
                              'be expanded. Please take a look '
                              'to {params}'.format(params=str(e)))
