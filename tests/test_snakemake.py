# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021, 2022, 2023, 2024, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons Snakemake tests."""

import json
import os
import sys
from pathlib import Path

import pytest
from reana_commons.errors import REANAValidationError
from reana_commons.snakemake import (
    SNAKEMAKE_DYNAMIC_CONTAINER_IMAGE,
    snakemake_load,
)
from reana_commons.validation.compute_backends import (
    build_compute_backends_validator,
)
from reana_commons.validation.parameters import build_parameters_validator
from reana_commons.validation.utils import validate_json_tree


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

    loader_paths = [
        value
        for step in metadata["steps"]
        for field in ("inputs", "outputs")
        for value in step[field].values()
    ]
    assert any(
        isinstance(value, str) and type(value) is not str for value in loader_paths
    )
    validate_json_tree(metadata)
    json.dumps(metadata)

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


def _snakemake_parameter_warnings(steps):
    """Return the parameter validation warnings for the given Snakemake steps."""
    validator = build_parameters_validator(
        {
            "inputs": {"parameters": {}},
            "workflow": {"type": "snakemake", "specification": {"steps": steps}},
        }
    )
    validator.validate_parameters()
    return sorted(
        warning["message"]
        for warning in validator.reana_params_warnings
        + validator.workflow_params_warnings
    )


@pytest.mark.parametrize(
    "command",
    [
        "echo {params.message:q} > {output.result:q} < {input.source:q}",
        "echo {params.message!r} > {output.result} < {input.source}",
        "echo {params.message[0]} > {output.result[0]} < {input.source.name}",
    ],
)
def test_snakemake_parameters_with_format_specifiers(command):
    """Test that formatting syntax is not taken as part of a parameter name."""
    assert not _snakemake_parameter_warnings(
        [
            {
                "name": "write",
                "inputs": {"source": "input.txt"},
                "params": {"message": "hello world"},
                "outputs": {"result": "result.txt"},
                "commands": [command],
            }
        ]
    )


@pytest.mark.parametrize(
    "command",
    [
        "cp {input.source} {output}",
        "cp {input} {output}",
        "cp input.txt {output}",
        "python copy.py",
    ],
)
def test_snakemake_named_inputs_are_not_reported_as_unused(command):
    """Test that named inputs do not have to be referenced in the command."""
    assert not _snakemake_parameter_warnings(
        [
            {
                "name": "copy",
                "inputs": {"source": "input.txt"},
                "params": {},
                "outputs": {},
                "commands": [command],
            }
        ]
    )


def test_snakemake_misused_parameters_are_still_reported():
    """Test that undefined and unused parameters keep producing warnings."""
    assert _snakemake_parameter_warnings(
        [
            {
                "name": "write",
                "inputs": {"source": "input.txt"},
                "params": {"message": "hello world", "unused": 1},
                "outputs": {"result": "result.txt"},
                "commands": [
                    "echo {params.message:q} {params.missing:q} {input.other}"
                    " > {output.result:q}"
                ],
            }
        ]
    ) == [
        'Snakemake input parameter "params.unused" found on step "write" does'
        " not seem to be used.",
        'Snakemake parameter "input.other" found on step "write" is not defined'
        " in input parameters.",
        'Snakemake parameter "params.missing" found on step "write" is not'
        " defined in input parameters.",
    ]


@pytest.mark.parametrize("command", ["cat data.txt", "cat {input.data}"])
def test_snakemake_named_input_does_not_hide_unused_param_of_same_name(command):
    """Test that a named input does not count as a use of a same-named param."""
    assert _snakemake_parameter_warnings(
        [
            {
                "name": "read",
                "inputs": {"data": "data.txt"},
                "params": {"data": "--fast"},
                "outputs": {},
                "commands": [command],
            }
        ]
    ) == [
        'Snakemake input parameter "params.data" found on step "read" does not'
        " seem to be used."
    ]


@pytest.mark.parametrize(
    "command",
    [
        "echo {params.sample-id} > {output.result}",
        "echo {params.sample-id:q} > {output.result:q}",
        "echo {params.sample-id[0]} > {output.result}",
    ],
)
def test_snakemake_parameter_names_beyond_python_identifiers(command):
    """Test that names are read up to the formatting syntax, e.g. with hyphens."""
    assert not _snakemake_parameter_warnings(
        [
            {
                "name": "write",
                "inputs": {},
                "params": {"sample-id": "hello"},
                "outputs": {"result": "result.txt"},
                "commands": [command],
            }
        ]
    )


def test_snakemake_loaded_rule_parameters_validation(tmpdir):
    """Test parameter validation of quoted fields and dependency-only inputs."""
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("""
rule all:
    input:
        "compared.txt"

rule write:
    output:
        result="result.txt"
    params:
        message="hello world"
    shell:
        "echo {params.message:q} > {output.result:q}"

rule compare:
    input:
        script="compare.py",
        result="result.txt"
    output:
        "compared.txt"
    shell:
        "python {input.script:q} > {output:q}"
""")
    tmpdir.join("compare.py").write("print(open('result.txt').read())")

    metadata = snakemake_load(Path(snakefile.strpath), workdir=Path(tmpdir.strpath))

    assert not _snakemake_parameter_warnings(metadata["steps"])


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


def test_snakemake_load_rule_with_wildcard_container(tmpdir):
    """A wildcard-templated container is recorded unexpanded, not resolved."""
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("""
rule all:
    input: "out_3.11.txt"
    default_target: True

rule create_output:
    output: "out_{version}.txt"
    container: "docker://python:{version}"
    shell: "touch {output}"
""")

    metadata = snakemake_load(Path(snakefile.strpath))

    assert len(metadata["steps"]) == 1
    assert metadata["steps"][0]["environment"] == "python:{version}"


def test_snakemake_load_rule_with_callable_container(tmpdir):
    """A callable container is recorded as the dynamic placeholder.

    Snakemake only calls the function once a job's wildcards are known, so no
    image name exists at load time. The function itself is not JSON-encodable
    and used to crash the loader with an ``AttributeError``.

    Only Snakemake 8+ accepts a callable here, so Python versions still pinned
    to Snakemake 7 assert the rejection they get instead.
    """
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("""
def pick_container(wildcards):
    return "docker://python:3.11"

rule all:
    input: "output.txt"
    default_target: True

rule create_output:
    output: "output.txt"
    container: pick_container
    shell: "touch {output}"
""")

    if sys.version_info < (3, 11):
        # Snakemake 7 refuses a callable ``container:`` while building the DAG,
        # so the rule never reaches the loader in the first place.
        with pytest.raises(REANAValidationError):
            snakemake_load(Path(snakefile.strpath))
        return

    metadata = snakemake_load(Path(snakefile.strpath))

    assert len(metadata["steps"]) == 1
    assert metadata["steps"][0]["environment"] == SNAKEMAKE_DYNAMIC_CONTAINER_IMAGE
    # The whole specification must stay serialisable for storage and transport.
    validate_json_tree(metadata)


@pytest.mark.parametrize(
    "container, type_name",
    [('["docker://python:3.11"]', "list"), ('{"image": "python:3.11"}', "dict")],
)
def test_snakemake_load_rule_with_invalid_container_type(tmpdir, container, type_name):
    """A container that is neither a string nor a function is rejected."""
    snakefile = tmpdir.join("Snakefile")
    snakefile.write(f"""
rule all:
    input: "output.txt"
    default_target: True

rule create_output:
    output: "output.txt"
    container: {container}
    shell: "touch {{output}}"
""")

    with pytest.raises(REANAValidationError) as excinfo:
        snakemake_load(Path(snakefile.strpath))

    if sys.version_info >= (3, 11):
        # Snakemake 7 rejects such a value itself, with a generic message.
        assert 'container of rule "create_output"' in str(excinfo.value)
        assert f"not {type_name}" in str(excinfo.value)


def test_snakemake_load_repeated_tuple_params(tmpdir):
    """Constant-folded tuple parameters remain JSON-compatible."""
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("""
rule all:
    input:
        "one.txt",
        "two.txt"
    default_target: True

rule one:
    output: "one.txt"
    params:
        flags=("-v", "-x"),
        extra=()
    shell: "touch {output}"

rule two:
    output: "two.txt"
    params:
        flags=("-v", "-x"),
        extra=()
    shell: "touch {output}"
""")

    metadata = snakemake_load(Path(snakefile.strpath), workdir=Path(tmpdir.strpath))
    params = [step["params"] for step in metadata["steps"]]

    assert params[0]["flags"] is params[1]["flags"]
    assert params[0]["extra"] is params[1]["extra"]
    validate_json_tree(metadata)
    json.dumps(metadata)


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
