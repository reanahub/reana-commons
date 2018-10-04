# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# REANA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# REANA; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307, USA.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization or
# submit itself to any jurisdiction.
"""REANA REST API base client."""

import json
import os

import pkg_resources
from bravado.client import SwaggerClient


class BaseAPIClient(object):
    """REANA API client code."""

    def __init__(self, component, server_data, http_client=None):
        """Create a OpenAPI client for a REANA component."""
        self.component = component
        server_url, spec_file = server_data
        json_spec = self._get_spec(spec_file)
        self._client = SwaggerClient.from_spec(
            json_spec,
            http_client=http_client,
            config={'also_return_response': True})
        self._client.swagger_spec.api_url = server_url
        self.server_url = server_url

    def _get_spec(self, spec_file):
        """Get json specification from package data."""
        spec_file_path = os.path.join(
            pkg_resources.
            resource_filename(
                self.component,
                'openapi_connections'),
            spec_file)

        with open(spec_file_path) as f:
            json_spec = json.load(f)
        return json_spec
