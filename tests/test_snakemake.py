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
from types import SimpleNamespace

import pytest
from reana_commons.config import SNAKEMAKE_DYNAMIC_VALUE
from reana_commons.errors import REANAValidationError
from reana_commons.snakemake import (
    _replace_functions,
    _resource_value,
    snakemake_load,
)
from reana_commons.validation.compute_backends import (
    build_compute_backends_validator,
)
from reana_commons.validation.images import extract_image_environments
from reana_commons.validation.parameters import build_parameters_validator
from reana_commons.validation.report import validate_serialized_spec
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


def _snakemake_reana_yaml(metadata):
    """Return a REANA specification that holds loaded Snakemake metadata."""
    return {
        "inputs": {"parameters": {}},
        "workflow": {
            "type": "snakemake",
            "file": "Snakefile",
            "specification": metadata,
        },
    }


def test_snakemake_load_named_input_and_param_functions(tmpdir):
    """Test that named input and parameter functions are recorded by name.

    Snakemake calls such functions for each job, so they have no value when
    the specification is loaded, and a function cannot be stored as JSON.
    """
    snakefile = tmpdir.join("Snakefile")
    snakefile.write("""
def get_data(wildcards):
    return "static.txt"

rule all:
    input: "output.txt"
    default_target: True

rule create_output:
    input:
        data=get_data,
        static="static.txt"
    output: "output.txt"
    params:
        label=lambda wildcards: "hello",
        flags=("-v", "-x")
    shell: "cat {input.data} {input.static} > {output}; echo {params.label} {params.flags}"
""")
    tmpdir.join("static.txt").write("Content of static.txt")

    metadata = snakemake_load(Path(snakefile.strpath), workdir=Path(tmpdir.strpath))

    assert len(metadata["steps"]) == 1
    step = metadata["steps"][0]
    assert step["inputs"] == {
        "data": SNAKEMAKE_DYNAMIC_VALUE,
        "static": "static.txt",
    }
    assert step["params"] == {
        "label": SNAKEMAKE_DYNAMIC_VALUE,
        "flags": ("-v", "-x"),
    }
    validate_json_tree(metadata)
    json.dumps(metadata, allow_nan=False)

    # The names stay usable by the parameter validator.
    validator = build_parameters_validator(_snakemake_reana_yaml(metadata))
    validator.validate_parameters()
    assert not validator.workflow_params_warnings

    report = validate_serialized_spec(_snakemake_reana_yaml(metadata), policy={})
    assert report == {"valid": True, "errors": [], "warnings": []}


def test_snakemake_replace_functions():
    """Test that only functions are replaced, also inside lists and mappings."""

    def function(wildcards):
        return "static.txt"

    assert _replace_functions(function) == SNAKEMAKE_DYNAMIC_VALUE
    assert _replace_functions([function, "static.txt"]) == [
        SNAKEMAKE_DYNAMIC_VALUE,
        "static.txt",
    ]
    assert _replace_functions({"flags": ("-v", function)}) == {
        "flags": ["-v", SNAKEMAKE_DYNAMIC_VALUE]
    }

    # Values without functions are returned as they are, not copied.
    for value in ("static.txt", 3, None, ("-v", "-x"), ["-v"], {"flags": ["-v"]}):
        assert _replace_functions(value) is value


@pytest.mark.parametrize(
    "resource, function",
    [
        ("compute_backend", 'lambda wildcards, attempt: "kubernetes"'),
        ("kubernetes_memory_limit", 'lambda wildcards, attempt: "256Mi"'),
        ("kubernetes_uid", "lambda wildcards, attempt: 1000"),
    ],
)
def test_snakemake_load_resource_functions(tmpdir, resource, function):
    """Test that a REANA resource set by a function is recorded as dynamic.

    The other resources keep their static values, and the loaded metadata
    passes the specification validation with a warning that names the rule and
    the resource.
    """
    static_resources = {
        "compute_backend": "kubernetes",
        "kubernetes_memory_limit": "256Mi",
        "kubernetes_uid": 1000,
    }
    resources = dict(
        {name: repr(value) for name, value in static_resources.items()},
        **{resource: function},
    )
    snakefile = tmpdir.join("Snakefile")
    snakefile.write(
        """
rule all:
    input: "output.txt"
    default_target: True

rule create_output:
    output: "output.txt"
    container: "docker://docker.io/library/python:3.10.0-buster"
    resources:
        {}
    shell: "touch {{output}}"
""".format(
            ",\n        ".join(
                "{}={}".format(name, value) for name, value in resources.items()
            )
        )
    )

    metadata = snakemake_load(Path(snakefile.strpath), workdir=Path(tmpdir.strpath))

    assert len(metadata["steps"]) == 1
    step = metadata["steps"][0]
    assert {name: step[name] for name in static_resources} == dict(
        static_resources, **{resource: SNAKEMAKE_DYNAMIC_VALUE}
    )
    validate_json_tree(metadata)
    json.dumps(metadata, allow_nan=False)

    reana_yaml = _snakemake_reana_yaml(metadata)
    report = validate_serialized_spec(
        reana_yaml, policy={"supported_backends": ["kubernetes"]}
    )
    assert report["valid"] is True
    assert report["warnings"] == [
        {
            "code": "dynamic_resource",
            "message": 'Rule "create_output" sets "{}" with a function. REANA '
            "does not check this value during validation. REANA checks it "
            "when each job starts.".format(resource),
            "path": "",
        }
    ]

    # The effective UID of the rule is known only when no function sets it.
    environments = extract_image_environments(reana_yaml, 1001, 0)
    if resource == "kubernetes_uid":
        assert environments == []
    else:
        assert environments == [
            {
                "image": "docker.io/library/python:3.10.0-buster",
                "runtime_uid": 1000,
                "runtime_gid": 0,
            }
        ]


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("kubernetes", "kubernetes"),
        (1000, 1000),
        (lambda wildcards: 1000, SNAKEMAKE_DYNAMIC_VALUE),
    ],
)
def test_snakemake_resource_value(value, expected):
    """Test the value recorded for a raw resource, as Snakemake 7 holds it."""
    rule = SimpleNamespace(name="create_output", resources={"kubernetes_uid": value})

    assert _resource_value(rule, "kubernetes_uid") == expected
    assert _resource_value(rule, "compute_backend") is None


def test_snakemake_resource_value_of_unsupported_type():
    """Test that an unsupported resource value names the rule and resource."""
    rule = SimpleNamespace(name="create_output", resources={"kubernetes_uid": [1000]})

    with pytest.raises(
        REANAValidationError,
        match='resource "kubernetes_uid" of rule "create_output" must be',
    ):
        _resource_value(rule, "kubernetes_uid")


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
