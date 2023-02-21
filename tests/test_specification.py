# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons specification utils tests."""

import pathlib
import pytest
import sys

from reana_commons.specification import load_reana_spec


def test_empty_parameters(tmp_path: pathlib.Path):
    """Test loading the specification of a workflow with empty parameters."""
    cwl_spec = tmp_path / "spec.cwl"
    cwl_spec.write_text("cwlVersion: v1.0\nclass: Workflow")

    reana_yaml = tmp_path / "reana.yaml"
    reana_yaml.write_text(
        "inputs:\n"
        "  files:\n"
        "   - input.txt\n"
        "workflow:\n"
        "  type: cwl\n"
        "  file: spec.cwl\n"
    )

    reana_spec = load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))
    # test that the spec was loaded correctly
    assert reana_spec["inputs"]["files"][0] == "input.txt"


def test_parameters_file(tmp_path: pathlib.Path):
    """Test loading the workflow parameters from an external file."""
    cwl_spec = tmp_path / "spec.cwl"
    cwl_spec.write_text("cwlVersion: v1.0\nclass: Workflow")

    reana_yaml = tmp_path / "reana.yaml"
    reana_yaml.write_text(
        "inputs:\n"
        "  parameters:\n"
        "    input: params.yaml\n"
        "workflow:\n"
        "  type: cwl\n"
        "  file: spec.cwl\n"
    )

    params = tmp_path / "params.yaml"
    params.write_text("qwerty: 123")

    reana_spec = load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))
    assert reana_spec["inputs"]["parameters"]["qwerty"] == 123
