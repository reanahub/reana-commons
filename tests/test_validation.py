# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022, 2023, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons validation testing."""

import operator

import pytest
from jsonschema.exceptions import ValidationError

from reana_commons.validation.utils import (
    MAX_LOAD_ERROR_MESSAGE_CHARS,
    MAX_SCHEMA_WARNINGS,
    bound_error_message,
    validate_reana_yaml,
)


@pytest.mark.parametrize(
    "retention_days",
    [
        {"x/y": 0},
        {"x/y": 0, "**/*.zip": 10},
        pytest.param({}, marks=pytest.mark.xfail(strict=True)),
        pytest.param({"x/y": "1"}, marks=pytest.mark.xfail(strict=True)),
        pytest.param({"x/y": -1}, marks=pytest.mark.xfail(strict=True)),
    ],
)
def test_validation_retention_days(yadage_workflow_spec_loaded, retention_days):
    """Test the validation of ``retention_days`` section of ``reana.yaml``."""
    reana_yaml = yadage_workflow_spec_loaded
    reana_yaml.setdefault("workspace", {}).update({"retention_days": retention_days})
    warnings = validate_reana_yaml(reana_yaml)
    assert warnings == {}


@pytest.mark.parametrize(
    "extra_keys,expected_warnings",
    [
        (
            ["wrong_key"],
            {"additional_properties": [{"property": "wrong_key", "path": ""}]},
        ),
        (
            ["wrong_key", "wrong_key2"],
            {
                "additional_properties": [
                    {"property": "wrong_key", "path": ""},
                    {"property": "wrong_key2", "path": ""},
                ]
            },
        ),
        ([], {}),
    ],
)
def test_warnings_reana_yaml(
    yadage_workflow_spec_loaded, extra_keys, expected_warnings
):
    """Test the validation of the ``reana.yaml`` file.

    Check that the validation returns the expected warnings when there is an
    unexpected key in the specification.
    """
    reana_yaml = yadage_workflow_spec_loaded
    for key in extra_keys:
        reana_yaml[key] = "value"
    warnings = validate_reana_yaml(reana_yaml)
    assert set(expected_warnings.keys()) == set(warnings.keys())
    for key, value in expected_warnings.items():
        if isinstance(value, list):
            assert len(value) == len(warnings[key])
            for warning_value in value:
                assert warning_value in warnings[key]
        else:
            assert value == warnings[key]


def test_schema_warnings_are_bounded(yadage_workflow_spec_loaded):
    """Unexpected properties cannot create an unbounded warning report."""
    for index in range(MAX_SCHEMA_WARNINGS + 1):
        yadage_workflow_spec_loaded[f"unexpected_{index}"] = True

    warnings = validate_reana_yaml(yadage_workflow_spec_loaded)

    assert len(warnings["additional_properties"]) == MAX_SCHEMA_WARNINGS
    assert warnings["schema_warnings_truncated"] == [
        {"message": "Additional schema warnings were omitted.", "path": ""}
    ]


def test_critical_errors_reana_yaml(yadage_workflow_spec_loaded):
    """Test the validation of the ``reana.yaml`` file.

    Test that the validation raises an error when a required key
    is missing in the specification (critical error).
    """
    # Delete a required key
    reana_yaml = yadage_workflow_spec_loaded
    del reana_yaml["workflow"]
    with pytest.raises(ValidationError):
        validate_reana_yaml(reana_yaml)


def test_bound_error_message_keeps_first_line():
    """The first (informative) line of a multi-line error is kept."""
    error = FileNotFoundError("[Errno 2] No such file or directory: 'rules/common.smk'")
    message = bound_error_message("{}\nTraceback ...\n  more frames".format(error))
    assert message == "[Errno 2] No such file or directory: 'rules/common.smk'"


def test_bound_error_message_accepts_exception():
    """An exception instance is stringified to its message."""
    assert bound_error_message(RuntimeError("boom")) == "boom"


def test_bound_error_message_truncates_long_input():
    """An over-long line is truncated with an ellipsis at the cap."""
    message = bound_error_message("A" * (MAX_LOAD_ERROR_MESSAGE_CHARS + 100))
    assert len(message) == MAX_LOAD_ERROR_MESSAGE_CHARS + len("...")
    assert message.endswith("...")


@pytest.mark.parametrize("value", ["", "   ", "\n\n"])
def test_bound_error_message_empty_falls_back(value):
    """An error with no text yields a generic fallback sentence."""
    assert bound_error_message(value) == "The specification could not be loaded."
