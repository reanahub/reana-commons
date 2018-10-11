# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Commons configuration."""

import os

BROKER_URL = os.getenv('RABBIT_MQ_URL',
                       'message-broker.default.svc.cluster.local')
"""RabbitMQ server host name."""

BROKER_USER = os.getenv('RABBIT_MQ_USER', 'test')
"""RabbitMQ user name."""

BROKER_PASS = os.getenv('RABBIT_MQ_PASS', '1234')
"""RabbitMQ password."""

BROKER_PORT = os.getenv('RABBIT_MQ_PORT', 5672)
"""RabbitMQ service port."""

BROKER = os.getenv('RABBIT_MQ', 'amqp://{0}:{1}@{2}//'.format(BROKER_USER,
                                                              BROKER_PASS,
                                                              BROKER_URL))
"""RabbitMQ connection string."""

STATUS_QUEUE = 'jobs-status'
"""Name of the queue where to publish/consume from."""

EXCHANGE = ''
"""RabbitMQ exchange."""

ROUTING_KEY = 'jobs-status'
"""RabbitMQ routing key."""

OPENAPI_SPECS = {
    'reana-workflow-controller': (
        'http://{address}:{port}'.format(
            address=os.getenv('WORKFLOW_CONTROLLER_SERVICE_HOST', '0.0.0.0'),
            port=os.getenv('WORKFLOW_CONTROLLER_SERVICE_PORT_HTTP', '5000')),
        'reana_workflow_controller.json'),
    'reana-server': (
        os.getenv('REANA_SERVER_URL', None),
        'reana_server.json'),
    'reana-job-controller': (
        'http://{address}:{port}'.format(
            address=os.getenv('JOB_CONTROLLER_SERVICE_HOST', '0.0.0.0'),
            port=os.getenv('JOB_CONTROLLER_SERVICE_PORT_HTTP', '5000')),
        'reana_job_controller.json')
}
"""REANA Workflow Controller address."""
