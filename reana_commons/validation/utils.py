# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons validation utilities."""

import json
import logging
import os
import re
from collections import deque
from typing import Dict, List

from jsonschema import ValidationError
from jsonschema.exceptions import best_match, ErrorTree
from jsonschema.validators import validator_for

from reana_commons.config import (
    REANA_WORKFLOW_NAME_ILLEGAL_CHARACTERS,
    WORKSPACE_PATHS,
    reana_yaml_schema_file_path,
)
from reana_commons.errors import REANAValidationError


def _get_schema_validation_warnings(errors: List[ValidationError]) -> Dict:
    """Parse a list of JSON schema validation errors.

    When validating the REANA specification file against the REANA specification
    schema, the validator can return many ValidationError object. This function parses
    the list of errors and returns a dictionary of warnings, in the form of
    {warning_key: [warning_value1, warning_value2, ...]}.
    """
    non_critical_validators = ["additionalProperties"]
    # Depending on whether a validator is critical or not,
    # separate errors into 'critical' and 'warnings'
    critical_errors = []
    validator_to_warning = {
        "additionalProperties": "additional_properties",
    }
    # The warning dictionary has as keys the properties that are not
    # respected, and as values, a list of strings that invalidates the property
    # or describe the error
    warnings = {}
    for e in errors:
        # Get the path of the error (where in reana.yaml it occurred).
        # The `path` property of a ValidationError is only relative to its `parent`.
        error_path = e.absolute_path
        error_path = ".".join(map(str, error_path))
        if e.validator in non_critical_validators:
            warning_value = [{"message": e.message, "path": error_path}]
            if e.validator == "additionalProperties":
                # If the error is about additional properties, we want to return the
                # name(s) of the additional properties in a list.
                # There is no easy way to extract the name of the additional properties,
                # so we parse the error message. See https://github.com/reanahub/reana-commons/pull/405

                # The error message is of the form:
                # "Additional properties are not allowed ('<property>' was unexpected)"
                # "Additional properties are not allowed ('<property1>', '<property2>' were unexpected)"
                content_inside_parentheses = re.search(r"\((.*?)\)", e.message).group(1)
                additional_properties = re.findall(
                    r"'(.*?)'", content_inside_parentheses or ""
                )
                warning_value = [
                    {"property": additional_property, "path": error_path}
                    for additional_property in additional_properties
                ]
            warning_key = validator_to_warning.get(str(e.validator), str(e.validator))
            warnings.setdefault(warning_key, []).extend(warning_value)
        else:
            critical_errors.append(e)

    # If there are critical errors, log and raise exception
    if critical_errors:
        err = best_match(critical_errors)
        logging.error("Invalid REANA specification: {error}".format(error=err.message))
        raise err

    return warnings


def validate_reana_yaml(reana_yaml: Dict) -> Dict:
    """Validate REANA specification file according to jsonschema.

    :param reana_yaml: Dictionary which represents REANA specification file.
    :returns: Dictionary of non-critical warnings, in the form of
    {warning_key: [warning_value1, warning_value2, ...]}.
    :raises ValidationError: Given REANA spec file does not validate against
        REANA specification schema.
    """
    try:
        with open(reana_yaml_schema_file_path, "r") as f:
            # Create validator from REANA specification schema
            reana_yaml_schema = json.loads(f.read())
            validator_class = validator_for(reana_yaml_schema)
            validator_class.check_schema(reana_yaml_schema)
            validator = validator_class(reana_yaml_schema)

            # Collect all validation errors
            errors = [e for e in validator.iter_errors(reana_yaml)]
            return _get_schema_validation_warnings(errors)
    except IOError as e:
        logging.info(
            "Something went wrong when reading REANA validation schema from "
            "{filepath} : \n"
            "{error}".format(filepath=reana_yaml_schema_file_path, error=e.strerror)
        )
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
