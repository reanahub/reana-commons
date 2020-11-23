# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Kubernetes secrets."""
import base64
import json
import logging

from kubernetes import client
from kubernetes.client.rest import ApiException
from reana_commons.config import (
    REANA_COMPONENT_PREFIX,
    REANA_RUNTIME_KUBERNETES_NAMESPACE,
    REANA_USER_SECRET_MOUNT_PATH,
)
from reana_commons.errors import REANASecretAlreadyExists, REANASecretDoesNotExist
from reana_commons.k8s.api_client import current_k8s_corev1_api_client
from reana_commons.utils import build_unique_component_name

log = logging.getLogger(__name__)


class REANAUserSecretsStore(object):
    """REANA user secrets store."""

    def __init__(self, user_secret_store_id):
        """Initialise the secret store object."""
        self.user_secret_store_id = build_unique_component_name(
            "secretsstore", str(user_secret_store_id)
        )

    def _initialise_user_secrets_store(self):
        """Initialise an empty Kubernetes secret for a given user."""
        try:
            empty_k8s_secret = client.V1Secret(
                api_version="v1",
                metadata=client.V1ObjectMeta(
                    name=str(self.user_secret_store_id),
                    namespace=REANA_RUNTIME_KUBERNETES_NAMESPACE,
                ),
                data={},
            )
            empty_k8s_secret.metadata.annotations = {"secrets_types": "{}"}
            current_k8s_corev1_api_client.create_namespaced_secret(
                REANA_RUNTIME_KUBERNETES_NAMESPACE, empty_k8s_secret
            )
            return empty_k8s_secret
        except ApiException:
            log.error(
                "Something went wrong while creating "
                "Kubernetes secret for user {0}.".format(
                    str(self.user_secret_store_id)
                ),
                exc_info=True,
            )

    def _update_store(self, k8s_user_secrets):
        """Update Kubernetes secret store.

        :param k8s_user_secrets: A Kubernetes secrets object containing a new
                                 version of the store.
        """
        current_k8s_corev1_api_client.replace_namespaced_secret(
            str(self.user_secret_store_id),
            REANA_RUNTIME_KUBERNETES_NAMESPACE,
            k8s_user_secrets,
        )

    def _get_k8s_user_secrets_store(self):
        """Retrieve the Kubernetes secret which contains all user secrets."""
        try:
            k8s_user_secrets_store = current_k8s_corev1_api_client.read_namespaced_secret(
                str(self.user_secret_store_id), REANA_RUNTIME_KUBERNETES_NAMESPACE
            )
            k8s_user_secrets_store.data = k8s_user_secrets_store.data or {}
            return k8s_user_secrets_store
        except ApiException as api_e:
            if api_e.status == 404:
                log.info(
                    "Kubernetes secret for user {0} does not "
                    "exist, creating...".format(str(self.user_secret_store_id))
                )
                return self._initialise_user_secrets_store()
            else:
                log.error(
                    "Something went wrong while retrieving "
                    "Kubernetes secret for user {0}.".format(
                        str(self.user_secret_store_id)
                    ),
                    exc_info=True,
                )

    def _dump_json_annotation_to_k8s_object(
        self, k8s_object, annotation_key, annotation_value
    ):
        """Dump Python object as annotation to Kubernetes object."""
        try:
            k8s_object.metadata.annotations[annotation_key] = json.dumps(
                annotation_value
            )
        except TypeError as e:
            log.error(
                "Could not add annotations to user secrets:\n" "{}".format(str(e)),
                exc_info=True,
            )

    def _load_json_annotation_from_k8s_object(self, k8s_object, annotation_key):
        """Load string annotations from Kubernetes object."""
        try:
            return json.loads(k8s_object.metadata.annotations[annotation_key])
        except ValueError:
            log.error(
                "Annotations for user {} secret store could not be"
                "loaded as json.".format(annotation_key)
            )
        except KeyError:
            log.error(
                "Annotation key {annotation_key} does not exist for"
                " user {user} secret store, so it can not be loaded".format(
                    annotation_key=annotation_key, user=k8s_object.metadata.name
                )
            )

    def add_secrets(self, secrets_dict, overwrite=False):
        """Add a new secret to the user's Kubernetes secret.

        :param secrets: Dictionary containing new secrets, where keys are
            secret names and corresponding values are dictionaries containing
            base64 encoded value and a type (which determines how the secret
            should be mounted).
        :returns: Updated user secret list.
        """
        try:
            k8s_user_secrets = self._get_k8s_user_secrets_store()
            for secret_name in secrets_dict:
                if k8s_user_secrets.data.get(secret_name) and not overwrite:
                    raise REANASecretAlreadyExists(
                        "Operation cancelled. Secret {} already exists. "
                        "If you want change it use overwrite".format(secret_name)
                    )
                secrets_types = self._load_json_annotation_from_k8s_object(
                    k8s_user_secrets, "secrets_types"
                )
                secrets_types[secret_name] = secrets_dict[secret_name]["type"]
                self._dump_json_annotation_to_k8s_object(
                    k8s_user_secrets, "secrets_types", secrets_types
                )
                k8s_user_secrets.data[secret_name] = secrets_dict[secret_name]["value"]
            self._update_store(k8s_user_secrets)
            return k8s_user_secrets.data.keys()
        except ApiException:
            log.error(
                "Something went wrong while adding secrets to "
                "Kubernetes secret for user {0}.".format(
                    str(self.user_secret_store_id)
                ),
                exc_info=True,
            )

    def get_secrets(self):
        """List all secrets for a given user."""
        secrets_store = self._get_k8s_user_secrets_store()
        secrets_with_types = []
        for secret_name in secrets_store.data:
            secrets_types = self._load_json_annotation_from_k8s_object(
                secrets_store, "secrets_types"
            )
            secrets_with_types.append(
                {"name": secret_name, "type": secrets_types[secret_name]}
            )

        return secrets_with_types

    def get_env_secrets_as_k8s_spec(self):
        """Return a list of specification items for env type secrets for k8s.

        Return all environment variable secrets as a list of Kubernetes
         environment variable specs.

        Object reference: https://github.com/kubernetes-client/python/
        blob/master/kubernetes/docs/V1EnvVar.md.
        """
        all_secrets = self.get_secrets()
        env_secrets = []
        for secret in all_secrets:
            name = secret["name"]
            if secret["type"] == "env":
                env_secrets.append(
                    {
                        "name": name,
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": self.user_secret_store_id,
                                "key": name,
                            }
                        },
                    }
                )
        return env_secrets

    def get_file_secrets_as_k8s_specs(self):
        """Return a list of k8s specification items for file-type secrets.

        API Reference: https://kubernetes.io/docs/concepts/configuration/
        secret/#using-secrets-as-files-from-a-pod
        """
        all_secrets = self.get_secrets()
        file_secrets = []
        for secret in all_secrets:
            name = secret["name"]
            if secret["type"] == "file":
                file_secrets.append(
                    {"key": name, "path": name,}
                )
        return file_secrets

    def get_file_secrets_volume_as_k8s_specs(self):
        """Return the k8s specification item for file-type secrets.

        Return the specification for Kubernetes secret store API,
        specifying the secrets that should be mounted as files.

        Object reference: https://github.com/kubernetes-client/python/
        blob/master/kubernetes/docs/V1SecretVolumeSource.md
        """
        user_id = self.user_secret_store_id
        return {
            "name": user_id,
            "secret": {
                "secretName": user_id,
                "items": self.get_file_secrets_as_k8s_specs(),
            },
        }

    def get_secrets_volume_mount_as_k8s_spec(self):
        """Return a secret volume mount object for secret store id."""
        return {
            "name": self.user_secret_store_id,
            "mountPath": REANA_USER_SECRET_MOUNT_PATH,
            "readOnly": True,
        }

    def delete_secrets(self, secrets):
        """Delete one or more of users secrets.

        :param secrets: List of secret names to be deleted form the store.
        :returns: List with the names of the deleted secrets.
        """
        try:
            k8s_user_secrets = self._get_k8s_user_secrets_store()
            deleted = []
            missing_secrets_list = []
            for secret_name in secrets:
                try:
                    secrets_types = self._load_json_annotation_from_k8s_object(
                        k8s_user_secrets, "secrets_types"
                    )
                    del secrets_types[secret_name]
                    self._dump_json_annotation_to_k8s_object(
                        k8s_user_secrets, "secrets_types", secrets_types
                    )
                    del k8s_user_secrets.data[secret_name]
                    deleted.append(secret_name)
                except KeyError:
                    missing_secrets_list.append(secret_name)
            if missing_secrets_list:
                raise REANASecretDoesNotExist(missing_secrets_list=missing_secrets_list)
            self._update_store(k8s_user_secrets)
            return deleted
        except ApiException:
            log.error(
                "Something went wrong while deleting secrets from "
                "Kubernetes secret for user {0}.".format(
                    str(self.user_secret_store_id)
                ),
                exc_info=True,
            )

    def get_secret_value(self, name):
        """Return secret value if secret with specified name is present."""
        secrets = self.get_secrets()
        secret_names = [secret["name"] for secret in secrets]
        if name in secret_names:
            secrets_store = self._get_k8s_user_secrets_store()
            secret_value = base64.standard_b64decode(secrets_store.data[name]).decode()
            return secret_value
        return None
