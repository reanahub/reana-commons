# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons API client tests."""

from unittest import mock

import pytest

from reana_commons.api_client import JobControllerAPIClient


def _make_client():
    """Build a ``JobControllerAPIClient`` with a mocked Bravado backend."""
    client = JobControllerAPIClient.__new__(JobControllerAPIClient)
    client._client = mock.MagicMock()
    client._client.jobs.create_job.return_value.result.return_value = (
        {"job_id": "x"},
        mock.Mock(status_code=200),
    )
    return client


@pytest.mark.parametrize(
    "kubernetes_uid,expected_in_spec",
    [
        (0, True),  # Root must reach job-controller so it can refuse it.
        (50, True),  # Below-minimum UIDs must reach job-controller too.
        (1000, True),  # Regular UIDs are forwarded.
        (None, False),  # No UID requested: omitted from the request.
    ],
)
def test_submit_forwards_kubernetes_uid(kubernetes_uid, expected_in_spec):
    """``kubernetes_uid`` must be forwarded even when zero or below minimum.

    Previously the API client used a truthy check, silently dropping UID 0
    before job-controller could refuse it. The check now uses ``is not None``
    so that the configurable minimum-UID guard is honoured for every
    explicit value.
    """
    client = _make_client()
    client.submit(image="busybox", cmd="ls", kubernetes_uid=kubernetes_uid)
    job_spec = client._client.jobs.create_job.call_args.kwargs["job"]
    if expected_in_spec:
        assert job_spec["kubernetes_uid"] == kubernetes_uid
    else:
        assert "kubernetes_uid" not in job_spec
