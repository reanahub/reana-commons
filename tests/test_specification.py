# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2023, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons specification utils tests."""

import pathlib
import pytest
import sys
import yaml

from reana_commons.specification import (
    load_reana_spec,
    load_input_parameters,
    load_workflow_spec_from_reana_yaml,
)
from reana_commons.validation.images import extract_images
from reana_commons.specification_paths import gather_validation_members
from reana_commons.errors import REANAValidationError


@pytest.mark.parametrize("legacy", [False, True])
def test_snakemake_load_uses_resolved_parameters(tmp_path, legacy):
    """Config-dependent workflow metadata uses file values and inline overrides."""
    (tmp_path / "Snakefile").write_text(
        "rule output:\n"
        '    output: "result.txt"\n'
        '    params: events=config["events"]\n'
        '    container: config["image"]\n'
        '    shell: "echo {params.events} > {output}"\n'
    )
    (tmp_path / "params.yaml").write_text("events: 2000\nimage: ubuntu:22.04\n")
    specification = {
        "workflow": {"type": "snakemake", "file": "Snakefile"},
        "inputs": {"parameters": {"image": "ubuntu:24.04"}},
    }
    if legacy:
        specification["inputs"]["parameters"]["input"] = "params.yaml"
    else:
        specification["workflow"]["parameters"] = {"file": "params.yaml"}
    path = tmp_path / "reana.yaml"
    path.write_text(yaml.safe_dump(specification))

    loaded = load_reana_spec(str(path), workspace_path=str(tmp_path))

    assert loaded["inputs"]["parameters"] == {"events": 2000, "image": "ubuntu:24.04"}
    assert extract_images(loaded) == ["ubuntu:24.04"]
    assert loaded["workflow"]["specification"]["steps"][0]["params"]["events"] == 2000


def test_yadage_parameter_files_are_scoped_and_merged(tmp_path):
    """Yadage validates the same ordered initfiles and inline values as execution."""
    (tmp_path / "workflow.yaml").write_text("stages: []\n")
    (tmp_path / "first.yaml").write_text("events: 20000\nseed: 42\n")
    (tmp_path / "second.yaml").write_text("events: 2000\n")
    specification = {
        "workflow": {"type": "yadage", "file": "workflow.yaml", "files": []},
        "inputs": {
            "parameters": {"seed": 7},
            "options": {"initfiles": ["first.yaml", "second.yaml"]},
        },
    }
    path = tmp_path / "reana.yaml"
    path.write_text(yaml.safe_dump(specification))

    members, _, _ = gather_validation_members(str(path))
    assert set(members) == {"reana.yaml", "workflow.yaml", "first.yaml", "second.yaml"}
    assert load_input_parameters(specification, str(tmp_path)) == {
        "events": 2000,
        "seed": 7,
    }


@pytest.mark.parametrize("contents", ["- invalid", "events: ["])
def test_yadage_rejects_invalid_parameter_file(tmp_path, contents):
    """Malformed Yadage initfiles fail loading before execution."""
    (tmp_path / "params.yaml").write_text(contents)
    specification = {
        "workflow": {"type": "yadage"},
        "inputs": {"options": {"initfiles": ["params.yaml"]}},
    }
    with pytest.raises((REANAValidationError, yaml.YAMLError)):
        load_input_parameters(specification, str(tmp_path))


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


def test_workflow_parameters_file(tmp_path: pathlib.Path):
    """Test the preferred workflow.parameters.file spelling."""
    cwl_spec = tmp_path / "spec.cwl"
    cwl_spec.write_text("cwlVersion: v1.0\nclass: Workflow")
    (tmp_path / "params.yaml").write_text("qwerty: 123")
    reana_yaml = tmp_path / "reana.yaml"
    reana_yaml.write_text(
        "workflow:\n"
        "  type: cwl\n"
        "  file: spec.cwl\n"
        "  parameters:\n"
        "    file: params.yaml\n"
    )
    reana_spec = load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))
    assert reana_spec["inputs"]["parameters"]["qwerty"] == 123
    assert reana_spec["workflow"]["parameters"]["file"] == "params.yaml"


def test_parameters_file_requires_mapping(tmp_path: pathlib.Path):
    """Parameter files cannot replace inputs.parameters with a scalar/list."""
    cwl_spec = tmp_path / "spec.cwl"
    cwl_spec.write_text("cwlVersion: v1.0\nclass: Workflow")
    (tmp_path / "params.yaml").write_text("- invalid")
    reana_yaml = tmp_path / "reana.yaml"
    reana_yaml.write_text(
        "workflow:\n"
        "  type: cwl\n"
        "  file: spec.cwl\n"
        "  parameters:\n"
        "    file: params.yaml\n"
    )
    with pytest.raises(Exception, match="must contain a YAML mapping"):
        load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))


def test_snakemake_container_image_extraction(tmp_path: pathlib.Path):
    """Test that loading a Snakemake workflow exposes its container images."""
    (tmp_path / "Snakefile").write_text(
        "rule all:\n"
        '    input: "output.txt"\n'
        "    default_target: True\n"
        "\n"
        "rule create_output:\n"
        '    output: "output.txt"\n'
        '    container: "docker://docker.io/library/ubuntu:24.04"\n'
        '    shell: "touch {output}"\n'
    )
    reana_yaml = {"workflow": {"type": "snakemake", "file": "Snakefile"}}

    reana_yaml["workflow"]["specification"] = load_workflow_spec_from_reana_yaml(
        reana_yaml, str(tmp_path)
    )

    assert extract_images(reana_yaml) == ["docker.io/library/ubuntu:24.04"]
