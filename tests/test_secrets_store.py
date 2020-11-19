# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import json

import pytest
from kubernetes import client
from kubernetes.client.rest import ApiException
from mock import DEFAULT, Mock, patch

from reana_commons.errors import REANASecretAlreadyExists, REANASecretDoesNotExist
from reana_commons.k8s.secrets import REANAUserSecretsStore


def test_create_secret(user_secrets, no_db_user):
    """Test creation of user secrets."""
    corev1_api_client = Mock()
    corev1_api_client.read_namespaced_secret = Mock(
        side_effect=ApiException(reason="Secret does not exist.", status=404)
    )
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client", corev1_api_client
    ):
        secrets_store = REANAUserSecretsStore(no_db_user.id_)
        secrets_store.add_secrets(user_secrets)
        corev1_api_client.create_namespaced_secret.assert_called_once()
        corev1_api_client.replace_namespaced_secret.assert_called_once()


def test_create_existing_secrets_fail(
    corev1_api_client_with_user_secrets, user_secrets, no_db_user
):
    """Test create secrets which already exist without overwrite."""
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ) as api_client:
        secrets_store = REANAUserSecretsStore(no_db_user)
        with pytest.raises(REANASecretAlreadyExists):
            secrets_store.add_secrets(user_secrets)
        api_client.replace_namespaced_secret.assert_not_called()


def test_overwrite_secret(
    corev1_api_client_with_user_secrets, user_secrets, no_db_user
):
    """Test overwriting secrets."""
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ) as api_client:
        secrets_store = REANAUserSecretsStore(no_db_user.id_)
        secrets_store.add_secrets(user_secrets, overwrite=True)
        api_client.replace_namespaced_secret.assert_called()


def test_get_secrets(corev1_api_client_with_user_secrets, user_secrets, no_db_user):
    """Test listing user secrests."""
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ):
        secrets_store = REANAUserSecretsStore(no_db_user.id_)
        secrets_list = secrets_store.get_secrets()
        for secret in secrets_list:
            assert user_secrets[secret["name"]]["type"] == secret["type"]


def test_delete_secrets(corev1_api_client_with_user_secrets, user_secrets, no_db_user):
    """Test deletion of user secrets."""
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ):
        secrets_store = REANAUserSecretsStore(no_db_user.id_)
        secret_names_list = user_secrets.keys()
        deleted_secrets = set(secrets_store.delete_secrets(secret_names_list))
        assert bool(deleted_secrets.intersection(secret_names_list)) and not bool(
            deleted_secrets.difference(secret_names_list)
        )


def test_delete_unknown_secret(
    corev1_api_client_with_user_secrets, user_secrets, no_db_user
):
    """Test delete a non existing secret."""
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ) as api_client:
        secrets_store = REANAUserSecretsStore(no_db_user.id_)
        secret_name = "unknown-secret"
        with pytest.raises(REANASecretDoesNotExist):
            secrets_store.delete_secrets([secret_name])
        api_client.replace_namespaced_secret.assert_not_called()
