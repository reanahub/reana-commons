# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Commons configuration."""

import logging
import os

MQ_URL = os.getenv('RABBIT_MQ_URL',
                   'reana-message-broker.default.svc.cluster.local')
"""Message queue (RabbitMQ) server host name."""

MQ_USER = os.getenv('RABBIT_MQ_USER', 'test')
"""Message queue (RabbitMQ) user name."""

MQ_PASS = os.getenv('RABBIT_MQ_PASS', '1234')
"""Message queue (RabbitMQ) password."""

MQ_PORT = os.getenv('RABBIT_MQ_PORT', 5672)
"""Message queue (RabbitMQ) service port."""

MQ_CONNECTION_STRING = os.getenv('RABBIT_MQ', 'amqp://{0}:{1}@{2}//'.format(
    MQ_USER, MQ_PASS, MQ_URL))
"""Message queue (RabbitMQ) connection string."""

MQ_DEFAULT_FORMAT = 'json'
"""Default serializing format (to consume/produce)."""

MQ_DEFAULT_EXCHANGE = ''
"""Message queue (RabbitMQ) exchange."""

MQ_DEFAULT_QUEUES = {'jobs-status':
                     {'routing_key': 'jobs-status',
                      'exchange': MQ_DEFAULT_EXCHANGE,
                      'durable': False},
                     'workflow-submission':
                     {'routing_key': 'workflow-submission',
                      'exchange': MQ_DEFAULT_EXCHANGE,
                      'durable': True}
                     }
"""Default message queues."""

MQ_PRODUCER_MAX_RETRIES = 3
"""Max retries to send a message."""

OPENAPI_SPECS = {
    'reana-workflow-controller': (
        'http://{address}:{port}'.format(
            address=os.getenv('REANA_WORKFLOW_CONTROLLER_SERVICE_HOST',
                              '0.0.0.0'),
            port=os.getenv('REANA_WORKFLOW_CONTROLLER_SERVICE_PORT_HTTP',
                           '5000')),
        'reana_workflow_controller.json'),
    'reana-server': (
        os.getenv('REANA_SERVER_URL', 'http://0.0.0.0:80'),
        'reana_server.json'),
    'reana-job-controller': (
        'http://{address}:{port}'.format(
            address=os.getenv('REANA_JOB_CONTROLLER_SERVICE_HOST', '0.0.0.0'),
            port=os.getenv('REANA_JOB_CONTROLLER_SERVICE_PORT_HTTP', '5000')),
        'reana_job_controller.json')
}
"""REANA Workflow Controller address."""

REANA_MAX_CONCURRENT_BATCH_WORKFLOWS = int(os.getenv(
    'REANA_MAX_CONCURRENT_BATCH_WORKFLOWS', '30'))
"""Upper limit on concurrent REANA batch workflows running in the cluster."""

REANA_READY_CONDITIONS = {'reana_commons.tasks':
                          ['check_predefined_conditions',
                           'check_running_reana_batch_workflows_count']}

REANA_LOG_LEVEL = logging.getLevelName(os.getenv('REANA_LOG_LEVEL', 'INFO'))
"""Log verbosity level for REANA components."""

REANA_LOG_FORMAT = os.getenv('REANA_LOG_FORMAT',
                             '%(asctime)s | %(name)s | %(threadName)s | '
                             '%(levelname)s | %(message)s')
"""REANA components log format."""

CVMFS_REPOSITORIES = {
    'alice.cern.ch': 'alice',
    'alice-ocdb.cern.ch': 'alice-ocdb',
    'ams.cern.ch': 'ams',
    'atlas.cern.ch': 'atlas',
    'atlas-condb.cern.ch': 'atlas-condb',
    'atlas-nightlies.cern.ch': 'atlas-nightlies',
    'cms.cern.ch': 'cms',
    'cms-ib.cern.ch': 'cms-ib',
    'cms-opendata-conddb.cern.ch': 'cms-opendata-conddb',
    'compass.cern.ch': 'compass',
    'compass-condb.cern.ch': 'compass-condb',
    'cvmfs-config.cern.ch': 'cvmfs-config',
    'fcc.cern.ch': 'fcc',
    'geant4.cern.ch': 'geant4',
    'ilc.desy.de': 'ilc-desy',
    'lhcb.cern.ch': 'lhcb',
    'lhcb-condb.cern.ch': 'lhcb-condb',
    'na61.cern.ch': 'na61',
    'na62.cern.ch': 'na62',
    'projects.cern.ch': 'projects',
    'sft.cern.ch': 'sft',
    'unpacked.cern.ch': 'unpacked'
}
"""CVMFS repositories available for mounting."""

REANA_CVMFS_PVC_TEMPLATE = {
    "metadata":
        {"name": ""},
    "spec":
        {"accessModes": ["ReadOnlyMany"],
         "storageClassName": "",
         "resources": {"requests": {"storage": "1G"}}}
}
"""CVMFS persistent volume claim template."""

REANA_CVMFS_SC_TEMPLATE = {
    "metadata":
        {"name": ""},
    "provisioner": "cvmfs.csi.cern.ch",
    "parameters":
        {"repository": ""}
}
"""CVMFS storage claim template."""

INTERACTIVE_SESSION_TYPES = ['jupyter']
"""List of supported interactive systems."""

REANA_STORAGE_BACKEND = os.getenv('REANA_STORAGE_BACKEND', 'local')
"""Storage backend deployed in current REANA cluster ['local'|'cephfs']."""

REANA_CEPHFS_PVC_NAME = os.getenv("REANA_CEPHFS_PVC_NAME", "reana-cephfs")
"""Name of the shared CEPHFS PVC which will be used by all REANA jobs."""

REANA_WORKFLOW_UMASK = 0o0002
"""Umask used for workflow worksapce."""

K8S_DEFAULT_NAMESPACE = "default"
"""Kubernetes workflow runtime default namespace"""

WORKFLOW_RUNTIME_USER_NAME = os.getenv(
    'WORKFLOW_RUNTIME_USER_NAME',
    'reana')
"""Default OS user name for running job controller."""

WORKFLOW_RUNTIME_USER_UID = os.getenv(
    'WORKFLOW_RUNTIME_USER_UID',
    1000)
"""Default user id for running job controller/workflow engine apps & jobs."""

WORKFLOW_RUNTIME_USER_GID = os.getenv(
    'WORKFLOW_RUNTIME_USER_GID',
    0)
"""Default group id for running job controller/workflow engine apps & jobs."""

REANA_USER_SECRET_MOUNT_PATH = os.getenv(
    'REANA_USER_SECRET_MOUNT_PATH',
    '/etc/reana/secrets'
)
"""Default mount path for user secrets which is mounted for job pod &
   workflow engines."""

SHARED_VOLUME_PATH = os.getenv('SHARED_VOLUME_PATH', '/var/reana')
"""Default shared volume path."""

K8S_CERN_EOS_MOUNT_CONFIGURATION = {
    'volume': {
        "name": "eos",
        "hostPath": {
                "path": "/var/eos"
        }
    },
    'volumeMounts':   {
        "name": "eos",
        "mountPath": "/eos",
        "mountPropagation": "HostToContainer"
    }
}
"""Configuration to mount EOS in Kubernetes objects.

For more information see the official documentation at
https://clouddocs.web.cern.ch/containers/tutorials/eos.html.
"""

K8S_CERN_EOS_AVAILABLE = os.getenv('K8S_CERN_EOS_AVAILABLE')
"""Whether EOS is available in the current cluster or not.

This a configuration set by the system administrators through Helm values at
cluster creation time.
"""

K8S_REANA_SERVICE_ACCOUNT_NAME = os.getenv('K8S_REANA_SERVICE_ACCOUNT_NAME')
"""REANA service account in the deployed Kubernetes cluster."""
