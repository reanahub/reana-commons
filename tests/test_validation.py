# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons validation testing."""

import pytest

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
    validate_reana_yaml(reana_yaml)
