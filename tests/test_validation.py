# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons validation testing."""
import operator

import pytest
from jsonschema.exceptions import ValidationError

from reana_commons.validation.utils import validate_reana_yaml


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
