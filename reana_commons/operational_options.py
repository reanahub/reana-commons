# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2020 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA Workflow Operational Options implementation utils."""

import copy
import subprocess
import sys

import click

from reana_commons.errors import REANAValidationError

available_options = {
    "CACHE": {"serial": "CACHE"},
    "FROM": {"serial": "FROM"},
    "TARGET": {"serial": "TARGET", "cwl": "--target"},
    "toplevel": {"yadage": "toplevel"},
    "initdir": {"yadage": "initdir"},
    "initfiles": {"yadage": "initfiles"},
    "accept_metadir": {"yadage": "accept_metadir"},
    "report": {"snakemake": "report"},
}


def validate_operational_options(workflow_type, parsed_options):
    """Validate and return  workflow operational options.

    :param workflow_type: A supported workflow specification type.
    :param parsed_options: A dict with the parsed operational parameters.
    :returns: A dictionary which represents the valid workflow specification.
    """
    if not isinstance(parsed_options, dict):
        raise REANAValidationError(
            "==> ERROR: Operational options must be a dictionary."
        )
    elif not parsed_options:
        return parsed_options

    validated_options = copy.deepcopy(parsed_options)
    for option in parsed_options.keys():
        if option not in available_options:
            raise REANAValidationError(
                '==> ERROR: Operational option "{0}" not supported.'.format(option)
            )
        translation = available_options[option].get(workflow_type)
        if not translation:
            raise REANAValidationError(
                '==> ERROR: Operational option "{0}" not supported for'
                " {1} workflows.".format(option, workflow_type)
            )
        # Override engine specific options
        if translation not in available_options:
            validated_options[translation] = validated_options[option]
            del validated_options[option]

    return validated_options
