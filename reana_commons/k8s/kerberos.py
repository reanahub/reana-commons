# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Kubernetes-Kerberos configuration."""

from collections import namedtuple
import os

from reana_commons.config import (
    KRB5_CONFIGMAP_NAME,
    KRB5_CONTAINER_IMAGE,
    KRB5_INIT_CONTAINER_NAME,
    KRB5_RENEW_CONTAINER_NAME,
    KRB5_STATUS_FILE_LOCATION,
    KRB5_STATUS_FILE_CHECK_INTERVAL,
    KRB5_TICKET_RENEW_INTERVAL,
    KRB5_TOKEN_CACHE_FILENAME,
    KRB5_TOKEN_CACHE_LOCATION,
)
from reana_commons.errors import REANASecretDoesNotExist
from reana_commons.k8s.secrets import REANAUserSecretsStore


KerberosConfig = namedtuple(
    "KerberosConfig",
    ["volumes", "volume_mounts", "env", "init_container", "renew_container"],
)


def get_kerberos_k8s_config(
    secrets_store: REANAUserSecretsStore, kubernetes_uid: int
) -> KerberosConfig:
    """Get the k8s specification for the Kerberos init and renew containers.

    These containers are used to generate and renew the Kerberos tickets.

    :param secrets_stores: User's secrets store
    :param kubernetes_uid: UID of the user who needs Kerberos
    :returns: - specification of the sidecar container
        - volumes needed by the sidecar container
        - volume mounts needed by the external container that uses Kerberos
        - environment variables needed by the external container that uses Kerberos
        - specification for init container used to generate Kerberos ticket
        - specification for renew container used to periodically renew Kerberos ticket
    """
    secrets_volume_mount = secrets_store.get_secrets_volume_mount_as_k8s_spec()
    keytab_file = secrets_store.get_secret_value("CERN_KEYTAB")
    cern_user = secrets_store.get_secret_value("CERN_USER")

    if not keytab_file:
        raise REANASecretDoesNotExist(missing_secrets_list=["CERN_KEYTAB"])
    if not cern_user:
        raise REANASecretDoesNotExist(missing_secrets_list=["CERN_USER"])

    ticket_cache_volume = {
        "name": "krb5-cache",
        "emptyDir": {},
    }
    krb5_config_volume = {
        "name": "krb5-conf",
        "configMap": {"name": KRB5_CONFIGMAP_NAME},
    }
    volumes = [ticket_cache_volume, krb5_config_volume]

    volume_mounts = [
        {
            "name": ticket_cache_volume["name"],
            "mountPath": KRB5_TOKEN_CACHE_LOCATION,
        },
        {
            "name": krb5_config_volume["name"],
            "mountPath": "/etc/krb5.conf",
            "subPath": "krb5.conf",
        },
    ]

    env = [
        {
            "name": "KRB5CCNAME",
            "value": os.path.join(
                KRB5_TOKEN_CACHE_LOCATION,
                KRB5_TOKEN_CACHE_FILENAME.format(kubernetes_uid),
            ),
        }
    ]

    # Kerberos init container generates ticket to access external services
    krb5_init_container = {
        "image": KRB5_CONTAINER_IMAGE,
        "command": [
            "kinit",
            "-kt",
            f"/etc/reana/secrets/{keytab_file}",
            f"{cern_user}@CERN.CH",
        ],
        "name": KRB5_INIT_CONTAINER_NAME,
        "imagePullPolicy": "IfNotPresent",
        "volumeMounts": [secrets_volume_mount] + volume_mounts,
        "env": env,
        "securityContext": {"runAsUser": kubernetes_uid},
    }

    # Kerberos renew container renews ticket periodically for long-running jobs
    krb5_renew_container = {
        "image": KRB5_CONTAINER_IMAGE,
        "command": ["bash", "-c"],
        "args": [
            (
                "SECONDS=0; "
                f"while ! test -f {KRB5_STATUS_FILE_LOCATION}; do "
                f"if [ $SECONDS -ge {KRB5_TICKET_RENEW_INTERVAL} ]; then "
                'echo "Renewing Kerberos ticket: $(date)"; kinit -R; SECONDS=0; fi; '
                f"sleep {KRB5_STATUS_FILE_CHECK_INTERVAL}; done"
            )
        ],
        "name": KRB5_RENEW_CONTAINER_NAME,
        "imagePullPolicy": "IfNotPresent",
        "volumeMounts": [secrets_volume_mount] + volume_mounts,
        "env": env,
        "securityContext": {"runAsUser": kubernetes_uid},
    }

    return KerberosConfig(
        volumes, volume_mounts, env, krb5_init_container, krb5_renew_container
    )
