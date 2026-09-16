# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons concurrency limits configuration tests."""

import importlib

import pytest

import reana_commons.config
from reana_commons.errors import REANAConfigurationError

CAP_ENV_VARS = [
    "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS",
    "REANA_MAX_CONCURRENT_K8S_BATCH_WORKFLOWS",
    "REANA_MAX_CONCURRENT_EXTERNAL_BATCH_WORKFLOWS",
    "REANA_MAX_CONCURRENT_DASK_WORKFLOWS",
    "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND",
]


@pytest.fixture
def reload_config(monkeypatch):
    """Reload the configuration module with the given environment."""

    def _reload(**env):
        for var in CAP_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        for var, value in env.items():
            monkeypatch.setenv(var, value)
        return importlib.reload(reana_commons.config)

    yield _reload
    # Leave the module in its default state for the other tests.
    for var in CAP_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    importlib.reload(reana_commons.config)


def test_caps_default(reload_config):
    """Unset caps fall back to their built-in defaults."""
    config = reload_config()

    assert config.get_concurrent_workflows_cap("kubernetes") == 30
    assert config.get_concurrent_workflows_cap("dask") == 5
    # Any backend without an override falls back to the external default, not
    # to the Kubernetes one.
    assert config.get_concurrent_workflows_cap("htcondorcern") == 200
    assert config.get_concurrent_workflows_cap("unknown-backend") == 200


def test_legacy_cap_applies_to_kubernetes(reload_config):
    """The deprecated cluster-wide cap keeps capping Kubernetes workflows."""
    config = reload_config(REANA_MAX_CONCURRENT_BATCH_WORKFLOWS="10")

    assert config.get_concurrent_workflows_cap("kubernetes") == 10

    config = reload_config(
        REANA_MAX_CONCURRENT_BATCH_WORKFLOWS="10",
        REANA_MAX_CONCURRENT_K8S_BATCH_WORKFLOWS="7",
    )

    assert config.get_concurrent_workflows_cap("kubernetes") == 7


def test_per_backend_override(reload_config):
    """Per-backend overrides take precedence over the defaults."""
    config = reload_config(
        REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND=(
            '{"htcondorcern": 3, "kubernetes": 4}'
        )
    )

    assert config.get_concurrent_workflows_cap("htcondorcern") == 3
    assert config.get_concurrent_workflows_cap("kubernetes") == 4
    assert config.get_concurrent_workflows_cap("slurmcern") == 200


def test_numeric_string_caps_are_coerced(reload_config):
    """Quoted numbers, easy to write in a values file, are read as integers.

    Left as strings they would reach the scheduler and raise a ``TypeError``
    on comparison inside the consumer callback, wedging the scheduler.
    """
    config = reload_config(
        REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND='{"htcondorcern": "3"}'
    )

    assert config.get_concurrent_workflows_cap("htcondorcern") == 3


def test_zero_cap_closes_the_resource(reload_config):
    """A cap of zero is preserved and means that the resource is closed."""
    config = reload_config(
        REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND='{"htcondorcern": 0}',
        REANA_MAX_CONCURRENT_DASK_WORKFLOWS="0",
    )

    assert config.get_concurrent_workflows_cap("htcondorcern") == 0
    assert config.get_concurrent_workflows_cap("dask") == 0


@pytest.mark.parametrize(
    "env,expected_message",
    [
        (
            {"REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND": "not-json"},
            "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND must be a JSON object",
        ),
        (
            {"REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND": '["htcondorcern"]'},
            "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND must be a JSON object",
        ),
        (
            {
                "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND": '{"htcondorcern": -1}'
            },
            "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND['htcondorcern']",
        ),
        (
            {
                "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND": (
                    '{"htcondorcern": "three"}'
                )
            },
            "REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND['htcondorcern']",
        ),
        (
            {"REANA_MAX_CONCURRENT_BATCH_WORKFLOWS_PER_BACKEND": '{"dask": 5}'},
            "REANA_MAX_CONCURRENT_DASK_WORKFLOWS",
        ),
        (
            {"REANA_MAX_CONCURRENT_DASK_WORKFLOWS": "many"},
            "REANA_MAX_CONCURRENT_DASK_WORKFLOWS must be a non-negative integer",
        ),
        (
            {"REANA_MAX_CONCURRENT_K8S_BATCH_WORKFLOWS": "-5"},
            "REANA_MAX_CONCURRENT_K8S_BATCH_WORKFLOWS must be a non-negative integer",
        ),
    ],
)
def test_invalid_caps_fail_fast(reload_config, env, expected_message):
    """Misconfigured caps are rejected at load time, naming the offender."""
    with pytest.raises(REANAConfigurationError) as exception:
        reload_config(**env)

    assert expected_message in str(exception.value.message)
