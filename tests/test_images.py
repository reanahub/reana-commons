# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for reana_commons.validation.images."""

from reana_commons.config import REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE
from reana_commons.validation.images import extract_cwl_images, extract_images

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

IMAGE = "docker.io/library/python:3.12"
IMAGE2 = "docker.io/library/ubuntu:24.04"


def test_snakemake_empty_environment_uses_default_image():
    """Snakemake rules without containers resolve to the configured default."""
    specification = {
        "workflow": {
            "type": "snakemake",
            "specification": {"steps": [{"environment": ""}]},
        }
    }

    assert extract_images(specification) == [REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE]


def test_serial_empty_environment_is_preserved():
    """Default substitution must not affect other workflow engines."""
    specification = {
        "workflow": {
            "type": "serial",
            "specification": {"steps": [{"environment": ""}]},
        }
    }

    assert extract_images(specification) == [""]


def test_null_workflow_specification_has_no_extractable_images():
    """Unexpanded workflow metadata must not crash server-side validation."""
    specification = {
        "workflow": {
            "type": "yadage",
            "specification": None,
        }
    }

    assert extract_images(specification) == []


def _wf(requirements=None, hints=None):
    """Build a minimal CWL workflow dict."""
    wf = {}
    if requirements is not None:
        wf["requirements"] = requirements
    if hints is not None:
        wf["hints"] = hints
    return wf


# ---------------------------------------------------------------------------
# requirements – list form (original behaviour, must keep working)
# ---------------------------------------------------------------------------


def test_requirements_list_form():
    wf = _wf(requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}])
    assert extract_cwl_images(wf) == [IMAGE]


def test_requirements_list_form_no_docker():
    wf = _wf(requirements=[{"class": "ResourceRequirement", "coresMin": 1}])
    assert extract_cwl_images(wf) == []


# ---------------------------------------------------------------------------
# hints – list form (previously bypassed vetting)
# ---------------------------------------------------------------------------


def test_hints_list_form():
    wf = _wf(hints=[{"class": "DockerRequirement", "dockerPull": IMAGE}])
    assert extract_cwl_images(wf) == [IMAGE]


def test_hints_list_form_no_docker():
    wf = _wf(hints=[{"class": "ResourceRequirement", "coresMin": 1}])
    assert extract_cwl_images(wf) == []


# ---------------------------------------------------------------------------
# requirements – mapping form (previously bypassed vetting)
# ---------------------------------------------------------------------------


def test_requirements_mapping_form():
    wf = _wf(requirements={"DockerRequirement": {"dockerPull": IMAGE}})
    assert extract_cwl_images(wf) == [IMAGE]


def test_requirements_mapping_form_no_docker():
    wf = _wf(requirements={"ResourceRequirement": {"coresMin": 1}})
    assert extract_cwl_images(wf) == []


# ---------------------------------------------------------------------------
# hints – mapping form (previously bypassed vetting)
# ---------------------------------------------------------------------------


def test_hints_mapping_form():
    wf = _wf(hints={"DockerRequirement": {"dockerPull": IMAGE}})
    assert extract_cwl_images(wf) == [IMAGE]


# ---------------------------------------------------------------------------
# both requirements and hints present
# ---------------------------------------------------------------------------


def test_requirements_and_hints_both_collected():
    wf = _wf(
        requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}],
        hints=[{"class": "DockerRequirement", "dockerPull": IMAGE2}],
    )
    assert extract_cwl_images(wf) == [IMAGE, IMAGE2]


# ---------------------------------------------------------------------------
# multi-node $graph
# ---------------------------------------------------------------------------


def test_graph_list_multiple_nodes():
    graph = [
        _wf(requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}]),
        _wf(hints=[{"class": "DockerRequirement", "dockerPull": IMAGE2}]),
    ]
    assert extract_cwl_images(graph) == [IMAGE, IMAGE2]


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


def test_empty_workflow():
    assert extract_cwl_images({}) == []


def test_empty_graph_list():
    assert extract_cwl_images([]) == []


def test_single_dict_wrapped_automatically():
    wf = _wf(requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}])
    # passing a plain dict (not a list) must still work
    assert extract_cwl_images(wf) == [IMAGE]


def test_none_requirements_treated_as_empty():
    # node.get("requirements") returns None when value is explicitly null
    wf = {"requirements": None, "hints": None}
    assert extract_cwl_images(wf) == []
