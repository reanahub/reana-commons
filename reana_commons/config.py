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
                   'message-broker.default.svc.cluster.local')
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
            address=os.getenv('WORKFLOW_CONTROLLER_SERVICE_HOST', '0.0.0.0'),
            port=os.getenv('WORKFLOW_CONTROLLER_SERVICE_PORT_HTTP', '5000')),
        'reana_workflow_controller.json'),
    'reana-server': (
        os.getenv('REANA_SERVER_URL'),
        'reana_server.json'),
    'reana-job-controller': (
        'http://{address}:{port}'.format(
            address=os.getenv('JOB_CONTROLLER_SERVICE_HOST', '0.0.0.0'),
            port=os.getenv('JOB_CONTROLLER_SERVICE_PORT_HTTP', '5000')),
        'reana_job_controller.json')
}
"""REANA Workflow Controller address."""

K8S_MAXIMUM_CONCURRENT_JOBS = 10
"""Upper limit on concurrent jobs running in the cluster."""

REANA_READY_CONDITIONS = {'reana_commons.tasks':
                          ['check_predefined_conditions',
                           'check_running_job_count']}

REANA_ENGINE_LOG_LEVEL = os.getenv('ENGINE_LOG_LEVEL', logging.DEBUG)
"""Level of verbosity for engine logs."""

REANA_ENGINE_LOG_FORMAT = os.getenv('ENGINE_LOG_FORMAT',
                                    '%(asctime)s - '
                                    '%(name)s - '
                                    '%(levelname)s - '
                                    '%(message)s')
"""Format of engine logs."""

CVMFS_REPOSITORIES = {
    'alice.cern.ch': 'alice',
    'alice-ocdb.cern.ch': 'alice-ocdb',
    'ams.cern.ch': 'ams',
    'atlas.cern.ch': 'atlas',
    'atlas-condb.cern.ch': 'atlas-condb',
    'atlas-nightlies.cern.ch': 'atlas-nightlies',
    'cms.cern.ch': 'cms',
    'cms-ib.cern.ch': 'cms-ib',
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
    'sft.cern.ch': 'sft'
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
    "provisioner": "csi-cvmfsplugin",
    "parameters":
        {"repository": ""}
}
"""CVMFS storage claim template."""
