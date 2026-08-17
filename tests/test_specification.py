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

from reana_commons.snakemake import snakemake_load
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


# ---------------------------------------------------------------------------
# Snakemake configuration: the specification must be loaded with exactly the
# configuration the runtime engine receives, which passes the final parameter
# mapping as ``--config`` (see reana-workflow-engine-snakemake runner.py).
# ---------------------------------------------------------------------------


def _write_snakemake_workflow(tmp_path, parameters, snakefile, files=None):
    """Write a Snakemake REANA project on disk and return its ``reana.yaml`` path."""
    for name, content in (files or {}).items():
        (tmp_path / name).write_text(content)
    (tmp_path / "Snakefile").write_text(snakefile)
    reana_yaml = tmp_path / "reana.yaml"
    reana_yaml.write_text(
        yaml.safe_dump(
            {
                "inputs": {"parameters": parameters},
                "workflow": {"type": "snakemake", "file": "Snakefile"},
            }
        )
    )
    return reana_yaml


CONFIG_DRIVEN_SNAKEFILE = (
    "rule make:\n"
    '    container: config["image"]\n'
    '    output: "out.txt"\n'
    '    shell: "touch {output}"\n'
)


def test_snakemake_direct_parameter_overrides_internal_configfile(tmp_path):
    """A direct parameter must win over a ``configfile:`` inside the Snakefile."""
    reana_yaml = _write_snakemake_workflow(
        tmp_path,
        {"image": "docker://python:3.11"},
        'configfile: "config.yaml"\n' + CONFIG_DRIVEN_SNAKEFILE,
        files={"config.yaml": "image: docker://python:3.9\n"},
    )

    reana_spec = load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))
    steps = reana_spec["workflow"]["specification"]["steps"]
    assert [step["environment"] for step in steps] == ["python:3.11"]


def test_snakemake_external_input_configfile(tmp_path):
    """``inputs.parameters.input`` names a config file that resolves images."""
    reana_yaml = _write_snakemake_workflow(
        tmp_path,
        {"input": "config.yaml"},
        CONFIG_DRIVEN_SNAKEFILE,
        files={"config.yaml": "image: docker://python:3.9\n"},
    )

    reana_spec = load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))
    steps = reana_spec["workflow"]["specification"]["steps"]
    assert [step["environment"] for step in steps] == ["python:3.9"]
    assert reana_spec["inputs"]["parameters"] == {"image": "docker://python:3.9"}


def test_snakemake_input_file_and_direct_parameters_coexist(tmp_path):
    """An input file and its sibling parameters merge, with siblings winning.

    This mirrors Snakemake's own precedence of ``--config`` over ``configfile:``.
    Siblings must survive into the persisted parameters, since that mapping is
    what the runtime engine is given.
    """
    reana_yaml = _write_snakemake_workflow(
        tmp_path,
        {"input": "config.yaml", "image": "docker://python:3.11", "n": 5},
        CONFIG_DRIVEN_SNAKEFILE,
        files={"config.yaml": "image: docker://python:3.9\nfrom_file: kept\n"},
    )

    reana_spec = load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))
    steps = reana_spec["workflow"]["specification"]["steps"]
    # The direct override wins over the same key in the file...
    assert [step["environment"] for step in steps] == ["python:3.11"]
    # ...and no parameter is lost on either side.
    assert reana_spec["inputs"]["parameters"] == {
        "image": "docker://python:3.11",
        "from_file": "kept",
        "n": 5,
    }


def test_snakemake_loaded_specification_matches_runtime_parameters(tmp_path):
    """The persisted parameters must reproduce the images recorded on the steps.

    The runtime engine passes the persisted ``inputs.parameters`` to Snakemake as
    ``--config``, so loading the workflow with them again must select the same
    images the specification recorded.
    """
    reana_yaml = _write_snakemake_workflow(
        tmp_path,
        {"input": "config.yaml", "image": "docker://python:3.11"},
        'configfile: "internal.yaml"\n' + CONFIG_DRIVEN_SNAKEFILE,
        files={
            "config.yaml": "image: docker://python:3.9\n",
            "internal.yaml": "image: docker://python:3.8\n",
        },
    )

    reana_spec = load_reana_spec(str(reana_yaml), workspace_path=str(tmp_path))
    persisted = reana_spec["inputs"]["parameters"]
    steps = reana_spec["workflow"]["specification"]["steps"]

    replayed = snakemake_load(
        pathlib.Path(tmp_path / "Snakefile"),
        workdir=pathlib.Path(tmp_path),
        config=persisted,
    )
    assert [step["environment"] for step in replayed["steps"]] == [
        step["environment"] for step in steps
    ]
