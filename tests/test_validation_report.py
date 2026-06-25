# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the aggregated server-side validation report."""

import math

import pytest
import yaml

from reana_commons.errors import REANAValidationError
from reana_commons.validation.dask import validate_dask_limits
from reana_commons.validation.images import validate_images
from reana_commons.validation.report import (
    MAX_VALIDATION_REPORT_ENTRIES,
    validate_serialized_spec,
)
from reana_commons.validation.utils import validate_inputs, validate_retention_rule
from reana_commons.validation.utils import MAX_INPUT_PATH_DECLARATIONS

ALLOWED_IMAGE = "docker.io/library/busybox:1.36"


def _serial_spec(image=ALLOWED_IMAGE):
    """Return a minimal already-serialized serial specification."""
    return {
        "workflow": {
            "type": "serial",
            "specification": {
                "steps": [
                    {
                        "name": "step1",
                        "environment": image,
                        "commands": ["echo hello"],
                    }
                ]
            },
        },
        "inputs": {"parameters": {}},
    }


def test_valid_serial_spec_reports_no_errors():
    """A well-formed serial spec validates with no errors."""
    reana_yaml = _serial_spec()
    report = validate_serialized_spec(reana_yaml, policy={})
    assert report["valid"] is True
    assert report["errors"] == []


@pytest.mark.parametrize(
    "yaml_value",
    [
        "2026-01-01",
        "!!binary YQ==",
        ".nan",
    ],
)
def test_non_json_yaml_values_are_rejected(yaml_value):
    """YAML-native scalar values cannot pass the later JSON boundary."""
    reana_yaml = _serial_spec()
    value = yaml.safe_load(yaml_value)
    if yaml_value == ".nan":
        assert math.isnan(value)
    reana_yaml["inputs"]["parameters"]["value"] = value

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is False
    assert report["errors"] == [
        {
            "code": "serialization",
            "message": (
                "Specification contains values that cannot be represented as JSON."
            ),
            "path": "",
        }
    ]


def test_recursive_yaml_alias_is_rejected_before_schema_validation():
    """A recursive YAML alias produces a bounded validation error, not a crash."""
    reana_yaml = _serial_spec()
    recursive_value = yaml.safe_load("&value {self: *value}")
    assert recursive_value["self"] is recursive_value
    reana_yaml["inputs"]["parameters"]["value"] = recursive_value

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is False
    assert report["errors"][0]["code"] == "serialization"


def test_acyclic_yaml_alias_graph_is_rejected_before_json_encoding(monkeypatch):
    """A shared alias graph cannot expand while crossing the JSON boundary."""
    reana_yaml = _serial_spec()
    levels = ["level0: &level0 [leaf]"]
    for level in range(1, 31):
        levels.append(
            "level{level}: &level{level} [*level{previous}, *level{previous}]".format(
                level=level, previous=level - 1
            )
        )
    # This roughly 1 KiB YAML graph would expand to more than one billion leaf
    # references if it reached the JSON encoder.
    shared_value = yaml.safe_load("\n".join(levels))["level30"]
    reana_yaml["inputs"]["parameters"]["value"] = shared_value

    def _unexpected_json_encoding(*args, **kwargs):
        raise AssertionError("the shared graph reached the JSON encoder")

    monkeypatch.setattr(
        "reana_commons.validation.report.json.dumps", _unexpected_json_encoding
    )

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is False
    assert report["errors"][0]["code"] == "serialization"


@pytest.mark.parametrize(
    "value",
    [
        {1: "non-string key"},
        {"set"},
    ],
)
def test_non_json_container_values_are_rejected(value):
    """Only JSON mappings, arrays, and scalar types cross the boundary."""
    reana_yaml = _serial_spec()
    reana_yaml["inputs"]["parameters"]["value"] = value

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is False
    assert report["errors"][0]["code"] == "serialization"


def test_json_encoder_compatible_subclasses_and_tuples_are_supported():
    """Loader-produced JSON-compatible values cross the serialization boundary."""

    class StringValue(str):
        pass

    class IntegerValue(int):
        pass

    class FloatValue(float):
        pass

    class MappingValue(dict):
        pass

    class SequenceValue(list):
        pass

    reana_yaml = _serial_spec()
    reana_yaml["inputs"]["parameters"][StringValue("value")] = MappingValue(
        nested=SequenceValue(
            [StringValue("input.txt"), IntegerValue(1), FloatValue(1.5)]
        ),
        tuple_value=(StringValue("one"), StringValue("two")),
    )

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is True
    assert report["errors"] == []


def test_repeated_immutable_tuples_are_supported():
    """Python may reuse immutable tuples that JSON can safely encode."""
    repeated = ("-v", "-x")
    empty = ()
    reana_yaml = _serial_spec()
    reana_yaml["inputs"]["parameters"].update(
        first=repeated,
        second=repeated,
        first_empty=empty,
        second_empty=empty,
    )

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is True
    assert report["errors"] == []


def test_scalar_yaml_aliases_remain_supported():
    """Reusing an immutable JSON scalar cannot amplify JSON traversal."""
    values = yaml.safe_load("value: &value text\ncopy: *value\n")
    reana_yaml = _serial_spec()
    reana_yaml["inputs"]["parameters"].update(values)

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is True


def test_disallowed_image_reports_image_error():
    """An image outside the allowlist is reported with a stable code."""
    reana_yaml = _serial_spec(image="evil.io/malware:latest")
    policy = {
        "vetted_images_enabled": True,
        "vetted_images_allowlist": [ALLOWED_IMAGE],
    }
    report = validate_serialized_spec(reana_yaml, policy)
    assert report["valid"] is False
    codes = [error["code"] for error in report["errors"]]
    assert "image_not_allowed" in codes


def test_allowed_image_passes_vetting():
    """An image present in the allowlist validates."""
    reana_yaml = _serial_spec()
    policy = {
        "vetted_images_enabled": True,
        "vetted_images_allowlist": [ALLOWED_IMAGE],
    }
    report = validate_serialized_spec(reana_yaml, policy)
    assert report["valid"] is True


def test_unsupported_compute_backend_reports_error():
    """A step on a backend the cluster does not support is rejected.

    This is one of the cluster-capability checks that used to be opt-in behind
    the client's ``--server-capabilities`` flag and now always runs server-side.
    """
    reana_yaml = _serial_spec()
    reana_yaml["workflow"]["specification"]["steps"][0][
        "compute_backend"
    ] = "htcondorcern"
    report = validate_serialized_spec(
        reana_yaml, policy={"supported_backends": ["kubernetes"]}
    )
    assert report["valid"] is False
    assert any(error["code"] == "compute_backend" for error in report["errors"])


def test_supported_compute_backend_passes():
    """A step on a supported backend validates."""
    reana_yaml = _serial_spec()
    reana_yaml["workflow"]["specification"]["steps"][0][
        "compute_backend"
    ] = "kubernetes"
    report = validate_serialized_spec(
        reana_yaml, policy={"supported_backends": ["kubernetes"]}
    )
    assert report["valid"] is True


def test_disallowed_workspace_root_path_reports_error():
    """A workspace root_path outside the cluster allowlist is rejected.

    Another former ``--server-capabilities`` check now always performed
    server-side.
    """
    reana_yaml = _serial_spec()
    reana_yaml["workspace"] = {"root_path": "/eos/forbidden"}
    report = validate_serialized_spec(
        reana_yaml, policy={"workspace_paths": ["/var/reana"]}
    )
    assert report["valid"] is False
    assert any(error["code"] == "workspace" for error in report["errors"])


def test_allowed_workspace_root_path_passes():
    """A workspace root_path within the cluster allowlist validates."""
    reana_yaml = _serial_spec()
    reana_yaml["workspace"] = {"root_path": "/var/reana/users"}
    report = validate_serialized_spec(
        reana_yaml, policy={"workspace_paths": ["/var/reana"]}
    )
    assert report["valid"] is True


def test_schema_error_short_circuits():
    """A critical schema error stops further checks and returns a single error."""
    report = validate_serialized_spec({"workflow": {}}, policy={})
    assert report["valid"] is False
    assert len(report["errors"]) == 1
    assert report["errors"][0]["code"] == "schema"


def test_schema_combinator_error_is_targeted_and_bounded():
    """A combinator failure does not echo the expanded workflow object."""
    reana_yaml = _serial_spec()
    del reana_yaml["workflow"]["type"]
    reana_yaml["workflow"]["specification"]["steps"] *= 200

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is False
    assert len(report["errors"][0]["message"]) <= 503
    assert "steps" not in report["errors"][0]["message"]


def test_parameter_warnings_share_one_global_report_budget():
    """Unused parameters cannot create an unbounded response or intermediate list."""
    reana_yaml = _serial_spec()
    reana_yaml["inputs"]["parameters"] = {
        "unused_{:04d}".format(index): index
        for index in range(MAX_VALIDATION_REPORT_ENTRIES + 50)
    }

    report = validate_serialized_spec(reana_yaml, policy={})

    assert report["valid"] is True
    assert len(report["errors"]) + len(report["warnings"]) == (
        MAX_VALIDATION_REPORT_ENTRIES
    )
    assert report["warnings"][-1] == {
        "code": "report_truncated",
        "message": "Additional validation findings were omitted.",
        "path": "",
    }


def test_retention_period_over_limit_reports_error():
    """A retention rule above the configured maximum is rejected."""
    reana_yaml = _serial_spec()
    reana_yaml.setdefault("workspace", {})["retention_days"] = {"**/*.tmp": 30}
    report = validate_serialized_spec(reana_yaml, policy={"max_retention_period": 10})
    assert report["valid"] is False
    assert any(error["code"] == "retention" for error in report["errors"])


# --- unit checks of the shared building blocks -----------------------------


@pytest.mark.parametrize(
    "files,directories",
    [
        (["../escape.txt"], []),
        (["/abs/path.txt"], []),
        (["data.txt"], ["data.txt"]),  # declared twice (file + directory tree)
    ],
)
def test_validate_inputs_rejects_unsafe_paths(files, directories):
    """Absolute, traversing, or duplicated input paths are rejected."""
    reana_yaml = {"inputs": {"files": files, "directories": directories}}
    with pytest.raises(REANAValidationError):
        validate_inputs(reana_yaml)


def test_validate_inputs_accepts_relative_paths():
    """Distinct relative input paths validate."""
    reana_yaml = {"inputs": {"files": ["a.txt"], "directories": ["b"]}}
    validate_inputs(reana_yaml)


def test_validate_inputs_bounds_combined_declarations():
    """Files and directories share one bounded declaration budget."""
    files = [f"file-{index}" for index in range(MAX_INPUT_PATH_DECLARATIONS)]
    validate_inputs({"inputs": {"files": files, "directories": []}})

    reana_yaml = {
        "workflow": {"type": "serial", "specification": {"steps": []}},
        "inputs": {"files": files, "directories": ["one-too-many"]},
    }
    report = validate_serialized_spec(reana_yaml, policy={})
    assert report["valid"] is False
    assert report["errors"] == [
        {
            "code": "input_path",
            "message": "Too many input paths declared (maximum is 1000)",
            "path": "",
        }
    ]


def test_validate_inputs_detects_nested_paths_with_sorted_scan():
    """A parent declaration is detected without quadratic pair generation."""
    reana_yaml = {
        "inputs": {
            "files": ["unrelated", "data/nested/file.txt"],
            "directories": ["data"],
        }
    }
    with pytest.raises(REANAValidationError, match="data.*data/nested/file.txt"):
        validate_inputs(reana_yaml)


def test_validate_retention_rule_limits():
    """Retention rule path safety and the maximum period are both enforced."""
    validate_retention_rule("data/*.tmp", 5, max_retention_period=10)
    with pytest.raises(REANAValidationError):
        validate_retention_rule("/abs/*.tmp", 5)
    with pytest.raises(REANAValidationError):
        validate_retention_rule("../*.tmp", 5)
    with pytest.raises(REANAValidationError):
        validate_retention_rule("data/*.tmp", 30, max_retention_period=10)


def test_validate_images_disabled_is_noop():
    """When vetting is disabled, any image is accepted."""
    reana_yaml = {
        "workflow": {
            "type": "serial",
            "specification": {"steps": [{"environment": "anything:latest"}]},
        }
    }
    validate_images(reana_yaml, enabled=False, allowlist=[])


def test_validate_dask_limits_blocks_when_disabled():
    """Requesting Dask resources on a cluster without Dask is rejected."""
    reana_yaml = {"workflow": {"type": "serial", "resources": {"dask": {}}}}
    # An empty dask block still counts as requesting dask resources.
    reana_yaml["workflow"]["resources"]["dask"] = {"number_of_workers": 1}
    with pytest.raises(REANAValidationError):
        validate_dask_limits(reana_yaml, {"enabled": False})


def test_malformed_dask_max_memory_raises_catchable_validation_error():
    """A malformed operator Dask ``max_*`` limit surfaces as a structured error.

    ``kubernetes_memory_to_bytes`` raises ``REANAKubernetesWrongMemoryFormat``
    (a plain ``Exception``, not a ``REANAValidationError``). ``validate_dask_limits``
    must re-raise it as a ``REANAValidationError`` so the report's ``_check``
    records it as a ``dask`` error rather than letting it escape as an unhandled
    500. (Asserting the catchable type is what proves the fix: the raw
    ``REANAKubernetesWrongMemoryFormat`` would not satisfy this ``raises``.)
    """
    reana_yaml = {
        "workflow": {
            "type": "serial",
            "resources": {"dask": {"single_worker_memory": "2Gi"}},
        }
    }
    dask_config = {
        "enabled": True,
        "max_single_worker_memory": "not-a-size",  # operator misconfiguration
        "max_memory_limit": "16Gi",
        "default_single_worker_memory": "2Gi",
        "default_number_of_workers": 1,
        "max_number_of_workers": 4,
        "default_single_worker_threads": 1,
        "max_single_worker_threads": 4,
    }
    with pytest.raises(REANAValidationError):
        validate_dask_limits(reana_yaml, dask_config)


def test_cwl_validation_does_not_touch_the_filesystem():
    """Validating a serialized CWL spec is pure -- it never reads workflow.file.

    A bogus / shell-metacharacter ``workflow.file`` path used to be interpolated
    into ``cwltool --validate`` and run with ``shell=True``; the serialized
    validator must not look at it at all (the on-disk parse is a load-time
    concern handled in the sandbox).
    """
    reana_yaml = {
        "version": "0.6.0",
        "workflow": {
            "type": "cwl",
            "file": "/nonexistent/evil.cwl;touch pwned",
            "specification": {
                "$graph": [
                    {
                        "id": "main",
                        "class": "Workflow",
                        "inputs": [],
                        "outputs": [],
                        "steps": [],
                    }
                ]
            },
        },
        "inputs": {"parameters": {}},
    }
    # Must not raise (no FileNotFound / SystemExit / shell-out) and must produce
    # a structured report.
    report = validate_serialized_spec(reana_yaml, policy={})
    assert "valid" in report
    assert all(error["code"] != "internal" for error in report["errors"])
