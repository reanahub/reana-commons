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

"""Pytest configuration for REANA-Commons."""

from __future__ import absolute_import, print_function

import base64
import json
from uuid import uuid4

import pytest
from kubernetes import client
from mock import Mock


@pytest.fixture
def test_user():
    """Test user."""
    user = Mock()
    user.id_ = uuid4()
    return user


@pytest.fixture
def user_secrets():
    """Test user secrets dictionary."""
    keytab_file = base64.b64encode(b'keytab file.')
    user_secrets = {
        "username": {"value": "reanauser",
                     "type": "env"},
        "password": {"value": "1232456",
                     "type": "env"},
        ".keytab": {"value": keytab_file,
                    "type": "file"}
    }
    return user_secrets


@pytest.fixture
def corev1_api_client_with_user_secrets(test_user, user_secrets):
    """Kubernetes CoreV1 api client with user secrets in K8s secret store."""
    corev1_api_client = Mock()
    metadata = client.V1ObjectMeta(name=str(test_user.id))
    metadata.annotations = {'secrets_types': '{}'}
    user_secrets_values = {}
    secrets_types = {}
    for secret_name in user_secrets:
        # Add type metadata to secret store
        secrets_types[secret_name] = \
            user_secrets[secret_name]['type']
        user_secrets_values[secret_name] = \
            user_secrets[secret_name]['value']
    metadata.annotations['secrets_types'] = json.dumps(secrets_types)
    k8s_secrets_store = client.V1Secret(
        api_version="v1",
        metadata=metadata,
        data=user_secrets_values)
    corev1_api_client.read_namespaced_secret = \
        lambda name, namespace: k8s_secrets_store
    return corev1_api_client
