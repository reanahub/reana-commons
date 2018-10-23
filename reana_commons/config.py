# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Commons configuration."""

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

MQ_DEFAULT_QUEUE = 'jobs-status'
"""Name of the queue where to publish/consume from."""

MQ_DEFAULT_ROUTING_KEY = 'jobs-status'
"""Message queue (RabbitMQ) routing key."""

MQ_PRODUCER_MAX_RETRIES = 3
"""Max retries to send a message."""

OPENAPI_SPECS = {
    'reana-workflow-controller': (
        'http://{address}:{port}'.format(
            address=os.getenv('WORKFLOW_CONTROLLER_SERVICE_HOST', '0.0.0.0'),
            port=os.getenv('WORKFLOW_CONTROLLER_SERVICE_PORT_HTTP', '5000')),
        'reana_workflow_controller.json'),
    'reana-server': (
        os.getenv('REANA_SERVER_URL', '0.0.0.0'),
        'reana_server.json'),
    'reana-job-controller': (
        'http://{address}:{port}'.format(
            address=os.getenv('JOB_CONTROLLER_SERVICE_HOST', '0.0.0.0'),
            port=os.getenv('JOB_CONTROLLER_SERVICE_PORT_HTTP', '5000')),
        'reana_job_controller.json')
}
"""REANA Workflow Controller address."""
