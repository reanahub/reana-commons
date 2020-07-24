# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Commons configuration."""

import json
import logging
import os

import yaml

from reana_commons.errors import REANAConfigDoesNotExist


class REANAConfig:
    """REANA global configuration class."""

    path = "/var/reana/config"
    config_mapping = {"ui": "ui-config.yaml"}

    @classmethod
    def _read_file(cls, filename):
        with open(os.path.join(cls.path, filename)) as yaml_file:
            data = yaml.load(yaml_file)
            return data

    @classmethod
    def load(cls, kind):
        """REANA-UI configuration."""
        if kind not in cls.config_mapping:
            raise REANAConfigDoesNotExist(
                "{} configuration does not exist".format(kind)
            )
        return cls._read_file(cls.config_mapping[kind])


REANA_COMPONENT_PREFIX = os.getenv("REANA_COMPONENT_PREFIX", "reana")
"""REANA component naming prefix, i.e. my-prefix-job-controller.

Useful to find the correct fully qualified name of a infrastructure component
and to correctly create new runtime pods.
"""

REANA_COMPONENT_PREFIX_ENVIRONMENT = REANA_COMPONENT_PREFIX.upper().replace("-", "_")
"""Environment variable friendly REANA component prefix."""

REANA_COMPONENT_TYPES = [
    "run-batch",
    "run-session",
    "run-job",
    "secretsstore",
]
"""Type of REANA components.

Note: this list is used for validation of on demand created REANA components
names, this is why it doesn't contain REANA infrastructure components.

``run-batch``: An instance of reana-workflow-engine-_
``run-session``: An instance of an interactive session
``run-job``: An instance of a workflow's job
``secretsstore``: An instance of a user secret store
"""

REANA_INFRASTRUCTURE_COMPONENTS = [
    "ui",
    "server",
    "workflow-controller",
    "cache",
    "message-broker",
    "db",
]
"""REANA infrastructure pods."""

REANA_COMPONENT_NAMING_SCHEME = os.getenv(
    "REANA_COMPONENT_NAMING_SCHEME", "{prefix}-{component_type}-{id}"
)
"""The naming scheme the components created by REANA should follow.

It is a Python format string which take as arguments:
- ``prefix``: the ``REANA_COMPONENT_PREFIX``
- ``component_type``: one of ``REANA_COMPONENT_TYPES``
- ``id``: unique identifier for the component, by default UUID4.
"""

REANA_INFRASTRUCTURE_KUBERNETES_NAMESPACE = os.getenv(
    "REANA_INFRASTRUCTURE_KUBERNETES_NAMESPACE", "default"
)
"""Kubernetes namespace in which REANA infrastructure is currently deployed."""

REANA_INFRASTRUCTURE_COMPONENTS_HOSTNAMES = {
    component_name: (
        "{component_prefix}-{component_name}.{namespace}.svc.cluster.local"
    ).format(
        component_prefix=REANA_COMPONENT_PREFIX,
        component_name=component_name,
        namespace=REANA_INFRASTRUCTURE_KUBERNETES_NAMESPACE,
    )
    for component_name in REANA_INFRASTRUCTURE_COMPONENTS
}
"""REANA infrastructure pods hostnames.

Uses the FQDN of the infrastructure components (which should be behind a Kubernetes
service) following the
`Kubernetes DNS-Based Service Discovery <https://github.com/kubernetes/dns/blob/master/docs/specification.md>`_
"""

REANA_RUNTIME_KUBERNETES_NAMESPACE = os.getenv(
    "REANA_RUNTIME_KUBERNETES_NAMESPACE", REANA_INFRASTRUCTURE_KUBERNETES_NAMESPACE
)
"""Kubernetes namespace in which REANA runtime pods should be running in.

By default runtime pods will run in the same namespace as the infrastructure pods.
"""

REANA_RUNTIME_KUBERNETES_NODE_LABEL = (
    {
        os.getenv("REANA_RUNTIME_KUBERNETES_NODE_LABEL")
        .split("=")[0]: os.getenv("REANA_RUNTIME_KUBERNETES_NODE_LABEL")
        .split("=")[1]
    }
    if os.getenv("REANA_RUNTIME_KUBERNETES_NODE_LABEL")
    else {}
)
"""Kubernetes label (with format ``lable_name=lable_value``) which identifies the nodes where the runtime pods should run.

If not set, the runtime pods run in any available node in the cluster.
"""


MQ_HOST = REANA_INFRASTRUCTURE_COMPONENTS_HOSTNAMES["message-broker"]
"""Message queue (RabbitMQ) server host name."""

MQ_USER = os.getenv("RABBIT_MQ_USER", "test")
"""Message queue (RabbitMQ) user name."""

MQ_PASS = os.getenv("RABBIT_MQ_PASS", "1234")
"""Message queue (RabbitMQ) password."""

MQ_PORT = os.getenv("RABBIT_MQ_PORT", 5672)
"""Message queue (RabbitMQ) service port."""

MQ_CONNECTION_STRING = os.getenv(
    "RABBIT_MQ", "amqp://{0}:{1}@{2}//".format(MQ_USER, MQ_PASS, MQ_HOST)
)
"""Message queue (RabbitMQ) connection string."""

MQ_DEFAULT_FORMAT = "json"
"""Default serializing format (to consume/produce)."""

MQ_DEFAULT_EXCHANGE = ""
"""Message queue (RabbitMQ) exchange."""

MQ_DEFAULT_QUEUES = {
    "jobs-status": {
        "routing_key": "jobs-status",
        "exchange": MQ_DEFAULT_EXCHANGE,
        "durable": False,
    },
    "workflow-submission": {
        "routing_key": "workflow-submission",
        "exchange": MQ_DEFAULT_EXCHANGE,
        "durable": True,
    },
}
"""Default message queues."""

MQ_PRODUCER_MAX_RETRIES = 3
"""Max retries to send a message."""

OPENAPI_SPECS = {
    "reana-workflow-controller": (
        "http://{host}:{port}".format(
            host=REANA_INFRASTRUCTURE_COMPONENTS_HOSTNAMES["workflow-controller"],
            port="80",
        ),
        "reana_workflow_controller.json",
    ),
    "reana-server": (
        os.getenv("REANA_SERVER_URL", "http://0.0.0.0:80"),
        "reana_server.json",
    ),
    "reana-job-controller": (
        "http://{address}:{port}".format(address="0.0.0.0", port="5000"),
        "reana_job_controller.json",
    ),
}
"""REANA Workflow Controller address."""

REANA_MAX_CONCURRENT_BATCH_WORKFLOWS = int(
    os.getenv("REANA_MAX_CONCURRENT_BATCH_WORKFLOWS", "30")
)
"""Upper limit on concurrent REANA batch workflows running in the cluster."""

REANA_READY_CONDITIONS = {
    "reana_commons.tasks": [
        "check_predefined_conditions",
        "check_running_reana_batch_workflows_count",
    ]
}

REANA_LOG_LEVEL = logging.getLevelName(os.getenv("REANA_LOG_LEVEL", "INFO"))
"""Log verbosity level for REANA components."""

REANA_LOG_FORMAT = os.getenv(
    "REANA_LOG_FORMAT",
    "%(asctime)s | %(name)s | %(threadName)s | " "%(levelname)s | %(message)s",
)
"""REANA components log format."""

CVMFS_REPOSITORIES = {
    "alice.cern.ch": "alice",
    "alice-ocdb.cern.ch": "alice-ocdb",
    "ams.cern.ch": "ams",
    "atlas.cern.ch": "atlas",
    "atlas-condb.cern.ch": "atlas-condb",
    "atlas-nightlies.cern.ch": "atlas-nightlies",
    "cms.cern.ch": "cms",
    "cms-ib.cern.ch": "cms-ib",
    "cms-opendata-conddb.cern.ch": "cms-opendata-conddb",
    "compass.cern.ch": "compass",
    "compass-condb.cern.ch": "compass-condb",
    "cvmfs-config.cern.ch": "cvmfs-config",
    "fcc.cern.ch": "fcc",
    "geant4.cern.ch": "geant4",
    "ilc.desy.de": "ilc-desy",
    "lhcb.cern.ch": "lhcb",
    "lhcb-condb.cern.ch": "lhcb-condb",
    "na61.cern.ch": "na61",
    "na62.cern.ch": "na62",
    "projects.cern.ch": "projects",
    "sft.cern.ch": "sft",
    "unpacked.cern.ch": "unpacked",
}
"""CVMFS repositories available for mounting."""

REANA_CVMFS_PVC_TEMPLATE = {
    "metadata": {"name": ""},
    "spec": {
        "accessModes": ["ReadOnlyMany"],
        "storageClassName": "",
        "resources": {"requests": {"storage": "1G"}},
    },
}
"""CVMFS persistent volume claim template."""

REANA_CVMFS_SC_TEMPLATE = {
    "metadata": {"name": ""},
    "provisioner": "cvmfs.csi.cern.ch",
    "parameters": {"repository": ""},
}
"""CVMFS storage claim template."""

INTERACTIVE_SESSION_TYPES = ["jupyter"]
"""List of supported interactive systems."""

REANA_STORAGE_BACKEND = os.getenv("REANA_STORAGE_BACKEND", "local")
"""Storage backend deployed in current REANA cluster ['local'|'cephfs']."""

REANA_SHARED_PVC_NAME = os.getenv(
    "REANA_SHARED_PVC_NAME",
    "{}-shared-persistent-volume".format(REANA_COMPONENT_PREFIX),
)
"""Name of the shared CEPHFS PVC which will be used by all REANA jobs."""

REANA_JOB_HOSTPATH_MOUNTS = json.loads(os.getenv("REANA_JOB_HOSTPATH_MOUNTS", "[]"))
"""List of dictionaries composed of name, hostPath and mountPath.

- ``name``: name of the mount.
- ``hostPath``: path in the Kubernetes cluster host nodes that will be mounted into job pods.
- ``mountPath``: path inside job pods where hostPath will get mounted.
  This is optional, by default the same path as the hostPath will be used

This configuration should be used only when one knows for sure that the
specified locations exist in all the cluster nodes. For example, if all nodes in your cluster
have a directory ``/usr/local/share/mydata``, and you pass the following configuration:

.. code-block::

    REANA_JOB_HOSTPATH_MOUNTS = [
        {"name": "mydata",
         "hostPath": "/usr/local/share/mydata",
         "mountPath": "/mydata"},
    ]

All jobs will have ``/mydata`` mounted with the content of
``/usr/local/share/mydata`` from the Kubernetes cluster host node.
"""

REANA_WORKFLOW_UMASK = 0o0002
"""Umask used for workflow worksapce."""

WORKFLOW_RUNTIME_USER_NAME = os.getenv("WORKFLOW_RUNTIME_USER_NAME", "reana")
"""Default OS user name for running job controller."""

WORKFLOW_RUNTIME_USER_UID = os.getenv("WORKFLOW_RUNTIME_USER_UID", 1000)
"""Default user id for running job controller/workflow engine apps & jobs."""

WORKFLOW_RUNTIME_USER_GID = os.getenv("WORKFLOW_RUNTIME_USER_GID", 0)
"""Default group id for running job controller/workflow engine apps & jobs."""

REANA_USER_SECRET_MOUNT_PATH = os.getenv(
    "REANA_USER_SECRET_MOUNT_PATH", "/etc/reana/secrets"
)
"""Default mount path for user secrets which is mounted for job pod &
   workflow engines."""

SHARED_VOLUME_PATH = os.getenv("SHARED_VOLUME_PATH", "/var/reana")
"""Default shared volume path."""

K8S_CERN_EOS_MOUNT_CONFIGURATION = {
    "volume": {"name": "eos", "hostPath": {"path": "/var/eos"}},
    "volumeMounts": {
        "name": "eos",
        "mountPath": "/eos",
        "mountPropagation": "HostToContainer",
    },
}
"""Configuration to mount EOS in Kubernetes objects.

For more information see the official documentation at
https://clouddocs.web.cern.ch/containers/tutorials/eos.html.
"""

K8S_CERN_EOS_AVAILABLE = os.getenv("K8S_CERN_EOS_AVAILABLE")
"""Whether EOS is available in the current cluster or not.

This a configuration set by the system administrators through Helm values at
cluster creation time.
"""

REANA_INFRASTRUCTURE_KUBERNETES_SERVICEACCOUNT_NAME = os.getenv(
    "REANA_INFRASTRUCTURE_KUBERNETES_SERVICEACCOUNT_NAME"
)
"""REANA infrastructure service account."""

REANA_RUNTIME_KUBERNETES_SERVICEACCOUNT_NAME = os.getenv(
    "REANA_RUNTIME_KUBERNETES_SERVICEACCOUNT_NAME",
    REANA_INFRASTRUCTURE_KUBERNETES_SERVICEACCOUNT_NAME,
)
"""REANA runtime service account.

If no runtime namespace is deployed it will default to the infrastructure service
account.
"""
