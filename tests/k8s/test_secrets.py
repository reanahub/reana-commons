# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019, 2020, 2021, 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import json
from uuid import uuid4

import pytest
from kubernetes import client
from kubernetes.client.rest import ApiException
from mock import DEFAULT, Mock, patch

from reana_commons.errors import REANASecretAlreadyExists, REANASecretDoesNotExist
from reana_commons.k8s.secrets import Secret, UserSecrets, UserSecretsStore


def test_secret_encoding():
    """Test the correct encoding of secret values."""
    s = Secret("name", type_="env", value="secret")
    assert s.value_bytes == b"secret"
    assert s.value_str == "secret"

    s = Secret("name", type_="env", value=b"secret2")
    assert s.value_bytes == b"secret2"
    assert s.value_str == "secret2"

    s.set_value(b"secret3")
    assert s.value_bytes == b"secret3"
    assert s.value_str == "secret3"

    s.set_value("secret4")
    assert s.value_bytes == b"secret4"
    assert s.value_str == "secret4"


def test_user_secrets_add():
    """Test adding user secrets."""
    us = UserSecrets(user_id="123", k8s_secret_name="asd")
    s = Secret("secret_name", "file", "hello!")
    us.add_secrets([s])
    assert us.get_secret("secret_name") == s


def test_user_secrets_delete():
    """Test deleting user secrets."""
    s = Secret("secret_name", "file", "hello!")
    us = UserSecrets(user_id="123", k8s_secret_name="asd", secrets=[s])
    assert us.get_secret("secret_name") is not None
    us.delete_secrets(["secret_name"])
    assert us.get_secret("secret_name") is None


def test_user_secrets_to_k8s():
    """Test converting user secrets to k8s secrets."""
    s = Secret("secret_name", "file", b"hello!")
    s2 = Secret("secret_name_2", "env", "hello env!")
    us = UserSecrets(user_id="123", k8s_secret_name="k8s_secret")
    us.add_secrets([s, s2])
    k8s_secret = us.to_k8s_secret()

    assert k8s_secret.metadata.name == "k8s_secret"
    secret_types = json.loads(k8s_secret.metadata.annotations["secrets_types"])
    assert secret_types["secret_name"] == "file"
    assert secret_types["secret_name_2"] == "env"
    assert k8s_secret.data["secret_name"] == "aGVsbG8h"
    assert k8s_secret.data["secret_name_2"] == "aGVsbG8gZW52IQ=="


def test_user_secrets_from_k8s():
    """Test converting k8s secrets to user secrets."""
    k8s_secret = client.V1Secret(
        metadata=client.V1ObjectMeta(
            name="k8s_secret",
            annotations={
                "secrets_types": json.dumps(
                    {"secret_name": "file", "secret_name_2": "env"}
                )
            },
        ),
        data={
            "secret_name": "aGVsbG8h",
            "secret_name_2": "aGVsbG8gZW52IQ==",
        },
    )

    us = UserSecrets.from_k8s_secret("123", k8s_secret)
    assert us.get_secret("secret_name").name == "secret_name"
    assert us.get_secret("secret_name").type_ == "file"
    assert us.get_secret("secret_name").value_str == "hello!"

    assert us.get_secret("secret_name_2").name == "secret_name_2"
    assert us.get_secret("secret_name_2").type_ == "env"
    assert us.get_secret("secret_name_2").value_str == "hello env!"

    assert len(us.secrets) == 2
    assert us.user_id == "123"
    assert us.k8s_secret_name == "k8s_secret"


def test_user_secrets_full_conversion_from_to_k8s():
    """Test full conversion from and to k8s secrets."""
    s = Secret("secret_name", "file", b"hello!")
    s2 = Secret("secret_name_2", "env", "hello env!")
    us = UserSecrets(user_id="123", k8s_secret_name="k8s_secret")
    us.add_secrets([s, s2])

    k8s_secret = us.to_k8s_secret()
    us_from_k8s = UserSecrets.from_k8s_secret("123", k8s_secret)

    assert us.user_id == us_from_k8s.user_id
    assert us.secrets == us_from_k8s.secrets


def test_create_secret():
    """Test creation of user secrets."""
    corev1_api_client = Mock()
    corev1_api_client.read_namespaced_secret = Mock(
        side_effect=ApiException(reason="Secret does not exist.", status=404)
    )
    secrets = [Secret(name="secret", type_="env", value="secret")]
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client", corev1_api_client
    ):
        user_secrets = UserSecretsStore.fetch(uuid4())
        user_secrets.add_secrets(secrets)
        UserSecretsStore.update(user_secrets)
        corev1_api_client.create_namespaced_secret.assert_called_once()
        corev1_api_client.replace_namespaced_secret.assert_called_once()


def test_create_existing_secrets_fail(
    corev1_api_client_with_user_secrets, user_secrets, no_db_user
):
    """Test create secrets which already exist without overwrite."""
    secret_name = next(iter(user_secrets.keys()))
    secrets = [Secret(name=secret_name, type_="env", value="secret")]
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ) as api_client:
        user_secrets = UserSecretsStore.fetch(no_db_user)
        with pytest.raises(REANASecretAlreadyExists):
            user_secrets.add_secrets(secrets)
        api_client.replace_namespaced_secret.assert_not_called()


def test_overwrite_secret(
    corev1_api_client_with_user_secrets, user_secrets, no_db_user
):
    """Test overwriting secrets."""
    secret_name = next(iter(user_secrets.keys()))
    secrets = [Secret(name=secret_name, type_="env", value="secret")]
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ) as api_client:
        user_secrets = UserSecretsStore.fetch(no_db_user.id_)
        user_secrets.add_secrets(secrets, overwrite=True)
        UserSecretsStore.update(user_secrets)
        api_client.replace_namespaced_secret.assert_called()


def test_delete_secrets(corev1_api_client_with_user_secrets, user_secrets, no_db_user):
    """Test deletion of user secrets."""
    secret_names_list = list(user_secrets.keys())
    with patch(
        "reana_commons.k8s.secrets." "current_k8s_corev1_api_client",
        corev1_api_client_with_user_secrets(user_secrets),
    ):
        user_secrets = UserSecretsStore.fetch(no_db_user.id_)
        deleted_secrets = set(user_secrets.delete_secrets(secret_names_list))
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
        user_secrets = UserSecretsStore.fetch(no_db_user.id_)
        secret_name = "unknown-secret"
        with pytest.raises(REANASecretDoesNotExist):
            user_secrets.delete_secrets([secret_name])
        api_client.replace_namespaced_secret.assert_not_called()
