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

from reana_commons.errors import (
    REANASecretAlreadyExists,
    REANASecretDoesNotExist,
    REANAValidationError,
)
from reana_commons.k8s.secrets import (
    get_declared_workflow_features,
    get_explicit_workflow_secret_names,
    Secret,
    UserSecrets,
    UserSecretsStore,
    get_declared_workflow_secret_names,
    get_workflow_secret_names,
    resolve_secret_names,
)


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


def test_user_secrets_filter():
    """Test filtering user secrets by explicit name allowlist."""
    secrets = [
        Secret("env_secret", "env", "hello env!"),
        Secret("file_secret", "file", b"hello!"),
    ]
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=secrets,
    )

    filtered = user_secrets.filter_secrets(["file_secret"])

    assert filtered.user_id == user_secrets.user_id
    assert filtered.k8s_secret_name == user_secrets.k8s_secret_name
    assert list(filtered.secrets) == ["file_secret"]
    assert filtered.get_secret("file_secret") == secrets[1]


def test_user_secrets_filter_empty():
    """Test filtering user secrets with an explicit empty allowlist."""
    secrets = [Secret("env_secret", "env", "hello env!")]
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=secrets,
    )

    filtered = user_secrets.filter_secrets([])

    assert filtered.get_secrets() == []


def test_user_secrets_filter_unknown_secret():
    """Test filtering user secrets with an unknown secret name."""
    secrets = [Secret("env_secret", "env", "hello env!")]
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=secrets,
    )

    with pytest.raises(REANASecretDoesNotExist):
        user_secrets.filter_secrets(["missing"])


def test_user_secrets_validate_secret_names():
    """Secret-name validation should be explicit and return no filtered value."""
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[Secret("env_secret", "env", "hello env!")],
    )

    assert user_secrets.validate_secret_names(["env_secret"]) is None
    with pytest.raises(REANASecretDoesNotExist):
        user_secrets.validate_secret_names(["missing"])


def test_user_secrets_has_file_secrets():
    """Only file-type secrets should require a Kubernetes secret volume."""
    env_only = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[Secret("env_secret", "env", "hello env!")],
    )
    with_file = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[Secret("file_secret", "file", "hello file!")],
    )

    assert not env_only.has_file_secrets()
    assert with_file.has_file_secrets()


def test_get_workflow_secret_names():
    """Test extraction of workflow-global secret allowlists."""
    assert get_workflow_secret_names() is None
    assert get_workflow_secret_names({}) is None
    assert get_workflow_secret_names({"secret_names": []}) == []
    assert get_workflow_secret_names({"secret_names": ["alpha"]}) == ["alpha"]


def test_resolve_secret_names():
    """Test scope-local secret resolution against workflow defaults."""
    workflow_resources = {"secret_names": ["global"]}

    assert resolve_secret_names(None, None) is None
    assert resolve_secret_names(None, workflow_resources) == ["global"]
    assert resolve_secret_names([], workflow_resources) == []
    assert resolve_secret_names(["local"], workflow_resources) == ["local"]

    with pytest.raises(REANAValidationError, match="secret_names"):
        resolve_secret_names(["local", 1], workflow_resources)


def test_get_declared_workflow_secret_names():
    """Workflow sidecars should carry the workflow-global and step-local union."""
    workflow_resources = {"secret_names": ["common", "global"]}
    workflow_specification = {
        "steps": [
            {"name": "prepare", "commands": ["true"]},
            {
                "name": "fit",
                "commands": ["true"],
                "secret_names": ["common", "global", "fit"],
            },
        ]
    }

    assert get_declared_workflow_secret_names(
        workflow_specification, workflow_resources
    ) == ["common", "global", "fit"]


def test_get_declared_workflow_secret_names_drops_unused_workflow_default():
    """Workflow defaults should not widen the sidecar when every scope overrides."""
    workflow_resources = {"secret_names": ["global"]}
    workflow_specification = {
        "steps": [
            {"name": "prepare", "commands": ["true"], "secret_names": []},
            {"name": "fit", "commands": ["true"], "secret_names": ["fit"]},
        ]
    }

    assert get_declared_workflow_secret_names(
        workflow_specification, workflow_resources
    ) == ["fit"]


def test_get_declared_workflow_secret_names_keeps_unscoped_default():
    """Step-local-only workflows can scope the sidecar when every step is explicit."""
    workflow_specification = {
        "steps": [{"name": "fit", "commands": ["true"], "secret_names": ["fit"]}]
    }

    assert get_declared_workflow_secret_names(workflow_specification, {}) == ["fit"]


def test_get_declared_workflow_secret_names_keeps_cwl_step_local_scope():
    """Packed CWL step-level secret_names should scope the sidecar without a global default."""
    workflow_specification = {
        "$graph": [
            {
                "class": "Workflow",
                "id": "#main",
                "steps": [
                    {
                        "id": "#main/fit",
                        "run": "#tool",
                        "in": [],
                        "out": [],
                        "hints": [{"class": "reana", "secret_names": ["fit"]}],
                    }
                ],
            },
            {"class": "CommandLineTool", "id": "#tool"},
        ]
    }

    assert get_declared_workflow_secret_names(workflow_specification, {}) == ["fit"]


def test_get_declared_workflow_secret_names_preserves_explicit_empty_scope():
    """Explicitly empty step-local scopes must remain distinct from omitted scopes."""
    workflow_specification = {
        "steps": [
            {"name": "prepare", "commands": ["true"], "secret_names": []},
            {"name": "fit", "commands": ["true"], "secret_names": []},
        ]
    }

    assert get_declared_workflow_secret_names(workflow_specification, {}) == []


def test_get_declared_workflow_secret_names_keeps_mixed_local_default_unscoped():
    """Mixed explicit and implicit step scopes must preserve expose-all semantics."""
    workflow_specification = {
        "steps": [
            {"name": "prepare", "commands": ["true"]},
            {"name": "fit", "commands": ["true"], "secret_names": ["fit"]},
        ]
    }

    assert get_declared_workflow_secret_names(workflow_specification, {}) is None


def test_get_explicit_workflow_secret_names_keeps_mixed_scope_declarations():
    """Explicit step-local secret names remain available for early validation."""
    workflow_specification = {
        "steps": [
            {"name": "prepare", "commands": ["true"]},
            {"name": "fit", "commands": ["true"], "secret_names": ["fit"]},
        ]
    }

    assert get_explicit_workflow_secret_names(workflow_specification) == ["fit"]


def test_get_declared_workflow_features():
    """Only enabled feature hints should widen the sidecar carve-out."""
    workflow_resources = {"kerberos": True}
    workflow_specification = {
        "steps": [
            {"name": "prepare", "commands": ["true"]},
            {"name": "fit", "commands": ["true"], "voms_proxy": True},
        ]
    }

    assert get_declared_workflow_features(
        workflow_specification, workflow_resources
    ) == {
        "kerberos": True,
        "voms_proxy": True,
        "rucio": False,
    }


def test_get_declared_workflow_features_ignores_scalar_yadage_resources():
    """Legacy scalar Yadage resources must not break feature discovery."""
    workflow_specification = {
        "stages": [
            {
                "scheduler": {
                    "parameters": {
                        "step": {
                            "process": {"process_type": "string-interpolated-cmd"},
                            "environment": {"resources": ["GRIDProxy"]},
                        }
                    }
                }
            }
        ]
    }

    assert get_declared_workflow_features(workflow_specification) == {
        "kerberos": False,
        "voms_proxy": False,
        "rucio": False,
    }


@pytest.mark.parametrize("secret_names", [{"alpha": True}, ["alpha", 1]])
def test_declared_workflow_secret_names_rejects_malformed_values(secret_names):
    """Unvalidated engine-local declarations must fail instead of being coerced."""
    workflow_specification = {
        "steps": [{"name": "fit", "commands": ["true"], "secret_names": secret_names}]
    }

    with pytest.raises(REANAValidationError, match="secret_names"):
        get_declared_workflow_secret_names(workflow_specification)


def test_get_declared_workflow_features_marks_cern_backends_as_kerberos_required():
    """CERN batch backends should imply Kerberos sidecar credentials."""
    workflow_specification = {
        "steps": [
            {
                "name": "fit",
                "commands": ["true"],
                "compute_backend": "htcondorcern",
            }
        ]
    }

    assert get_declared_workflow_features(workflow_specification, {}) == {
        "kerberos": True,
        "voms_proxy": False,
        "rucio": False,
    }


def test_get_declared_workflow_features_reads_cwl_step_reana_hints():
    """Packed CWL step-level REANA hints should drive sidecar feature detection."""
    workflow_specification = {
        "$graph": [
            {
                "class": "Workflow",
                "id": "#main",
                "steps": [
                    {
                        "id": "#main/fit",
                        "run": "#tool",
                        "in": [],
                        "out": [],
                        "hints": [{"class": "reana", "voms_proxy": True}],
                    }
                ],
            },
            {"class": "CommandLineTool", "id": "#tool"},
        ]
    }

    assert get_declared_workflow_features(workflow_specification, {}) == {
        "kerberos": False,
        "voms_proxy": True,
        "rucio": False,
    }


def test_user_secrets_get_scoped_secrets_for_kerberos():
    """Kerberos-required secrets must stay available when scoping ordinary ones."""
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[
            Secret("ordinary", "env", "hello"),
            Secret("CERN_USER", "env", "johndoe"),
            Secret("CERN_KEYTAB", "env", ".keytab"),
            Secret(".keytab", "file", b"secret"),
        ],
    )

    scoped = user_secrets.get_scoped_secrets([], kerberos=True)

    assert list(scoped.secrets) == ["CERN_USER", "CERN_KEYTAB", ".keytab"]


def test_user_secrets_get_scoped_secrets_for_voms_proxy_file_mode():
    """VOMS file mode must keep both the selector env secret and the file secret."""
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[
            Secret("ordinary", "env", "hello"),
            Secret("VOMSPROXY_FILE", "env", "proxy.pem"),
            Secret("proxy.pem", "file", b"proxy"),
        ],
    )

    scoped = user_secrets.get_scoped_secrets([], voms_proxy=True)

    assert list(scoped.secrets) == ["VOMSPROXY_FILE", "proxy.pem"]


def test_user_secrets_get_scoped_secrets_for_voms_proxy_generated_mode():
    """VOMS generated mode must keep the secrets needed to mint the proxy."""
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[
            Secret("ordinary", "env", "hello"),
            Secret("VONAME", "env", "atlas"),
            Secret("VOMSPROXY_PASS", "env", "password"),
            Secret("userkey.pem", "file", b"key"),
            Secret("usercert.pem", "file", b"cert"),
        ],
    )

    scoped = user_secrets.get_scoped_secrets([], voms_proxy=True)

    assert list(scoped.secrets) == [
        "VONAME",
        "VOMSPROXY_PASS",
        "userkey.pem",
        "usercert.pem",
    ]


def test_user_secrets_get_scoped_secrets_for_rucio():
    """Rucio-required secrets must stay available, including optional overrides."""
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[
            Secret("ordinary", "env", "hello"),
            Secret("VONAME", "env", "atlas"),
            Secret("RUCIO_USERNAME", "env", "johndoe"),
            Secret("RUCIO_RUCIO_HOST", "env", "https://rucio.example"),
        ],
    )

    scoped = user_secrets.get_scoped_secrets([], rucio=True)

    assert list(scoped.secrets) == ["VONAME", "RUCIO_USERNAME", "RUCIO_RUCIO_HOST"]


def test_user_secrets_get_existing_feature_secret_names():
    """Existing feature-managed secrets should be discoverable without hints."""
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[
            Secret("ordinary", "env", "hello"),
            Secret("CERN_USER", "env", "johndoe"),
            Secret("CERN_KEYTAB", "env", ".keytab"),
            Secret(".keytab", "file", b"secret"),
            Secret("VOMSPROXY_FILE", "env", "proxy.pem"),
            Secret("proxy.pem", "file", b"proxy"),
            Secret("VONAME", "env", "atlas"),
            Secret("RUCIO_USERNAME", "env", "johndoe"),
        ],
    )

    assert user_secrets.get_existing_feature_secret_names() == [
        "CERN_USER",
        "CERN_KEYTAB",
        ".keytab",
        "VOMSPROXY_FILE",
        "proxy.pem",
        "VONAME",
        "RUCIO_USERNAME",
    ]


def test_user_secrets_get_existing_required_feature_secret_names():
    """Only feature secrets required by enabled hints should be returned."""
    user_secrets = UserSecrets(
        user_id="123",
        k8s_secret_name="k8s_secret",
        secrets=[
            Secret("CERN_USER", "env", "johndoe"),
            Secret("CERN_KEYTAB", "env", ".keytab"),
            Secret(".keytab", "file", b"secret"),
            Secret("VOMSPROXY_FILE", "env", "proxy.pem"),
            Secret("proxy.pem", "file", b"proxy"),
        ],
    )

    assert user_secrets.get_existing_required_feature_secret_names(voms_proxy=True) == [
        "VOMSPROXY_FILE",
        "proxy.pem",
    ]


def test_user_secrets_from_pod_secrets(tmp_path):
    """Scoped secrets should be reconstructible from pod env and files."""
    secret_path = tmp_path / ".keytab"
    secret_path.write_bytes(b"keytab")

    user_secrets = UserSecrets.from_pod_secrets(
        user_id="123",
        secrets_types={"username": "env", ".keytab": "file"},
        mount_path=str(tmp_path),
        env={"username": "johndoe"},
    )

    assert user_secrets.get_secret("username").value_str == "johndoe"
    assert user_secrets.get_secret(".keytab").value_bytes == b"keytab"


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
