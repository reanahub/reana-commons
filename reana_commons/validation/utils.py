# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022, 2023, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons validation utilities."""

import json
import logging
import math
import os
import pathlib
import re
from collections import deque
from typing import Dict, List, Optional

from jsonschema import ValidationError
from jsonschema.exceptions import ErrorTree, best_match
from jsonschema.validators import validator_for

from reana_commons.config import (
    REANA_WORKFLOW_NAME_ILLEGAL_CHARACTERS,
    WORKSPACE_PATHS,
    reana_yaml_schema_file_path,
)
from reana_commons.errors import REANAValidationError

MAX_INPUT_PATH_DECLARATIONS = 1000
MAX_SCHEMA_WARNINGS = 100
JSON_BOUNDARY_ERROR = (
    "Specification contains values that cannot be represented as JSON."
)


def validate_json_tree(value) -> None:
    """Require a finite tree made only of JSON-encodable values.

    YAML aliases can produce an acyclic object graph in which the same mapping
    or mutable sequence is referenced many times.  A JSON encoder expands every
    such reference, so a small loaded graph can yield exponentially large
    output.  Reject shared mutable containers, as well as cycles, before any
    JSON encoding.

    :param value: Loaded value intended to cross a JSON boundary.
    :raises REANAValidationError: If ``value`` is not a JSON-compatible tree.
    """
    containers = set()
    pending = [value]

    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            identity = id(item)
            if identity in containers:
                raise REANAValidationError(JSON_BOUNDARY_ERROR)
            containers.add(identity)
            for key, child in item.items():
                if not isinstance(key, str):
                    raise REANAValidationError(JSON_BOUNDARY_ERROR)
                pending.append(child)
        elif isinstance(item, (list, tuple)):
            # YAML aliases and mutable cycles are represented by shared lists.
            # Immutable tuples, on the other hand, are routinely reused by
            # Python and Snakemake (for example through constant folding), and
            # the standard JSON encoder accepts them as arrays.
            if isinstance(item, list):
                identity = id(item)
                if identity in containers:
                    raise REANAValidationError(JSON_BOUNDARY_ERROR)
                containers.add(identity)
            pending.extend(item)
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise REANAValidationError(JSON_BOUNDARY_ERROR)
        elif item is None or isinstance(item, (bool, int, str)):
            continue
        else:
            raise REANAValidationError(JSON_BOUNDARY_ERROR)


def _get_schema_validation_warnings(errors) -> Dict:
    """Parse a list of JSON schema validation errors.

    When validating the REANA specification file against the REANA specification
    schema, the validator can return many ValidationError object. This function parses
    the list of errors and returns a dictionary of warnings, in the form of
    {warning_key: [warning_value1, warning_value2, ...]}.
    """
    non_critical_validators = ["additionalProperties"]
    # Depending on whether a validator is critical or not,
    # separate errors into 'critical' and 'warnings'
    validator_to_warning = {
        "additionalProperties": "additional_properties",
    }
    # The warning dictionary has as keys the properties that are not
    # respected, and as values, a list of strings that invalidates the property
    # or describe the error
    warnings = {}
    warning_count = 0
    warnings_truncated = False
    for e in errors:
        # Get the path of the error (where in reana.yaml it occurred).
        # The `path` property of a ValidationError is only relative to its `parent`.
        error_path = e.absolute_path
        error_path = ".".join(map(str, error_path))
        if e.validator in non_critical_validators:
            if warning_count >= MAX_SCHEMA_WARNINGS:
                warnings_truncated = True
                continue
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
            remaining = MAX_SCHEMA_WARNINGS - warning_count
            retained_values = warning_value[:remaining]
            warnings.setdefault(warning_key, []).extend(retained_values)
            warning_count += len(retained_values)
            warnings_truncated = warnings_truncated or len(retained_values) < len(
                warning_value
            )
        else:
            if e.context:
                e = best_match(e.context)
            logging.error(
                "Invalid REANA specification: {error}".format(
                    error=bound_error_message(e.message)
                )
            )
            raise e

    if warnings_truncated:
        warnings["schema_warnings_truncated"] = [
            {
                "message": "Additional schema warnings were omitted.",
                "path": "",
            }
        ]

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

            return _get_schema_validation_warnings(validator.iter_errors(reana_yaml))
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


def _is_relative_to(path: pathlib.Path, base: pathlib.Path) -> bool:
    """Check whether ``path`` is contained inside ``base``."""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def validate_inputs(reana_yaml: Dict) -> None:
    """Check whether the paths of the input files/directories are valid.

    :param reana_yaml: REANA specification.
    :raises REANAValidationError: If an input path is absolute, empty, contains
        ``..``, or is declared/contained more than once.
    """
    inputs = reana_yaml.get("inputs", {})
    files = inputs.get("files", [])
    directories = inputs.get("directories", [])
    if len(files) + len(directories) > MAX_INPUT_PATH_DECLARATIONS:
        raise REANAValidationError(
            "Too many input paths declared (maximum is "
            f"{MAX_INPUT_PATH_DECLARATIONS})"
        )
    paths = [pathlib.Path(path) for path in files + directories]

    unique_paths = set()
    for path in paths:
        if path.is_absolute():
            raise REANAValidationError(f"Input path cannot be absolute: {path}")
        if not path.parts:
            raise REANAValidationError("Input path cannot be empty")
        if ".." in path.parts:
            raise REANAValidationError(f"Input path cannot contain '..': {path}")
        if path in unique_paths:
            raise REANAValidationError(f"Input path declared multiple times: {path}")
        unique_paths.add(path)

    sorted_paths = sorted(paths, key=lambda path: path.parts)
    for parent, candidate in zip(sorted_paths, sorted_paths[1:]):
        if _is_relative_to(candidate, parent):
            raise REANAValidationError(
                f"Duplicate input paths '{parent}' and '{candidate}' found. "
                "Please deduplicate inputs first."
            )


def validate_retention_rule(
    rule: str, days: int, max_retention_period: Optional[int] = None
) -> None:
    """Validate a workspace retention rule.

    :param rule: Retention rule (relative path or glob).
    :param days: Number of days after which the rule is applied.
    :param max_retention_period: Maximum allowed retention period in days, or
        ``None`` when default retention rules are disabled.
    :raises REANAValidationError: If the rule is not valid.
    """
    rule_path = pathlib.Path(rule)
    if rule_path.is_absolute():
        raise REANAValidationError(f"Retention rule {rule} cannot be an absolute path")
    if not rule_path.parts:
        raise REANAValidationError(f"Retention rule {rule} cannot be empty")
    if ".." in rule_path.parts:
        raise REANAValidationError(f"Retention rule {rule} cannot contain '..'")

    if max_retention_period is not None and days >= max_retention_period:
        raise REANAValidationError(
            "Maximum workflow retention period was reached. "
            f"Please use less than {max_retention_period} days."
        )


MAX_LOAD_ERROR_MESSAGE_CHARS = 500
"""Cap on the length of a surfaced spec-loading error message.

Loading a workflow specification runs untrusted code (Snakemake/CWL/Yadage), so
its exception text is user-influenceable and potentially huge; bounding it keeps
a spec that fails to load informative without letting it flood the report or
leak a wall of loader output."""


def bound_error_message(error, max_chars: int = MAX_LOAD_ERROR_MESSAGE_CHARS) -> str:
    """Reduce an exception (or string) to a short, single-line message.

    Returns the first non-empty line of ``str(error)``, truncated to
    ``max_chars`` with an ellipsis when longer. The first line is where the
    useful detail lives (e.g. the name of a missing referenced file), while the
    length cap bounds any flood/leak from untrusted loader code. Falls back to a
    generic sentence when the error carries no text.

    :param error: An exception instance or a string.
    :param max_chars: Maximum length of the returned message.
    :returns: A bounded, single-line message.
    """
    text = str(error).strip()
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    if not first_line:
        return "The specification could not be loaded."
    if len(first_line) > max_chars:
        return first_line[:max_chars].rstrip() + "..."
    return first_line
