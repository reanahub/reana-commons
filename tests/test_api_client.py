# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons API client tests."""

import io
import json
import sys
from unittest import mock

if sys.version_info >= (3, 9):
    from importlib.resources import files
else:
    from importlib_resources import files

import pytest
from bravado.client import SwaggerClient
from bravado.testing.response_mocks import IncomingResponseMock
from bravado_core.response import unmarshal_response

from reana_commons.api_client import (
    JobControllerAPIClient,
    StreamingMultipartBody,
)


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


def test_streaming_multipart_body_never_reads_a_file_without_a_bound():
    """Bravado file uploads must not use requests' eager ``read()`` encoder."""

    class BoundedReader(io.BytesIO):
        def read(self, size=-1):
            assert size > 0
            return super().read(size)

    source = BoundedReader(b"bundle contents")
    body = StreamingMultipartBody([("bundle", ("validation-bundle.zip", source))])
    encoded = b"".join(body)

    assert len(encoded) == len(body)
    assert b'name="bundle"' in encoded
    assert b'filename="validation-bundle.zip"' in encoded
    assert b"bundle contents" in encoded


def test_validation_load_error_accepts_null_reana_specification():
    """Bravado accepts the structured report returned for unloadable YAML."""
    spec_resource = (
        files("reana_commons") / "openapi_specifications" / "reana_server.json"
    )
    client = SwaggerClient.from_spec(
        json.loads(spec_resource.read_text()),
        config={"validate_responses": True},
    )
    report = {
        "valid": False,
        "reana_specification": None,
        "errors": [{"code": "load", "message": "Could not load YAML."}],
        "warnings": [],
    }
    response = IncomingResponseMock(
        status_code=200,
        headers={"content-type": "application/json"},
        json=lambda: report,
    )

    result = unmarshal_response(
        response,
        client.api.validate_workflow_specification.operation,
    )

    assert result["reana_specification"] is None
    assert result["errors"][0]["code"] == "load"


@pytest.mark.parametrize(
    "secret_names,expected_in_spec",
    [
        (None, False),  # No allowlist requested: omitted from the request.
        ([], True),  # Explicitly expose no secrets.
        (["alpha", "beta"], True),  # Forward the allowlist verbatim.
    ],
)
def test_submit_forwards_secret_names(secret_names, expected_in_spec):
    """``secret_names`` must be forwarded even when the allowlist is empty."""
    client = _make_client()
    client.submit(image="busybox", cmd="ls", secret_names=secret_names)
    job_spec = client._client.jobs.create_job.call_args.kwargs["job"]
    if expected_in_spec:
        assert job_spec["secret_names"] == secret_names
    else:
        assert "secret_names" not in job_spec
