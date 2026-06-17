# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test helpers around :class:`reana_commons.api_client.BaseAPIClient`."""

from __future__ import absolute_import, print_function

from mock import Mock

from reana_commons.api_client import BaseAPIClient


def make_mock_api_client(component):
    """Return a factory that builds a mocked Bravado client for ``component``."""
    mock_response, mock_http_response = {}, Mock()
    mock_http_response.status_code = 200
    mock_http_response.raw_bytes = b"Sample downloaded data"

    def mock_api_client(
        mock_response=mock_response, mock_http_response=mock_http_response
    ):
        mock_http_client, mock_result = Mock(), Mock()
        mock_result.result.return_value = (mock_response, mock_http_response)
        mock_http_client.request.return_value = mock_result
        # Tests using this helper deliberately replace the HTTP transport and
        # must not depend on process-wide service discovery.  Supplying an
        # explicit, non-routable URL keeps that contract while production
        # clients can still fail fast when REANA_SERVER_URL is missing.
        mock_api_client = BaseAPIClient(
            component,
            http_client=mock_http_client,
            server_url="http://mock-reana.invalid",
        )
        return mock_api_client._client

    return mock_api_client
