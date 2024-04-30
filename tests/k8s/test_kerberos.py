# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

from uuid import uuid4
from reana_commons.k8s.secrets import Secret, UserSecrets
from reana_commons.k8s.kerberos import KerberosConfig, get_kerberos_k8s_config


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
    assert conf.renew_container["securityContext"]["runAsUser"] == 123
