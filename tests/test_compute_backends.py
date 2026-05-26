# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for compute backend utilities."""

import pytest

from reana_commons.validation.compute_backends import workflow_uses_kubernetes


def _serial_spec(steps):
    return {"workflow": {"type": "serial", "specification": {"steps": steps}}}


def _snakemake_spec(steps):
    return {"workflow": {"type": "snakemake", "specification": {"steps": steps}}}


def _yadage_spec(stages):
    return {"workflow": {"type": "yadage", "specification": {"stages": stages}}}


def _cwl_spec(steps, as_list=False):
    graph = {"steps": steps}
    if as_list:
        graph = [graph]
    return {"workflow": {"type": "cwl", "specification": {"$graph": graph}}}


def _yadage_stage(name, backend=None):
    resources = [{"compute_backend": backend}] if backend else []
    return {
        "name": name,
        "scheduler": {
            "step": {"environment": {"resources": resources}},
        },
    }


def _cwl_step(name, backend=None):
    hints = []
    if backend is not None:
        hints = [{"class": "reana", "compute_backend": backend}]
    return {"id": name, "hints": hints}


# --- serial ---


@pytest.mark.parametrize(
    "steps, expected",
    [
        ([{"name": "step1"}], True),  # no backend -> assumes kubernetes used
        ([{"name": "step1", "compute_backend": "kubernetes"}], True),
        ([{"name": "step1", "compute_backend": "htcondor"}], False),
        ([{"name": "step1", "compute_backend": "slurm"}], False),
        (
            [
                {"name": "step1", "compute_backend": "htcondor"},
                {"name": "step2"},  # no backend -> counts as using kubernetes
            ],
            True,  # hybrid workflow
        ),
        (
            [
                {"name": "step1", "compute_backend": "htcondor"},
                {"name": "step2", "compute_backend": "slurm"},
            ],
            False,  # non-kubernetes workflow
        ),
        ([], False),  # no steps -> non-kubernetes workflow
    ],
)
def test_serial_workflow_uses_kubernetes(steps, expected):
    assert workflow_uses_kubernetes(_serial_spec(steps)) is expected


# --- snakemake ---


@pytest.mark.parametrize(
    "steps, expected",
    [
        ([{"name": "step1"}], True),
        ([{"name": "step1", "compute_backend": "htcondor"}], False),
        (
            [
                {"name": "step1", "compute_backend": "htcondor"},
                {"name": "step2", "compute_backend": "kubernetes"},
            ],
            True,
        ),
    ],
)
def test_snakemake_workflow_uses_kubernetes(steps, expected):
    assert workflow_uses_kubernetes(_snakemake_spec(steps)) is expected


# --- yadage ---


@pytest.mark.parametrize(
    "stages, expected",
    [
        ([_yadage_stage("s1")], True),  # no backend -> assumes kubernetes used
        ([_yadage_stage("s1", "kubernetes")], True),
        ([_yadage_stage("s1", "htcondor")], False),
        ([_yadage_stage("s1", "slurm")], False),
        (
            [_yadage_stage("s1", "htcondor"), _yadage_stage("s2")],
            True,
        ),  # hybrid workflow
        ([_yadage_stage("s1", "htcondor"), _yadage_stage("s2", "slurm")], False),
        ([], False),
    ],
)
def test_yadage_workflow_uses_kubernetes(stages, expected):
    assert workflow_uses_kubernetes(_yadage_spec(stages)) is expected


def test_yadage_nested_workflow_uses_kubernetes():
    """Nested yadage workflows are recursively checked."""
    nested_stage = _yadage_stage("inner", "htcondor")
    outer_stage = {
        "name": "outer",
        "scheduler": {"workflow": {"stages": [nested_stage]}},
    }
    assert workflow_uses_kubernetes(_yadage_spec([outer_stage])) is False

    nested_k8s = _yadage_stage("inner")  # defaults to kubernetes
    outer_k8s = {
        "name": "outer",
        "scheduler": {"workflow": {"stages": [nested_k8s]}},
    }
    assert workflow_uses_kubernetes(_yadage_spec([outer_k8s])) is True


# --- cwl ---


@pytest.mark.parametrize(
    "steps, as_list, expected",
    [
        ([_cwl_step("s1")], False, True),  # no backend -> assumes kubernetes used
        ([_cwl_step("s1", "kubernetes")], False, True),
        ([_cwl_step("s1", "htcondor")], False, False),
        (
            [_cwl_step("s1", "htcondor"), _cwl_step("s2")],
            False,
            True,
        ),  # hybrid workflow
        ([_cwl_step("s1", "htcondor")], True, False),  # list form
        ([_cwl_step("s1")], True, True),
        ([], False, False),
    ],
)
def test_cwl_workflow_uses_kubernetes(steps, as_list, expected):
    assert workflow_uses_kubernetes(_cwl_spec(steps, as_list=as_list)) is expected


# --- unknown workflow type ---


def test_unknown_workflow_type_defaults_to_kubernetes():
    spec = {"workflow": {"type": "unknown_future_type", "specification": {}}}
    assert workflow_uses_kubernetes(spec) is True
