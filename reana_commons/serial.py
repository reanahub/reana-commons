# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2020, 2021, 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA Workflow Engine Serial implementation utils."""

import json
from copy import deepcopy
from string import Template

import click
from jsonschema import ValidationError, validate

from reana_commons.config import (
    HTCONDOR_JOB_FLAVOURS,
    KUBERNETES_MEMORY_FORMAT,
)

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
                "required": ["commands"],
                "properties": {
                    "name": {
                        "$id": "#/properties/steps/properties/environment",
                        "type": "string",
                    },
                    "environment": {
                        "$id": "#/properties/steps/properties/environment",
                        "type": "string",
                    },
                    "unpacked_image": {
                        "$id": "#/properties/steps/properties/unpacked_image",
                        "type": "boolean",
                        "default": "false",
                    },
                    "compute_backend": {
                        "$id": "#/properties/steps/properties/compute_backend",
                        "type": "string",
                        "enum": ["kubernetes", "htcondorcern", "slurmcern"],
                    },
                    "kerberos": {
                        "$id": "#/properties/steps/properties/kerberos",
                        "type": "boolean",
                        "default": "false",
                    },
                    "kubernetes_uid": {
                        "$id": "#/properties/steps/properties/kubernetes_uid",
                        "type": "integer",
                        "default": "None",
                    },
                    "kubernetes_memory_limit": {
                        "$id": "#/properties/steps/properties/kubernetes_memory_limit",
                        "type": "string",
                        "default": "",
                        "pattern": KUBERNETES_MEMORY_FORMAT,
                    },
                    "voms_proxy": {
                        "$id": "#/properties/steps/properties/voms_proxy",
                        "type": "boolean",
                        "default": "false",
                    },
                    "rucio": {
                        "$id": "#/properties/steps/properties/rucio",
                        "type": "boolean",
                        "default": "false",
                    },
                    "htcondor_max_runtime": {
                        "$id": "#/properties/steps/properties/htcondor_max_runtime",
                        "type": "string",
                        "default": "",
                    },
                    "htcondor_accounting_group": {
                        "$id": "#/properties/steps/properties/htcondor_accounting_group",
                        "type": "string",
                        "default": "",
                    },
                    "slurm_partition": {
                        "$id": "#/properties/steps/properties/slurm_partition",
                        "type": "string",
                        "default": "",
                    },
                    "slurm_time": {
                        "$id": "#/properties/steps/properties/slurm_time",
                        "type": "string",
                        "default": "",
                    },
                    "commands": {
                        "$id": "#/properties/steps/properties/commands",
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "$id": "#/properties/steps/items/properties/"
                            "commands/items",
                            "type": "string",
                        },
                    },
                },
            },
        }
    },
}


def serial_load(workflow_file, specification, parameters=None, original=None, **kwargs):
    """Validate and return a expanded REANA Serial workflow specification.

    :param workflow_file: A specification file compliant with
        REANA Serial workflow specification.
    :returns: A dictionary which represents the valid Serial workflow with all
        parameters expanded.
    """
    if not check_htcondor_max_runtime(specification):
        raise Exception("Invalid input in htcondor_max_runtime.")

    parameters = parameters or {}

    if not specification:
        with open(workflow_file, "r") as f:
            specification = json.loads(f.read())

    expanded_specification = _expand_parameters(specification, parameters, original)

    validate(specification, serial_workflow_schema)

    return expanded_specification


def _expand_parameters(specification, parameters, original=None):
    """Expand parameters inside commands for Serial workflow specifications.

    :param specification: Full valid Serial workflow specification.
    :param parameters: Parameters to be extended on a Serial specification.
    :param original: Flag which, determines type of specifications to return.
    :returns: If 'original' parameter is set, a copy of the specification
        whithout expanded parametrers will be returned. If 'original' is not
        set, a copy of the specification with expanded parameters (all $varname
        and ${varname} will be expanded with their value). Otherwise an error
        will be thrown if the parameters can not be expanded.
    :raises: jsonschema.ValidationError
    """
    # if call is done from client, original==True and original
    # specifications withtout applied parameters are returned.
    if original:
        return specification
    else:
        try:
            expanded_specification = deepcopy(specification)
            for step_num, step in enumerate(expanded_specification["steps"]):
                current_step = expanded_specification["steps"][step_num]
                for command_num, command in enumerate(step["commands"]):
                    current_step["commands"][command_num] = Template(
                        command
                    ).substitute(parameters)
            return expanded_specification
        except KeyError as e:
            raise ValidationError(
                "Workflow parameter(s) could not "
                "be expanded. Please take a look "
                "to {params}".format(params=str(e))
            )


def check_htcondor_max_runtime(specification):
    """Check if the field htcondor_max_runtime has a valid input.

    :param reana_specification: reana specification of workflow.
    """
    check_pass = True
    steps_with_max_runtime = (
        step
        for step in specification["steps"]
        if step.get("htcondor_max_runtime", False)
    )
    for i, step in enumerate(steps_with_max_runtime):
        htcondor_max_runtime = step["htcondor_max_runtime"]
        if (
            not str.isdigit(htcondor_max_runtime)
            and htcondor_max_runtime not in HTCONDOR_JOB_FLAVOURS
        ):
            check_pass = False
            click.secho(
                "In step {0}:\n'{1}' is not a valid input for htcondor_max_runtime. Inputs must be a digit in the form of a string, or one of the following job flavours: '{2}'.".format(
                    step.get("name", i),
                    htcondor_max_runtime,
                    "' '".join(
                        [
                            k
                            for k, v in sorted(
                                HTCONDOR_JOB_FLAVOURS.items(), key=lambda key: key[1]
                            )
                        ]
                    ),
                ),
                fg="red",
            )
    return check_pass
