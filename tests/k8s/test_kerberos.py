# This file is part of REANA.
# Copyright (C) 2024, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

from uuid import uuid4
from reana_commons.k8s.secrets import Secret, UserSecrets
from reana_commons.k8s.kerberos import KerberosConfig, get_kerberos_k8s_config
from reana_commons.config import WORKFLOW_RUNTIME_USER_GID


def test_get_kerberos_k8s_config(kerberos_user_secrets):
    """Test get_kerberos_k8s_config."""
    secrets = [
        Secret.from_base64(name, type_=s["type"], value=s["value"])
        for name, s in kerberos_user_secrets.items()
    ]
    user_secrets = UserSecrets(str(uuid4()), "k8s_kerberos_secret", secrets)
    conf: KerberosConfig = get_kerberos_k8s_config(user_secrets, 123)

    assert conf.init_container["command"] == [
        "kinit",
        "-kt",
        "/etc/reana/secrets/.keytab",
        "johndoe@CERN.CH",
    ]
    assert conf.init_container["securityContext"]["runAsUser"] == 123
    assert conf.init_container["securityContext"]["runAsGroup"] == int(
        WORKFLOW_RUNTIME_USER_GID
    )
    assert conf.init_container["securityContext"]["runAsNonRoot"] is True
    assert conf.init_container["securityContext"]["allowPrivilegeEscalation"] is False
    assert conf.init_container["securityContext"]["capabilities"] == {"drop": ["ALL"]}
    assert conf.init_container["securityContext"]["seccompProfile"] == {
        "type": "RuntimeDefault"
    }
    assert conf.renew_container["securityContext"]["runAsUser"] == 123
    assert conf.renew_container["securityContext"]["runAsGroup"] == int(
        WORKFLOW_RUNTIME_USER_GID
    )
    assert conf.renew_container["securityContext"]["runAsNonRoot"] is True
    assert conf.renew_container["securityContext"]["allowPrivilegeEscalation"] is False
    assert conf.renew_container["securityContext"]["capabilities"] == {"drop": ["ALL"]}
    assert conf.renew_container["securityContext"]["seccompProfile"] == {
        "type": "RuntimeDefault"
    }


def test_get_kerberos_k8s_config_without_security_context(kerberos_user_secrets):
    """Test get_kerberos_k8s_config when security contexts are disabled."""
    secrets = [
        Secret.from_base64(name, type_=s["type"], value=s["value"])
        for name, s in kerberos_user_secrets.items()
    ]
    user_secrets = UserSecrets(str(uuid4()), "k8s_kerberos_secret", secrets)
    conf: KerberosConfig = get_kerberos_k8s_config(
        user_secrets, 123, use_security_context=False
    )

    assert "securityContext" not in conf.init_container
    assert "securityContext" not in conf.renew_container
