# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021, 2022, 2023, 2024, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons Snakemake tests."""

import os
import sys
from pathlib import Path

import pytest
from reana_commons.errors import REANAValidationError
from reana_commons.snakemake import snakemake_load
from reana_commons.validation.compute_backends import (
    build_compute_backends_validator,
)
from reana_commons.validation.parameters import build_parameters_validator


def test_snakemake_load(tmpdir, dummy_snakefile):
    """Test that Snakemake metadata is loaded properly."""
    workdir = tmpdir.mkdir("sub")
    # write Snakefile
    p = workdir.join("Snakefile")
    p.write(dummy_snakefile)
    # write dummy input file
    dummy_input = workdir.join("input.txt")
    dummy_input.write("Content of input.txt")
    assert len(tmpdir.listdir()) == 1
    assert len(workdir.listdir()) == 2

    os.chdir(tmpdir)
    metadata = snakemake_load(Path(p.strpath), workdir=Path(workdir.strpath))
    # check that the cwd is preserved
    assert os.getcwd() == tmpdir

    assert {step["name"]: step["environment"] for step in metadata["steps"]} == {
        "foo": "docker.io/library/python:3.10.0-buster",
        "bar": "docker.io/library/python:3.10.0-buster",
        "baz": "docker.io/library/python:3.10.0-buster",
    }
    assert all(step["commands"] for step in metadata["steps"])
    assert all(step["kubernetes_memory_limit"] == "256Mi" for step in metadata["steps"])
    assert all(step["compute_backend"] is None for step in metadata["steps"])

    if sys.version_info < (3, 11):
        for step in metadata["steps"]:
            assert step["kubernetes_memory_limit"] == "256Mi"
        assert metadata["job_dependencies"] == {
            "foo": [],
            "bar": ["foo"],
            "baz": ["foo", "bar"],
            "all": ["foo", "bar", "baz"],
        }
    else:
        assert metadata["job_dependencies"] == {}

    validator = build_parameters_validator(
        {
            "inputs": {"parameters": {}},
            "workflow": {
                "type": "snakemake",
                "specification": metadata,
            },
        }
    )
    validator.validate_parameters()
    build_compute_backends_validator(
        {
            "workflow": {
                "type": "snakemake",
                "specification": metadata,
            },
        },
        ["kubernetes"],
    ).validate()


def test_snakemake_load_rule_without_container(tmpdir):
    """Test that rules without a container preserve an empty environment."""
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("""
rule all:
    input: "output.txt"
    default_target: True

rule create_output:
    output: "output.txt"
    resources:
        compute_backend="kubernetes",
        kubernetes_uid=1000
    shell: "touch {output}"
""")

    metadata = snakemake_load(Path(snakefile.strpath))

    assert len(metadata["steps"]) == 1
    assert metadata["steps"][0]["name"] == "create_output"
    assert metadata["steps"][0]["environment"] == ""
    assert metadata["steps"][0]["commands"] == ["touch {output}"]
    assert metadata["steps"][0]["compute_backend"] == "kubernetes"
    assert metadata["steps"][0]["kubernetes_memory_limit"] is None
    assert metadata["steps"][0]["kubernetes_uid"] == 1000


def test_snakemake_load_rule_without_shell_command(tmpdir):
    """Test that non-shell rules have no command metadata."""
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("""
rule create_output:
    output: "output.txt"
    run:
        with open(output[0], "w"):
            pass
""")

    metadata = snakemake_load(Path(snakefile.strpath))

    assert len(metadata["steps"]) == 1
    assert metadata["steps"][0]["name"] == "create_output"
    assert metadata["steps"][0]["commands"] == []


def test_snakemake_load_invalid_workflow(tmpdir):
    """Test that parser failures are exposed as REANA validation errors."""
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("this is not a valid Snakefile")

    with pytest.raises(REANAValidationError, match="invalid"):
        snakemake_load(Path(snakefile.strpath))
