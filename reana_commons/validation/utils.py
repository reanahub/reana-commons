# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons validation utilities."""

import json
import logging
import os
from typing import Dict, List

from jsonschema import ValidationError, validate

from reana_commons.config import (
    REANA_WORKFLOW_NAME_ILLEGAL_CHARACTERS,
    WORKSPACE_PATHS,
    reana_yaml_schema_file_path,
)
from reana_commons.errors import REANAValidationError


def validate_reana_yaml(reana_yaml: Dict) -> None:
    """Validate REANA specification file according to jsonschema.

    :param reana_yaml: Dictionary which represents REANA specification file.
    :raises ValidationError: Given REANA spec file does not validate against
        REANA specification schema.
    """
    try:
        with open(reana_yaml_schema_file_path, "r") as f:
            reana_yaml_schema = json.loads(f.read())
            validate(reana_yaml, reana_yaml_schema)
    except IOError as e:
        logging.info(
            "Something went wrong when reading REANA validation schema from "
            "{filepath} : \n"
            "{error}".format(filepath=reana_yaml_schema_file_path, error=e.strerror)
        )
        raise e
    except ValidationError as e:
        logging.info("Invalid REANA specification: {error}".format(error=e.message))
        raise e


def validate_workflow_name(workflow_name: str) -> str:
    """Validate workflow name."""
    if workflow_name:
        for item in REANA_WORKFLOW_NAME_ILLEGAL_CHARACTERS:
            if item in workflow_name:
                raise ValueError(
                    f'Workflow name {workflow_name} contains illegal character "{item}"'
                )
    return workflow_name


def validate_workspace(
    workspace_option: str, available_paths: List[str] = list(WORKSPACE_PATHS.values())
) -> str:
    """Validate and return workspace.

    :param workspace_option: A string of the workspace to validate.
    :type workspace_option: string
    :param available_paths: A list of the available workspaces.
    :type available_paths: list
    :returns: A string of the validated workspace.
    """
    if workspace_option:
        available = any(
            os.path.join(os.path.abspath(workspace_option), "").startswith(
                os.path.join(os.path.abspath(path), "")
            )
            for path in available_paths
        )
        if not available:
            raise REANAValidationError(
                f'Desired workspace "{workspace_option}" is not valid.\n'
                f'Available workspace prefix values are: {", ".join(available_paths)}',
            )
    return workspace_option
