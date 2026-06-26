# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019, 2020, 2021, 2022, 2024, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Kubernetes secrets."""

import base64
import binascii
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID

from kubernetes import client
from kubernetes.client.rest import ApiException
from reana_commons.config import (
    REANA_RUNTIME_KUBERNETES_NAMESPACE,
    REANA_USER_SECRET_MOUNT_PATH,
)
from reana_commons.errors import (
    REANASecretAlreadyExists,
    REANASecretDoesNotExist,
    REANAValidationError,
)
from reana_commons.k8s.api_client import current_k8s_corev1_api_client
from reana_commons.utils import build_unique_component_name

log = logging.getLogger(__name__)
_CERN_BACKENDS_REQUIRING_KERBEROS = {"htcondorcern", "slurmcern"}
_MISSING = object()


def get_workflow_secret_names(
    workflow_resources: Optional[Dict[str, Any]] = None,
) -> Optional[List[str]]:
    """Return the workflow-global secret allowlist if configured."""
    workflow_resources = workflow_resources or {}
    if "secret_names" in workflow_resources:
        return _normalize_secret_names(workflow_resources["secret_names"])
    return None


def resolve_secret_names(
    scoped_secret_names: Optional[List[str]],
    workflow_resources: Optional[Dict[str, Any]] = None,
) -> Optional[List[str]]:
    """Resolve a scope-local allowlist against the workflow-global default."""
    if scoped_secret_names is not None:
        return _normalize_secret_names(scoped_secret_names)
    return get_workflow_secret_names(workflow_resources)


def _normalize_secret_names(secret_names: Any) -> Optional[List[str]]:
    """Normalize a ``secret_names`` declaration to a string list."""
    if secret_names is None:
        return None

    if isinstance(secret_names, str):
        return [secret_names]

    if isinstance(secret_names, Sequence) and not isinstance(
        secret_names, (bytes, str)
    ):
        if all(isinstance(secret_name, str) for secret_name in secret_names):
            return list(secret_names)

    raise REANAValidationError(
        "secret_names must be a string or a list containing only strings."
    )


def _get_scope_secret_names(scope: Dict[str, Any]) -> Optional[List[str]]:
    """Return explicitly declared ``secret_names`` for a supported scope."""
    if isinstance(scope.get("commands"), list):
        return _normalize_secret_names(scope.get("secret_names"))

    if scope.get("class") == "CommandLineTool" or _is_cwl_workflow_step_scope(scope):
        secret_names = []
        found = False

        scope_secret_names = _normalize_secret_names(scope.get("secret_names"))
        if scope_secret_names is not None:
            found = True
            secret_names.extend(scope_secret_names)

        for item in _iter_cwl_hints(scope):
            if item.get("class") in (None, "reana"):
                hint_secret_names = _normalize_secret_names(item.get("secret_names"))
                if hint_secret_names is not None:
                    found = True
                    secret_names.extend(hint_secret_names)

        if found:
            return list(dict.fromkeys(secret_names))
        return None

    if isinstance(scope.get("process"), dict) and isinstance(
        scope.get("environment"), dict
    ):
        secret_names = []
        found = False
        for resource in scope.get("environment", {}).get("resources", []) or []:
            if isinstance(resource, dict):
                resource_secret_names = _normalize_secret_names(
                    resource.get("secret_names")
                )
                if resource_secret_names is not None:
                    found = True
                    secret_names.extend(resource_secret_names)
        if found:
            return list(dict.fromkeys(secret_names))
        return None

    return None


def _get_cwl_declared_field(scope: Dict[str, Any], field_name: str):
    """Return a CWL field declared directly or via a REANA hint."""
    if field_name in scope:
        return scope[field_name]

    for item in _iter_cwl_hints(scope):
        if item.get("class") in (None, "reana") and field_name in item:
            return item[field_name]

    return _MISSING


def _build_effective_cwl_step_scope(
    step: Dict[str, Any], tool: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build an effective CWL step scope with step-local override precedence."""
    effective_scope = dict(step)

    for field_name in (
        "secret_names",
        "compute_backend",
        "kerberos",
        "voms_proxy",
        "rucio",
    ):
        value = _get_cwl_declared_field(step, field_name)
        if value is _MISSING and isinstance(tool, dict):
            value = _get_cwl_declared_field(tool, field_name)
        if value is _MISSING:
            effective_scope.pop(field_name, None)
        else:
            effective_scope[field_name] = value

    # The effective scope already carries the resolved REANA fields above.
    effective_scope["hints"] = []
    effective_scope["requirements"] = []
    return effective_scope


def _iter_packed_cwl_step_scopes(workflow_specification: Dict[str, Any]):
    """Yield effective CWL workflow step scopes from packed ``$graph`` specs."""
    graph = workflow_specification.get("$graph")
    if not isinstance(graph, list):
        return

    tool_by_id = {
        node.get("id"): node
        for node in graph
        if isinstance(node, dict) and node.get("class") == "CommandLineTool"
    }

    for node in graph:
        if not isinstance(node, dict) or node.get("class") != "Workflow":
            continue
        for step in node.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            run_definition = step.get("run")
            if isinstance(run_definition, dict):
                tool = run_definition
            else:
                tool = tool_by_id.get(run_definition)
            yield _build_effective_cwl_step_scope(step, tool)


def _iter_cwl_hints(node: Dict[str, Any]):
    """Yield CWL requirement/hint dictionaries in list or mapping form."""
    for key in ("requirements", "hints"):
        block = node.get(key) or []
        if isinstance(block, dict):
            for class_name, body in block.items():
                entry = {"class": class_name}
                if isinstance(body, dict):
                    entry.update(body)
                yield entry
        else:
            for item in block:
                if isinstance(item, dict):
                    yield item


def _is_cwl_workflow_step_scope(scope: Dict[str, Any]) -> bool:
    """Return whether a mapping looks like a packed CWL workflow step."""
    return "run" in scope and ("in" in scope or "out" in scope)


def _iter_executable_scopes(workflow_specification: Any):
    """Yield executable workflow scopes across supported workflow formats."""
    if isinstance(workflow_specification, dict):
        packed_cwl_steps = list(
            _iter_packed_cwl_step_scopes(workflow_specification) or []
        )
        if packed_cwl_steps:
            yield from packed_cwl_steps
            for key, value in workflow_specification.items():
                if key != "$graph":
                    yield from _iter_executable_scopes(value)
            return

        if workflow_specification.get("class") == "Workflow" and isinstance(
            workflow_specification.get("steps"), list
        ):
            for step in workflow_specification.get("steps", []) or []:
                if not isinstance(step, dict):
                    continue
                run_definition = step.get("run")
                tool = run_definition if isinstance(run_definition, dict) else None
                yield _build_effective_cwl_step_scope(step, tool)
            for key, value in workflow_specification.items():
                if key != "steps":
                    yield from _iter_executable_scopes(value)
            return

        if isinstance(workflow_specification.get("commands"), list):
            yield workflow_specification
        elif workflow_specification.get("class") == "CommandLineTool":
            yield workflow_specification
        elif _is_cwl_workflow_step_scope(workflow_specification):
            yield workflow_specification
        elif isinstance(workflow_specification.get("process"), dict) and isinstance(
            workflow_specification.get("environment"), dict
        ):
            yield workflow_specification

        for value in workflow_specification.values():
            yield from _iter_executable_scopes(value)
    elif isinstance(workflow_specification, list):
        for value in workflow_specification:
            yield from _iter_executable_scopes(value)


def _scope_declares_secret_names(scope: Dict[str, Any]) -> bool:
    """Return whether the scope explicitly declares ``secret_names``."""
    return _get_scope_secret_names(scope) is not None


def _scope_uses_feature(scope: Dict[str, Any], feature_name: str) -> bool:
    """Return whether the executable scope enables a feature-managed credential."""
    if isinstance(scope.get("commands"), list):
        if (
            feature_name == "kerberos"
            and scope.get("compute_backend") in _CERN_BACKENDS_REQUIRING_KERBEROS
        ):
            return True
        return bool(scope.get(feature_name, False))

    if scope.get("class") == "CommandLineTool" or _is_cwl_workflow_step_scope(scope):
        if (
            feature_name == "kerberos"
            and scope.get("compute_backend") in _CERN_BACKENDS_REQUIRING_KERBEROS
        ):
            return True
        if feature_name == "kerberos" and any(
            item.get("class") in (None, "reana")
            and item.get("compute_backend") in _CERN_BACKENDS_REQUIRING_KERBEROS
            for item in _iter_cwl_hints(scope)
        ):
            return True
        if scope.get(feature_name):
            return True
        for item in _iter_cwl_hints(scope):
            if item.get("class") in (None, "reana") and item.get(feature_name):
                return True
        return False

    if isinstance(scope.get("process"), dict) and isinstance(
        scope.get("environment"), dict
    ):
        for resource in scope.get("environment", {}).get("resources", []) or []:
            if not isinstance(resource, dict):
                continue
            if (
                feature_name == "kerberos"
                and resource.get("compute_backend") in _CERN_BACKENDS_REQUIRING_KERBEROS
            ):
                return True
            if resource.get(feature_name):
                return True
        return False

    return False


def get_declared_workflow_features(
    workflow_specification: Any = None,
    workflow_resources: Optional[Dict[str, Any]] = None,
) -> Dict[str, bool]:
    """Return which feature-managed credential families are actually enabled."""
    workflow_resources = workflow_resources or {}
    workflow_features = {
        "kerberos": bool(workflow_resources.get("kerberos", False)),
        "voms_proxy": bool(workflow_resources.get("voms_proxy", False)),
        "rucio": bool(workflow_resources.get("rucio", False)),
    }

    for scope in _iter_executable_scopes(workflow_specification or {}):
        for feature_name in workflow_features:
            workflow_features[feature_name] = workflow_features[
                feature_name
            ] or _scope_uses_feature(scope, feature_name)

    return workflow_features


def get_explicit_workflow_secret_names(workflow_specification: Any = None) -> List[str]:
    """Return the explicit ``secret_names`` declared in executable scopes."""
    secret_names = []
    for scope in _iter_executable_scopes(workflow_specification or {}):
        scope_secret_names = _get_scope_secret_names(scope)
        if scope_secret_names is not None:
            secret_names.extend(scope_secret_names)
    return list(dict.fromkeys(secret_names))


def get_declared_workflow_secret_names(
    workflow_specification: Any = None,
    workflow_resources: Optional[Dict[str, Any]] = None,
) -> Optional[List[str]]:
    """Return the sidecar-visible secret union required by the workflow.

    The workflow-global ``secret_names`` allowlist acts as the default only for
    executable scopes that omit their own local declaration. Without a
    workflow-global default, the sidecar can still be scoped if every detected
    executable scope declares its own ``secret_names`` explicitly. Mixed
    workflows keep the legacy expose-all behaviour for the unscoped steps.
    """
    workflow_secret_names = get_workflow_secret_names(workflow_resources)
    declared_secret_names = get_explicit_workflow_secret_names(workflow_specification)
    executable_scopes = list(_iter_executable_scopes(workflow_specification or {}))

    if workflow_secret_names is None:
        if not executable_scopes:
            return None
        if not all(_scope_declares_secret_names(scope) for scope in executable_scopes):
            return None
        return list(dict.fromkeys(declared_secret_names))

    if executable_scopes and all(
        _scope_declares_secret_names(scope) for scope in executable_scopes
    ):
        return list(dict.fromkeys(declared_secret_names))

    secret_names = list(workflow_secret_names)
    secret_names.extend(declared_secret_names)
    return list(dict.fromkeys(secret_names))


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

    def get_secret_types(self) -> Dict[str, str]:
        """Return the secret type mapping."""
        return {secret.name: secret.type_ for secret in self.secrets.values()}

    @classmethod
    def from_pod_secrets(
        cls,
        user_id: Union[str, int],
        secrets_types: Dict[str, str],
        mount_path: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> "UserSecrets":
        """Rebuild scoped secrets from the pod env and mounted files."""
        user_id = str(user_id)
        mount_path = mount_path or REANA_USER_SECRET_MOUNT_PATH
        env = env or os.environ
        secrets = []
        missing_secrets = []

        for secret_name, secret_type in secrets_types.items():
            if secret_type == "env":
                secret_value = env.get(secret_name)
                if secret_value is None:
                    missing_secrets.append(secret_name)
                    continue
                secrets.append(Secret(secret_name, "env", secret_value))
                continue

            if secret_type == "file":
                secret_path = os.path.join(mount_path, secret_name)
                try:
                    with open(secret_path, "rb") as secret_file:
                        secrets.append(Secret(secret_name, "file", secret_file.read()))
                except FileNotFoundError:
                    missing_secrets.append(secret_name)
                continue

            raise ValueError(f"type_ must be one of: {Secret.types}")

        if missing_secrets:
            raise REANASecretDoesNotExist(missing_secrets)

        return cls(
            user_id=user_id,
            k8s_secret_name=build_unique_component_name("secretsstore", user_id),
            secrets=secrets,
        )

    def filter_secrets(
        self, secret_names: Optional[Sequence[str]] = None
    ) -> "UserSecrets":
        """Return a filtered secret collection.

        If ``secret_names`` is ``None``, all secrets are returned.
        """
        if secret_names is None:
            return self

        self.validate_secret_names(secret_names)

        filtered_secrets = [self.secrets[name] for name in secret_names]
        return UserSecrets(
            user_id=self.user_id,
            k8s_secret_name=self.k8s_secret_name,
            secrets=filtered_secrets,
        )

    def validate_secret_names(self, secret_names: Sequence[str]) -> None:
        """Raise when any requested secret name does not exist."""
        missing_secrets = [name for name in secret_names if name not in self.secrets]
        if missing_secrets:
            raise REANASecretDoesNotExist(missing_secrets)

    def has_file_secrets(self) -> bool:
        """Return whether at least one file-type secret is present."""
        return any(secret.type_ == "file" for secret in self.secrets.values())

    def _required_feature_secret_names(
        self,
        kerberos: bool = False,
        voms_proxy: bool = False,
        rucio: bool = False,
    ) -> List[str]:
        """Return feature-managed secret names required for the selected hints."""
        feature_secret_names = []

        if kerberos:
            feature_secret_names.extend(["CERN_USER", "CERN_KEYTAB"])
            keytab_file = self.get_secret("CERN_KEYTAB")
            if keytab_file:
                feature_secret_names.append(keytab_file.value_str)

        if voms_proxy:
            voms_proxy_file = self.get_secret("VOMSPROXY_FILE")
            if voms_proxy_file:
                feature_secret_names.extend(
                    ["VOMSPROXY_FILE", voms_proxy_file.value_str]
                )
            else:
                feature_secret_names.extend(
                    ["VONAME", "VOMSPROXY_PASS", "userkey.pem", "usercert.pem"]
                )

        if rucio:
            feature_secret_names.extend(["VONAME", "RUCIO_USERNAME"])
            if self.get_secret("RUCIO_RUCIO_HOST"):
                feature_secret_names.append("RUCIO_RUCIO_HOST")
            if self.get_secret("RUCIO_AUTH_HOST"):
                feature_secret_names.append("RUCIO_AUTH_HOST")

        return list(dict.fromkeys(feature_secret_names))

    def get_existing_feature_secret_names(self) -> List[str]:
        """Return existing feature-managed secret names without requiring hints."""
        feature_secret_names = []

        cern_user = self.get_secret("CERN_USER")
        keytab_env = self.get_secret("CERN_KEYTAB")
        if cern_user:
            feature_secret_names.append("CERN_USER")
        if keytab_env:
            feature_secret_names.append("CERN_KEYTAB")
            keytab_file = self.get_secret(keytab_env.value_str)
            if keytab_file:
                feature_secret_names.append(keytab_file.name)

        voms_proxy_file = self.get_secret("VOMSPROXY_FILE")
        if voms_proxy_file:
            feature_secret_names.extend(["VOMSPROXY_FILE"])
            voms_proxy_secret_file = self.get_secret(voms_proxy_file.value_str)
            if voms_proxy_secret_file:
                feature_secret_names.append(voms_proxy_secret_file.name)
        else:
            for secret_name in [
                "VONAME",
                "VOMSPROXY_PASS",
                "userkey.pem",
                "usercert.pem",
            ]:
                if self.get_secret(secret_name):
                    feature_secret_names.append(secret_name)

        for secret_name in [
            "VONAME",
            "RUCIO_USERNAME",
            "RUCIO_RUCIO_HOST",
            "RUCIO_AUTH_HOST",
        ]:
            if self.get_secret(secret_name):
                feature_secret_names.append(secret_name)

        return list(dict.fromkeys(feature_secret_names))

    def get_existing_required_feature_secret_names(
        self,
        kerberos: bool = False,
        voms_proxy: bool = False,
        rucio: bool = False,
    ) -> List[str]:
        """Return the existing feature-managed secrets required by enabled hints."""
        required_secret_names = self._required_feature_secret_names(
            kerberos=kerberos,
            voms_proxy=voms_proxy,
            rucio=rucio,
        )
        return [
            secret_name
            for secret_name in dict.fromkeys(required_secret_names)
            if self.get_secret(secret_name)
        ]

    def get_scoped_secrets(
        self,
        secret_names: Optional[Sequence[str]] = None,
        kerberos: bool = False,
        voms_proxy: bool = False,
        rucio: bool = False,
    ) -> "UserSecrets":
        """Return the secrets visible for the requested scope.

        ``secret_names`` controls ordinary user secrets:

        - ``None`` keeps the current behaviour and exposes all user secrets;
        - ``[]`` exposes no ordinary user secrets;
        - a non-empty list exposes only the named ordinary user secrets.

        Feature-managed secrets required by Kerberos, VOMS, or Rucio are still
        added when these hints are enabled.
        """
        if secret_names is None:
            return self

        requested_names = list(secret_names)
        requested_names.extend(
            self._required_feature_secret_names(
                kerberos=kerberos,
                voms_proxy=voms_proxy,
                rucio=rucio,
            )
        )
        deduplicated_names = list(dict.fromkeys(requested_names))
        return self.filter_secrets(deduplicated_names)

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
