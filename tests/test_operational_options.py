# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2020 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons utilities testing."""

import pytest

from reana_commons.errors import REANAValidationError
from reana_commons.operational_options import validate_operational_options


@pytest.mark.parametrize(
    "workflow_type, options, except_msg",
    [
        ("serial", "CACHE=on", "must be a dict"),
        ("yadage", {"unsupported": "yes"}, "not supported"),
        ("foo", {"TARGET": "gendata"}, "not supported for {workflow_type} workflows"),
        (
            "serial",
            {"toplevel": "github:reanahub/awesome-workflow"},
            "not supported for {workflow_type} workflows",
        ),
    ],
)
def test_unsupported(workflow_type, options, except_msg):
    """Test unsupported operational options cases."""
    with pytest.raises(REANAValidationError) as e:
        validate_operational_options(workflow_type, options)
    assert except_msg.format(workflow_type=workflow_type) in e.value.message


@pytest.mark.parametrize(
    "workflow_type, options, option",
    [
        ("serial", {"FROM": "fitdata"}, "FROM"),
        ("yadage", {"toplevel": "github:reanahub/awesome-workflow"}, "toplevel"),
        ("cwl", {"TARGET": "gendata"}, "--target"),
    ],
)
def test_successful(workflow_type, options, option):
    """Test successful operational options cases."""
    validated_options = validate_operational_options(workflow_type, options)
    assert validated_options[option]
