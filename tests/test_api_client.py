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
from types import SimpleNamespace
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
    BaseAPIClient,
    JobControllerAPIClient,
    StreamingMultipartBody,
)


@pytest.fixture(autouse=True)
def clear_api_client_cache():
    """Keep transport-cache state from leaking between tests."""
    BaseAPIClient._bravado_client_instances.clear()
    yield
    BaseAPIClient._bravado_client_instances.clear()


def _make_client():
    """Build a ``JobControllerAPIClient`` with a mocked Bravado backend."""
    client = JobControllerAPIClient.__new__(JobControllerAPIClient)
    client._client = mock.MagicMock()
    client._client.jobs.create_job.return_value.result.return_value = (
        {"job_id": "x"},
        mock.Mock(status_code=200),
    )
    return client


@pytest.mark.parametrize("ssl_verify", [True, False, "/etc/reana/ca.pem"])
def test_base_api_client_forwards_tls_verification_policy(ssl_verify, monkeypatch):
    """Generated API calls must use the caller's TLS verification policy."""
    requests_client = mock.Mock()
    requests_client_factory = mock.Mock(return_value=requests_client)
    swagger_client = mock.Mock()
    swagger_client.swagger_spec.http_client = requests_client
    monkeypatch.setattr(
        "reana_commons.api_client.StreamingRequestsClient",
        requests_client_factory,
    )
    from_spec = mock.Mock(return_value=swagger_client)
    monkeypatch.setattr("reana_commons.api_client.SwaggerClient.from_spec", from_spec)
    monkeypatch.setattr(BaseAPIClient, "_get_spec", mock.Mock(return_value={}))
    monkeypatch.setattr(
        "reana_commons.api_client.OPENAPI_SPECS",
        {"reana-server": ("https://reana.example.org", "reana_server.json")},
    )
    BaseAPIClient("reana-server", ssl_verify=ssl_verify)

    assert from_spec.call_args.kwargs["http_client"] is requests_client
    requests_client_factory.assert_called_once_with(ssl_verify=ssl_verify)


def test_base_api_client_rebuilds_transport_when_tls_policy_changes(monkeypatch):
    """A cached generated client must not pin an earlier TLS policy."""
    monkeypatch.setenv("REANA_SERVER_URL", "https://reana.example.org")
    transports = [object(), object()]
    requests_client_factory = mock.Mock(side_effect=transports)
    swagger_clients = [
        SimpleNamespace(swagger_spec=SimpleNamespace(http_client=transport))
        for transport in transports
    ]
    from_spec = mock.Mock(side_effect=swagger_clients)
    monkeypatch.setattr(
        "reana_commons.api_client.StreamingRequestsClient", requests_client_factory
    )
    monkeypatch.setattr("reana_commons.api_client.SwaggerClient.from_spec", from_spec)
    monkeypatch.setattr(BaseAPIClient, "_get_spec", mock.Mock(return_value={}))
    monkeypatch.setattr(
        "reana_commons.api_client.OPENAPI_SPECS",
        {"reana-server": ("https://reana.example.org", "reana_server.json")},
    )
    BaseAPIClient("reana-server", ssl_verify=True)
    BaseAPIClient("reana-server", ssl_verify=True)
    BaseAPIClient("reana-server", ssl_verify="/etc/reana/ca.pem")

    assert requests_client_factory.call_args_list == [
        mock.call(ssl_verify=True),
        mock.call(ssl_verify="/etc/reana/ca.pem"),
    ]
    assert from_spec.call_count == 2


def test_base_api_client_preserves_configured_server_without_env(monkeypatch):
    """An absent environment override must not erase configured API URLs."""
    monkeypatch.delenv("REANA_SERVER_URL", raising=False)
    monkeypatch.setattr(BaseAPIClient, "_get_spec", mock.Mock(return_value={}))
    monkeypatch.setattr(
        "reana_commons.api_client.OPENAPI_SPECS",
        {"reana-server": ("https://configured.example.org", "reana_server.json")},
    )
    swagger_client = mock.Mock()
    swagger_client.swagger_spec.http_client = mock.Mock()
    monkeypatch.setattr(
        "reana_commons.api_client.SwaggerClient.from_spec",
        mock.Mock(return_value=swagger_client),
    )
    client = BaseAPIClient("reana-server")

    assert client.server_url == "https://configured.example.org"
    assert swagger_client.swagger_spec.api_url == "https://configured.example.org"


def test_base_api_client_prefers_explicit_server_url(monkeypatch):
    """An explicitly passed server URL wins over environment and mapping."""
    monkeypatch.setenv("REANA_SERVER_URL", "raw-environment-value")
    monkeypatch.setattr(BaseAPIClient, "_get_spec", mock.Mock(return_value={}))
    specs = {"reana-server": ("https://configured.example.org", "reana_server.json")}
    monkeypatch.setattr("reana_commons.api_client.OPENAPI_SPECS", specs)
    swagger_client = mock.Mock()
    swagger_client.swagger_spec.http_client = mock.Mock()
    monkeypatch.setattr(
        "reana_commons.api_client.SwaggerClient.from_spec",
        mock.Mock(return_value=swagger_client),
    )
    client = BaseAPIClient("reana-server", server_url="https://active.example.org")

    assert client.server_url == "https://active.example.org"
    assert swagger_client.swagger_spec.api_url == "https://active.example.org"
    # Resolving one client must not change what the next client sees.
    assert specs["reana-server"] == (
        "https://configured.example.org",
        "reana_server.json",
    )


def test_base_api_client_isolates_clients_for_different_server_urls(monkeypatch):
    """Creating a second client must not retarget an existing client."""
    transports = [object(), object()]
    swagger_clients = [
        SimpleNamespace(swagger_spec=SimpleNamespace(http_client=transport))
        for transport in transports
    ]
    monkeypatch.setattr(
        "reana_commons.api_client.StreamingRequestsClient", mock.Mock(side_effect=transports)
    )
    from_spec = mock.Mock(side_effect=swagger_clients)
    monkeypatch.setattr("reana_commons.api_client.SwaggerClient.from_spec", from_spec)
    monkeypatch.setattr(BaseAPIClient, "_get_spec", mock.Mock(return_value={}))
    monkeypatch.setattr(
        "reana_commons.api_client.OPENAPI_SPECS",
        {"reana-server": ("https://configured.example.org", "reana_server.json")},
    )

    first = BaseAPIClient("reana-server", server_url="https://first.example.org")
    second = BaseAPIClient("reana-server", server_url="https://second.example.org")

    assert first._client is not second._client
    assert first._client.swagger_spec.api_url == "https://first.example.org"
    assert second._client.swagger_spec.api_url == "https://second.example.org"
    assert from_spec.call_count == 2


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


def test_reana_server_openapi_spec_does_not_declare_query_access_tokens():
    """REANA Server OpenAPI spec must not require token query parameters."""
    spec_path = files("reana_commons") / "openapi_specifications" / "reana_server.json"
    spec = json.loads(spec_path.read_text())

    offenders = []
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            for parameter in operation.get("parameters", []):
                if parameter.get("name") in {"access_token", "user_access_token"}:
                    offenders.append(f"{method.upper()} {path}")

    assert offenders == []


def test_reana_server_openapi_spec_does_not_declare_retired_token_api():
    """REANA Server OpenAPI spec must not expose retired REANA token APIs."""
    spec_path = files("reana_commons") / "openapi_specifications" / "reana_server.json"
    spec = json.loads(spec_path.read_text())

    assert "/api/token" not in spec.get("paths", {})


def test_reana_server_openapi_spec_declares_oidc_authentication_api():
    """REANA Server OpenAPI spec must expose only the current auth contract."""
    spec_path = files("reana_commons") / "openapi_specifications" / "reana_server.json"
    spec = json.loads(spec_path.read_text())
    paths = spec.get("paths", {})

    assert spec["securityDefinitions"]["BearerAuth"] == {
        "description": "OIDC access token using the `Bearer <token>` scheme.",
        "in": "header",
        "name": "Authorization",
        "type": "apiKey",
    }
    assert {
        "/api/.well-known/openid-configuration",
        "/api/login",
        "/api/logout",
        "/api/oauth/callback",
        "/api/workflows/{workflow_id_or_name}/interactive-session-secret",
    } <= paths.keys()
    # Guard against reintroducing the retired Invenio local-auth routes. Match
    # by substring so the check survives prefix/slash drift: the historical
    # routes were ``/signin``, ``/signup/`` and ``/confirm`` (no ``/api`` prefix).
    assert not any(
        token in path for path in paths for token in ("signin", "signup", "confirm")
    )
