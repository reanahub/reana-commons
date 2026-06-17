# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Authentication contract checks for the REANA Server OpenAPI spec."""

import json
from importlib.resources import files


HTTP_METHODS = frozenset(
    {"delete", "get", "head", "options", "patch", "post", "put"}
)
BEARER_SECURITY = [{"BearerAuth": []}]

# These operations deliberately do not use an Authorization Bearer token.
# The quota endpoints authenticate with their documented
# X-Quota-Management-Secret header; the remaining endpoints are public or
# belong to the browser-cookie BFF flow.
NON_BEARER_OPERATIONS = frozenset(
    {
        ("GET", "/api/.well-known/openid-configuration"),
        ("GET", "/api/config"),
        ("GET", "/api/login"),
        ("POST", "/api/logout"),
        ("GET", "/api/oauth/callback"),
        ("GET", "/api/ping"),
        ("GET", "/api/quota"),
        ("PATCH", "/api/quota"),
        ("POST", "/api/quota"),
    }
)


def _load_reana_server_spec():
    """Load the packaged REANA Server Swagger specification."""
    spec_path = (
        files("reana_commons") / "openapi_specifications" / "reana_server.json"
    )
    return json.loads(spec_path.read_text())


def _operations(spec):
    """Yield ``((METHOD, path), operation)`` pairs from a Swagger spec."""
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS:
                yield (method.upper(), path), operation


def test_all_reana_server_operations_have_an_authentication_classification():
    """Default every operation to Bearer and audit every non-Bearer exception."""
    spec = _load_reana_server_spec()
    assert spec["security"] == BEARER_SECURITY

    operations = dict(_operations(spec))
    non_bearer_operations = {
        key for key, operation in operations.items() if operation.get("security") == []
    }

    # Exact equality makes adding or removing an exemption an intentional contract
    # change. It also proves that every expected public/BFF operation still exists.
    assert non_bearer_operations == NON_BEARER_OPERATIONS

    unclassified = {}
    for key, operation in operations.items():
        effective_security = operation.get("security", spec.get("security"))
        if effective_security not in (BEARER_SECURITY, []):
            unclassified[key] = effective_security

    assert unclassified == {}


def test_reana_server_spec_does_not_restore_retired_invenio_auth_routes():
    """Reject retired Invenio routes regardless of prefix or trailing slash."""
    paths = _load_reana_server_spec().get("paths", {})
    retired_route_fragments = ("signin", "signup", "confirm")

    offenders = sorted(
        path
        for path in paths
        if any(fragment in path.lower() for fragment in retired_route_fragments)
    )

    assert offenders == []
