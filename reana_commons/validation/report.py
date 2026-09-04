# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

r"""Aggregate REANA workflow specification validation into a structured report.

This module runs all the structural and policy checks on an *already-serialized*
REANA specification (i.e. one whose ``workflow.specification`` has already been
produced by loading the workflow files) and returns a machine-readable report.

It never loads or parses workflow files, so it executes no untrusted code and is
safe to call in-process. The dangerous loading step lives in
:func:`reana_commons.specification.load_reana_spec` and must only run inside the
sandboxed workflow validator (or in-process for serial workflows, whose loading
is pure dictionary manipulation).

The report uses stable string ``code``\\ s rather than English prose so that
non-Python clients (e.g. the Go client) can render and localise messages without
parsing them.
"""

import json
from typing import Dict, List

from jsonschema import ValidationError

from reana_commons.errors import REANAValidationError
from reana_commons.validation.compute_backends import build_compute_backends_validator
from reana_commons.validation.dask import validate_dask_limits
from reana_commons.validation.images import validate_images
from reana_commons.validation.operational_options import validate_operational_options
from reana_commons.validation.parameters import build_parameters_validator
from reana_commons.validation.utils import (
    MAX_INPUT_PATH_DECLARATIONS,
    bound_error_message,
    validate_json_tree,
    validate_inputs,
    validate_reana_yaml,
    validate_retention_rule,
    validate_workspace,
)

MAX_VALIDATION_REPORT_ENTRIES = 100
REPORT_TRUNCATED_CODE = "report_truncated"


def _entry(code: str, message, path: str = "") -> Dict:
    """Build a single report entry."""
    return {
        "code": code,
        "message": bound_error_message(message),
        "path": bound_error_message(path) if path else "",
    }


class _ValidationReport:
    """Collect validation findings within one global response budget."""

    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.has_errors = False
        self.truncated = False

    def add_error(self, code: str, message, path: str = "") -> None:
        """Record an error while reserving room for a truncation marker."""
        self.has_errors = True
        if len(self.errors) < MAX_VALIDATION_REPORT_ENTRIES - 1:
            self.errors.append(_entry(code, message, path))
        else:
            self.truncated = True

    def add_warning(self, code: str, message, path: str = "") -> None:
        """Record a warning within a bounded intermediate list."""
        if len(self.warnings) < MAX_VALIDATION_REPORT_ENTRIES:
            self.warnings.append(_entry(code, message, path))
        else:
            self.truncated = True

    def mark_truncated(self) -> None:
        """Record that a producer omitted findings before adding them here."""
        self.truncated = True

    def as_dict(self) -> Dict:
        """Return the bounded public report, prioritising errors over warnings."""
        remaining = MAX_VALIDATION_REPORT_ENTRIES - len(self.errors)
        warnings = self.warnings[:remaining]
        truncated = self.truncated or len(warnings) < len(self.warnings)
        if truncated:
            warnings = warnings[: max(remaining - 1, 0)]
            if remaining:
                warnings.append(
                    _entry(
                        REPORT_TRUNCATED_CODE,
                        "Additional validation findings were omitted.",
                    )
                )
        return {
            "valid": not self.has_errors,
            "errors": self.errors,
            "warnings": warnings,
        }


def _check(report: _ValidationReport, code: str, func, *args, **kwargs) -> None:
    """Run a policy check, recording a ``REANAValidationError`` as an error entry.

    Centralises the "call a validator, turn its ``REANAValidationError`` into a
    structured error entry" pattern shared by most checks below.
    """
    try:
        func(*args, **kwargs)
    except REANAValidationError as e:
        report.add_error(code, e)


def _validate_json_boundary(reana_yaml: Dict) -> None:
    """Reject values that cannot cross the HTTP and database JSON boundary."""
    validate_json_tree(reana_yaml)
    try:
        json.dumps(reana_yaml, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as e:
        raise REANAValidationError(
            "Specification contains values that cannot be represented as JSON."
        ) from e


def _validate_input_path_budget(reana_yaml: Dict) -> None:
    """Reject specifications with too many declared input paths."""
    inputs = reana_yaml.get("inputs", {})
    if not isinstance(inputs, dict):
        return
    files = inputs.get("files", [])
    directories = inputs.get("directories", [])
    if (
        isinstance(files, list)
        and isinstance(directories, list)
        and len(files) + len(directories) > MAX_INPUT_PATH_DECLARATIONS
    ):
        raise REANAValidationError(
            "Too many input paths declared (maximum is {})".format(
                MAX_INPUT_PATH_DECLARATIONS
            )
        )


def validate_serialized_spec(reana_yaml: Dict, policy: Dict) -> Dict:
    """Validate an already-serialized REANA specification.

    :param reana_yaml: Serialized REANA specification (``workflow.specification``
        already expanded).
    :param policy: Cluster policy inputs. Recognised keys (all optional):
        ``vetted_images_enabled`` (bool), ``vetted_images_allowlist`` (list),
        ``supported_backends`` (list), ``workspace_paths`` (list),
        ``dask_config`` (dict or ``None`` to skip), ``max_retention_period``
        (int or ``None``).
    :returns: Report dict ``{"valid": bool, "errors": [...], "warnings": [...]}``
        where each entry is ``{"code", "message", "path"}``.
    """
    report = _ValidationReport()

    # These cheap bounded checks must run before JSON Schema traversal so that
    # recursive YAML aliases cannot reach recursive validator code.
    _check(report, "serialization", _validate_json_boundary, reana_yaml)
    _check(report, "input_path", _validate_input_path_budget, reana_yaml)
    if report.has_errors:
        return report.as_dict()

    workflow_type = reana_yaml.get("workflow", {}).get("type")

    # 1. JSON schema -- a critical schema error makes the rest meaningless.
    try:
        schema_warnings = validate_reana_yaml(reana_yaml)
    except ValidationError as e:
        report.add_error("schema", e.message, ".".join(map(str, e.absolute_path)))
        return report.as_dict()

    for key, values in schema_warnings.items():
        for value in values:
            if key == "additional_properties":
                report.add_warning(
                    "additional_properties",
                    f"Unexpected property '{value['property']}'",
                    value.get("path", ""),
                )
            else:
                report.add_warning(key, value.get("message", ""), value.get("path", ""))

    # 2. Operational options
    options = reana_yaml.get("inputs", {}).get("options", {})
    if options:
        _check(
            report,
            "operational_options",
            validate_operational_options,
            workflow_type,
            options,
        )

    # 3. Parameters (warnings only for serial/yadage/snakemake; CWL may raise)
    try:
        validator = build_parameters_validator(
            reana_yaml, max_warnings=MAX_VALIDATION_REPORT_ENTRIES
        )
        validator.validate_parameters()
        for warning in (
            validator.reana_params_warnings
            + validator.workflow_params_warnings
            + validator.operations_warnings
        ):
            report.add_warning("parameters", warning["message"])
        if validator.warnings_truncated:
            report.mark_truncated()
    except REANAValidationError as e:
        report.add_error("parameters", e)

    # 4. Compute backends
    _check(
        report,
        "compute_backend",
        lambda: build_compute_backends_validator(
            reana_yaml, policy.get("supported_backends") or []
        ).validate(),
    )

    # 5. Workspace root path
    root_path = reana_yaml.get("workspace", {}).get("root_path")
    if root_path:
        _check(
            report,
            "workspace",
            validate_workspace,
            root_path,
            policy.get("workspace_paths") or [],
        )

    # 6. Inputs (path traversal / duplicates)
    _check(report, "input_path", validate_inputs, reana_yaml)

    # 7. Container images (vetted allowlist)
    _check(
        report,
        "image_not_allowed",
        validate_images,
        reana_yaml,
        enabled=policy.get("vetted_images_enabled", False),
        allowlist=policy.get("vetted_images_allowlist") or [],
    )

    # 8. Dask limits (skipped when no dask policy is provided)
    dask_config = policy.get("dask_config")
    if dask_config is not None:
        _check(report, "dask", validate_dask_limits, reana_yaml, dask_config)

    # 9. Retention rules
    retention_days = reana_yaml.get("workspace", {}).get("retention_days") or {}
    for rule, days in retention_days.items():
        _check(
            report,
            "retention",
            validate_retention_rule,
            rule,
            days,
            policy.get("max_retention_period"),
        )

        if len(report.errors) >= MAX_VALIDATION_REPORT_ENTRIES - 1:
            report.mark_truncated()
            break

    return report.as_dict()
