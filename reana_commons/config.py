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


def kubernetes_node_label_to_dict(node_label):
    """Load Kubernetes node label to Python dict."""
    if node_label:
        label_name, value = node_label.split("=")
        return {label_name: value}

    return {}


REANA_RUNTIME_BATCH_KUBERNETES_NODE_LABEL = kubernetes_node_label_to_dict(
    os.getenv("REANA_RUNTIME_BATCH_KUBERNETES_NODE_LABEL")
)
"""Kubernetes label (with format ``label_name=label_value``) which identifies the nodes where the runtime batch workflows should run.

If not set, the runtime pods run in any available node in the cluster.
"""

REANA_RUNTIME_JOBS_KUBERNETES_NODE_LABEL = kubernetes_node_label_to_dict(
    os.getenv("REANA_RUNTIME_JOBS_KUBERNETES_NODE_LABEL")
)
"""Kubernetes label (with format ``label_name=label_value``) which identifies the nodes where the runtime jobs should run.

If not set, the runtime pods run in any available node in the cluster.
"""

REANA_RUNTIME_SESSIONS_KUBERNETES_NODE_LABEL = kubernetes_node_label_to_dict(
    os.getenv(
        "REANA_RUNTIME_SESSIONS_KUBERNETES_NODE_LABEL",
        os.getenv("REANA_RUNTIME_JOBS_KUBERNETES_NODE_LABEL"),
    )
)
"""Kubernetes label (with format ``label_name=label_value``) which identifies the nodes where the runtime sessions should run.

If not set, the runtime sessions run in the same nodes as runtime jobs if ``REANA_RUNTIME_JOBS_KUBERNETES_NODE_LABEL`` is set,
otherwise, they will be allocated in any available node in the cluster.
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

MQ_MAX_PRIORITY = 100
"""Declare the queue as a priority queue and set the highest priority number."""

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
        "max_priority": MQ_MAX_PRIORITY,
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

REANA_LOG_LEVEL = logging.getLevelName(os.getenv("REANA_LOG_LEVEL", "INFO"))
"""Log verbosity level for REANA components."""

REANA_LOG_FORMAT = os.getenv(
    "REANA_LOG_FORMAT",
    "%(asctime)s | %(name)s | %(threadName)s | " "%(levelname)s | %(message)s",
)
"""REANA components log format."""

CVMFS_REPOSITORIES = {
    "alice-ocdb.cern.ch": "alice-ocdb",
    "alice.cern.ch": "alice",
    "ams.cern.ch": "ams",
    "atlas-condb.cern.ch": "atlas-condb",
    "atlas-nightlies.cern.ch": "atlas-nightlies",
    "atlas.cern.ch": "atlas",
    "cernvm-prod.cern.ch": "cernvm-prod",
    "cms-ib.cern.ch": "cms-ib",
    "cms-opendata-conddb.cern.ch": "cms-opendata-conddb",
    "cms.cern.ch": "cms",
    "compass-condb.cern.ch": "compass-condb",
    "compass.cern.ch": "compass",
    "cvmfs-config.cern.ch": "cvmfs-config",
    "fcc.cern.ch": "fcc",
    "geant4.cern.ch": "geant4",
    "grid.cern.ch": "grid",
    "ilc.desy.de": "ilc-desy",
    "lhcb-condb.cern.ch": "lhcb-condb",
    "lhcb.cern.ch": "lhcb",
    "lhcbdev.cern.ch": "lhcbdev",
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


def workspaces(paths):
    """Tranform list of mounted workspaces as strings, to dictionary of pairs as cluster_node_path:cluster_pod_mountpath."""
    if isinstance(paths, list):
        return dict(p.split(":") for p in paths)
    return paths


WORKSPACE_PATHS = workspaces(json.loads(os.getenv("WORKSPACE_PATHS", "{}")))
"""Dictionary of available workspace paths with pairs of cluster_node_path:cluster_pod_mountpath."""


def default_workspace():
    """Obtain default workspace path."""
    workspaces_list = [path for path in list(WORKSPACE_PATHS.values())]
    return workspaces_list[0] if workspaces_list else SHARED_VOLUME_PATH


DEFAULT_WORKSPACE_PATH = default_workspace()
"""Default workspace path defined by the admin."""

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

HTCONDOR_JOB_FLAVOURS = {
    "espresso": 1200,
    "microcentury": 3600,
    "longlunch": 7200,
    "workday": 28800,
    "tomorrow": 86400,
    "testmatch": 259200,
    "nextweek": 604800,
}
"""HTCondor job flavours and their respective runtime in seconds."""

REANA_RESOURCE_HEALTH_COLORS = {
    "healthy": "green",
    "warning": "yellow",
    "critical": "red",
}
"""REANA mapping between resource health statuses and click-compatible colors."""

KUBERNETES_MEMORY_UNITS = ["E", "P", "T", "G", "M", "K"]
"""Kubernetes valid memory units"""

KUBERNETES_MEMORY_FORMAT = r"(?:(?P<value_bytes>\d+)|(?P<value_unit>(\d+[.])?\d+)(?P<unit>[{}])(?P<binary>i?))$".format(
    "".join(KUBERNETES_MEMORY_UNITS)
)
"""Kubernetes valid memory format regular expression e.g. Ki, M, Gi, G, etc."""

REANA_RUNTIME_KUBERNETES_KEEP_ALIVE_JOBS_WITH_STATUSES = os.getenv(
    "REANA_RUNTIME_KUBERNETES_KEEP_ALIVE_JOBS_WITH_STATUSES", ""
).split(",")
"""Keep alive Kubernetes user runtime jobs depending on status.

Keep alive both batch workflow jobs and invididual step jobs after termination
when their statuses match one of the specified comma-separated values
(possible values are: ``finished``, ``failed``). By default all jobs are
cleaned up.

Example: ``REANA_RUNTIME_KUBERNETES_KEEP_ALIVE_JOBS_WITH_STATUSES="finished,failed"``
would keep jobs that terminated successfully and jobs that failed.
"""

REANA_COMPUTE_BACKENDS = {
    "kubernetes": "Kubernetes",
    "htcondor": "HTCondor",
    "slurm": "Slurm",
}
"""REANA supported compute backends."""

REANA_WORKFLOW_ENGINES = ["yadage", "cwl", "serial", "snakemake"]
"""Available workflow engines."""

REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE = "snakemake/snakemake:v6.8.0"
"""Snakemake default job environment image."""
