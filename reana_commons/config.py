# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2020, 2021, 2022, 2023, 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Commons configuration."""

import json
import logging
import os

import pkg_resources
import yaml

from reana_commons.errors import REANAConfigDoesNotExist


class REANAConfig:
    """REANA global configuration class."""

    path = "/var/reana/config"
    config_mapping = {"ui": "ui-config.yaml"}

    @classmethod
    def _read_file(cls, filename):
        with open(os.path.join(cls.path, filename)) as yaml_file:
            data = yaml.load(yaml_file, Loader=yaml.FullLoader)
            return data

    @classmethod
    def load(cls, kind):
        """REANA-UI configuration."""
        if kind not in cls.config_mapping:
            raise REANAConfigDoesNotExist(
                "{} configuration does not exist".format(kind)
            )
        return cls._read_file(cls.config_mapping[kind])


reana_yaml_schema_file_path = pkg_resources.resource_filename(
    __name__, "validation/schemas/reana_analysis_schema.json"
)
"""REANA specification schema location."""

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
    KUBERNETES_SERVICE_DNS_DOMAIN = os.getenv(
    "KUBERNETES_SERVICE_DNS_DOMAIN", "cluster.local"
    )
"""Kubernetes service DNS domain"""
    component_name: (
        "{component_prefix}-{component_name}.{namespace}.svc.{service_dns_domain}"
    ).format(
        component_prefix=REANA_COMPONENT_PREFIX,
        component_name=component_name,
        namespace=REANA_INFRASTRUCTURE_KUBERNETES_NAMESPACE,
        service_dns_domain=KUBERNETES_SERVICE_DNS_DOMAIN,
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

REANA_CVMFS_STORAGE_CLASS_NAME = f"{REANA_COMPONENT_PREFIX}-cvmfs"
"""Name of the StorageClass used to mount CVMFS repositories."""

REANA_CVMFS_PVC_NAME = f"{REANA_COMPONENT_PREFIX}-cvmfs"
"""Name of the PersistentVolumeClaim used to mount CVMFS repositories."""

REANA_CVMFS_PVC = {
    "metadata": {
        "name": REANA_CVMFS_PVC_NAME,
        "namespace": REANA_RUNTIME_KUBERNETES_NAMESPACE,
    },
    "spec": {
        "accessModes": ["ReadOnlyMany"],
        "storageClassName": REANA_CVMFS_STORAGE_CLASS_NAME,
        "resources": {"requests": {"storage": 1}},
    },
}
"""PersistentVolumeClaim used to mount CVMFS repositories."""

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

REANA_WORKFLOW_NAME_ILLEGAL_CHARACTERS = ["."]
"""List of illegal characters for workflow name validation."""

REANA_WORKFLOW_UMASK = 0o0002
"""Umask used for workflow workspace."""

WORKFLOW_RUNTIME_USER_NAME = os.getenv("WORKFLOW_RUNTIME_USER_NAME", "reana")
"""Default OS user name for running job controller."""

WORKFLOW_RUNTIME_GROUP_NAME = os.getenv("WORKFLOW_RUNTIME_GROUP_NAME", "root")
"""Default OS group name for running job controller."""

WORKFLOW_RUNTIME_USER_UID = os.getenv("WORKFLOW_RUNTIME_USER_UID", 1000)
"""Default user id for running job controller/workflow engine apps & jobs."""

WORKFLOW_RUNTIME_USER_GID = os.getenv("WORKFLOW_RUNTIME_USER_GID", 0)
"""Default group id for running job controller/workflow engine apps & jobs.

If the group id is changed to a value different than zero, then also the
`WORKFLOW_RUNTIME_GROUP_NAME` needs to be changed to a value different than `root`.
"""

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

WORKFLOW_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
"""Time format for workflow starting time, created time etc."""

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


K8S_USE_SECURITY_CONTEXT = (
    os.getenv("K8S_USE_SECURITY_CONTEXT", "True").lower() == "true"
)
"""Whether to use Kubernetes security contexts or not.

This (enabled by default) runs workflows as the WORKFLOW_RUNTIME_USER_UID and
WORKFLOW_RUNTIME_USER_GID.  It should be set to False for systems (like OpenShift)
that assign ephemeral UIDs.
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

statuses = os.getenv("REANA_RUNTIME_KUBERNETES_KEEP_ALIVE_JOBS_WITH_STATUSES", [])
REANA_RUNTIME_KUBERNETES_KEEP_ALIVE_JOBS_WITH_STATUSES = (
    statuses.split(",") if statuses else statuses
)
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

REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE = "docker.io/snakemake/snakemake:v7.32.4"
"""Snakemake default job environment image."""

REANA_JOB_CONTROLLER_CONNECTION_CHECK_SLEEP = float(
    os.getenv("REANA_JOB_CONTROLLER_CONNECTION_CHECK_SLEEP", "10")
)
"""How many seconds to wait between job controller connection checks."""

COMMAND_DANGEROUS_OPERATIONS = ["sudo ", "cd /"]
"""Operations in workflow commands considered dangerous."""

# Kerberos configurations

KRB5_CONTAINER_IMAGE = os.getenv(
    "KRB5_CONTAINER_IMAGE", "docker.io/reanahub/reana-auth-krb5:1.0.3"
)
"""Default docker image of KRB5 sidecar container."""

KRB5_INIT_CONTAINER_NAME = "krb5-init"
"""Name of KRB5 init container."""

KRB5_RENEW_CONTAINER_NAME = "krb5-renew"
"""Name of KRB5 sidecar container used for ticket renewal."""

KRB5_STATUS_FILE_CHECK_INTERVAL = 15
"""Time interval in seconds between checks to the status file."""

KRB5_TICKET_RENEW_INTERVAL = 21600  # 6 hours
"""Time interval in seconds between renewals of the KRB5 ticket."""

KRB5_TOKEN_CACHE_LOCATION = "/krb5_cache/"
"""Directory of Kerberos tokens cache, shared between job/engine & KRB5 container. It
should match `default_ccache_name` in krb5.conf.
"""

KRB5_TOKEN_CACHE_FILENAME = "krb5_{}"
"""Name of the Kerberos token cache file."""

KRB5_STATUS_FILENAME = "status_file"
"""Name of status file used to terminate KRB5 renew container when the main
job finishes."""

KRB5_STATUS_FILE_LOCATION = os.path.join(
    KRB5_TOKEN_CACHE_LOCATION, KRB5_STATUS_FILENAME
)
"""Status file path used to terminate KRB5 renew container when the main
job finishes."""

KRB5_CONFIGMAP_NAME = os.getenv(
    "REANA_KRB5_CONFIGMAP_NAME", f"{REANA_COMPONENT_PREFIX}-krb5-conf"
)
"""Kerberos configMap name."""
