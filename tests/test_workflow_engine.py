# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons workflow-engine utility tests."""

from reana_commons.workflow_engine import (
    REANA_WORKFLOW_RESOURCES_ENV,
    get_workflow_resources,
    set_workflow_resources,
)


def test_workflow_resources_environment_round_trip(monkeypatch):
    """Workflow engines should share one environment-variable API."""
    monkeypatch.delenv(REANA_WORKFLOW_RESOURCES_ENV, raising=False)
    assert get_workflow_resources() == {}

    set_workflow_resources({"secret_names": ["alpha"]})

    assert get_workflow_resources() == {"secret_names": ["alpha"]}
