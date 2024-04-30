# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019, 2020, 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Kubernetes secrets."""
import base64
import binascii
import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID

from kubernetes import client
from kubernetes.client.rest import ApiException
from reana_commons.config import (
    REANA_RUNTIME_KUBERNETES_NAMESPACE,
    REANA_USER_SECRET_MOUNT_PATH,
)
from reana_commons.errors import REANASecretAlreadyExists, REANASecretDoesNotExist
from reana_commons.k8s.api_client import current_k8s_corev1_api_client
from reana_commons.utils import build_unique_component_name

log = logging.getLogger(__name__)


class Secret:
    """User secret.

    This class accepts either `bytes` or `str` values.
    """

    types = ["env", "file"]

    @classmethod
    def from_base64(cls, name: str, type_: str, value: str):
        """Initialise Secret from base64 encoded value."""
        try:
            decoded = base64.b64decode(value, validate=True)
        except binascii.Error:
            raise ValueError("Invalid base64 value.")
        return cls(name, type_, decoded)

    def __init__(self, name: str, type_: str, value: Union[str, bytes]):
        """Initialise Secret."""
        if type_ not in self.types:
            raise ValueError(f"type_ must be one of: {self.types}")
        self.name: str = name
        self.type_: str = type_
        self.set_value(value)

    @property
    def value_str(self) -> str:
        """Get secret value as string."""
        return self._value_bytes.decode()

    @property
    def value_bytes(self) -> bytes:
        """Get secret value as bytes."""
        return self._value_bytes

    def set_value(self, value: Union[str, bytes]):
        """Set secret value."""
        self._value_bytes = value.encode() if isinstance(value, str) else bytes(value)

    def __eq__(self, other):
        """Check if two secrets are equal."""
        if not isinstance(other, Secret):
            return False
        return (
            self.name == other.name
            and self.type_ == other.type_
            and self._value_bytes == other._value_bytes
        )


class UserSecrets:
    """Collections of secrets of a given user."""

    def __init__(self, user_id: str, k8s_secret_name: str, secrets: List[Secret] = []):
        """Initialise UserSecrets."""
        self.user_id = user_id
        self.k8s_secret_name = k8s_secret_name
        self.secrets = {secret.name: secret for secret in secrets}

    @classmethod
    def from_k8s_secret(cls, user_id: str, k8s_secret: client.V1Secret):
        """Initialise from k8s secret object."""
        secrets = []
        types = json.loads(k8s_secret.metadata.annotations["secrets_types"])
        for secret_name, secret_value in k8s_secret.data.items():
            secrets.append(
                Secret.from_base64(secret_name, types[secret_name], secret_value)
            )
        return cls(
            user_id=user_id,
            k8s_secret_name=k8s_secret.metadata.name,
            secrets=secrets,
        )

    def to_k8s_secret(self) -> client.V1Secret:
        """Return user secrets as Kubernetes secret."""
        secrets_types = {secret.name: secret.type_ for secret in self.secrets.values()}
        k8s_secret = client.V1Secret(
            api_version="v1",
            metadata=client.V1ObjectMeta(
                name=self.k8s_secret_name,
                namespace=REANA_RUNTIME_KUBERNETES_NAMESPACE,
                annotations={"secrets_types": json.dumps(secrets_types)},
            ),
            data={
                secret.name: base64.standard_b64encode(secret.value_bytes).decode()
                for secret in self.secrets.values()
            },
        )
        return k8s_secret

    def add_secrets(self, secrets: Sequence[Secret], overwrite: bool = False):
        """Add new secrets to the user's secrets."""
        for secret in secrets:
            if secret.name in self.secrets and not overwrite:
                raise REANASecretAlreadyExists(
                    "Operation cancelled. Secret {} already exists. "
                    "If you want change it use overwrite".format(secret.name)
                )
            self.secrets[secret.name] = secret

    def delete_secrets(self, names: Sequence[str]) -> List[str]:
        """Delete one or more of users secrets."""
        missing_secrets = [name for name in names if name not in self.secrets]
        if missing_secrets:
            raise REANASecretDoesNotExist(missing_secrets)

        for secret_name in names:
            del self.secrets[secret_name]
        return list(names)

    def get_secret(self, name: str) -> Optional[Secret]:
        """Get secret of given user by name."""
        return self.secrets.get(name)

    def get_secrets(self) -> List[Secret]:
        """List all secrets for a given user."""
        return list(self.secrets.values())

    def get_env_secrets_as_k8s_spec(self) -> List:
        """Get the list of specification items for env-type secrets for k8s.

        Return all environment variable secrets as a list of dicts.

        Object reference: https://github.com/kubernetes-client/python/
        blob/master/kubernetes/docs/V1EnvVar.md.
        """
        env_secrets = []
        for secret in self.secrets.values():
            if secret.type_ == "env":
                env_secrets.append(
                    {
                        "name": secret.name,
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": self.k8s_secret_name,
                                "key": secret.name,
                            }
                        },
                    }
                )
        return env_secrets

    def get_secrets_volume_mount_as_k8s_spec(self) -> Dict[str, Any]:
        """Return a volume mount object for the file-type secrets."""
        return {
            "name": self.k8s_secret_name,
            "mountPath": REANA_USER_SECRET_MOUNT_PATH,
            "readOnly": True,
        }

    def get_file_secrets_volume_as_k8s_specs(self):
        """Get the k8s specification of a volume for file-type secrets.

        Return the specification of volume adapted from a k8s secret,
        specifying the secrets that should be mounted as files.

        Object reference: https://github.com/kubernetes-client/python/
        blob/master/kubernetes/docs/V1SecretVolumeSource.md
        """
        file_secrets = []
        for secret in self.secrets.values():
            if secret.type_ == "file":
                file_secrets.append(
                    {
                        "key": secret.name,
                        "path": secret.name,
                    }
                )
        return {
            "name": self.k8s_secret_name,
            "secret": {
                "secretName": self.k8s_secret_name,
                "items": file_secrets,
            },
        }


class UserSecretsStore:
    """Utility class to fetch and update user secrets stored in Kubernetes."""

    @staticmethod
    def init(user_id: Union[str, UUID]) -> UserSecrets:
        """Initialise the secret store of a given user through the k8s API."""
        user_id = str(user_id)
        user_secret_store_id = build_unique_component_name("secretsstore", user_id)
        empty_secrets = UserSecrets(user_id, user_secret_store_id)
        try:
            current_k8s_corev1_api_client.create_namespaced_secret(
                REANA_RUNTIME_KUBERNETES_NAMESPACE, empty_secrets.to_k8s_secret()
            )
            return empty_secrets
        except ApiException:
            log.error(
                "Something went wrong while creating "
                "Kubernetes secret for user {0}.".format(user_secret_store_id),
                exc_info=True,
            )
            raise

    @staticmethod
    def fetch(user_id: Union[str, UUID]) -> UserSecrets:
        """Fetch the secret store of a given user through the k8s API.

        If the secret store does not exist, it will be created.
        """
        user_id = str(user_id)
        user_secret_store_id = build_unique_component_name("secretsstore", user_id)
        try:
            k8s_user_secrets_store = (
                current_k8s_corev1_api_client.read_namespaced_secret(
                    user_secret_store_id, REANA_RUNTIME_KUBERNETES_NAMESPACE
                )
            )
            k8s_user_secrets_store.data = k8s_user_secrets_store.data or {}
            return UserSecrets.from_k8s_secret(user_id, k8s_user_secrets_store)
        except ApiException as api_e:
            if api_e.status == 404:
                log.info(
                    "Kubernetes secret for user {0} does not "
                    "exist, creating...".format(user_secret_store_id)
                )
                return UserSecretsStore.init(user_id)
            else:
                log.error(
                    "Something went wrong while retrieving "
                    "Kubernetes secret for user {0}.".format(user_secret_store_id),
                    exc_info=True,
                )
                raise

    @staticmethod
    def update(secrets: UserSecrets):
        """Update the secret store of a given user through the k8s API."""
        current_k8s_corev1_api_client.replace_namespaced_secret(
            secrets.k8s_secret_name,
            REANA_RUNTIME_KUBERNETES_NAMESPACE,
            secrets.to_k8s_secret(),
        )
