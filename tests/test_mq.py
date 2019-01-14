# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# REANA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with REANA; if not, see <http://www.gnu.org/licenses>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization or
# submit itself to any jurisdiction.

"""REANA-Commons message queue publisher tests."""

import json
import threading

import pytest
from kombu import Connection, Exchange, Queue
from kombu.exceptions import OperationalError
from mock import ANY, patch

from reana_commons.publisher import WorkflowStatusPublisher


def test_consume_msg(ConsumerBaseOnMessageMock, in_memory_queue_connection,
                     default_queue, default_in_memory_producer,
                     consume_queue):
    """Test message is consumed from the queue."""
    consumer = ConsumerBaseOnMessageMock(
        connection=in_memory_queue_connection,
        queue=default_queue)
    default_in_memory_producer.publish({'hello': 'REANA'},
                                       declare=[default_queue])
    consume_queue(consumer, limit=1)
    consumer.on_message.assert_called_once_with(
        {'hello': 'REANA'}, ANY)


def test_server_unreachable(ConsumerBase, default_queue):
    """Test consumer never starts because server is unreachable."""
    unreachable_connection = Connection('amqp://unreachable:5672')
    consumer = ConsumerBase(queue=default_queue,
                            connection=unreachable_connection)
    with pytest.raises(OperationalError):
        # Typically we will leave by default the connection max retires since
        # the BaseConsumer takes care of recovering connection through
        # ``kombu.mixins.ConsumerMixin`` but for the sake of the test we set
        # it to 1.
        consumer.connect_max_retries = 1
        consumer.run()


def test_workflow_status_publish(ConsumerBaseOnMessageMock,
                                 in_memory_queue_connection,
                                 default_queue,
                                 consume_queue):
    """Test WorkflowStatusPublisher."""
    consumer = ConsumerBaseOnMessageMock(
        connection=in_memory_queue_connection,
        queue=default_queue)
    workflow_status_publisher = WorkflowStatusPublisher(
        connection=in_memory_queue_connection,
        routing_key=default_queue.routing_key,
        exchange=default_queue.exchange.name,
        queue=default_queue.name)
    workflow_id = 'test'
    status = 1
    message = {
        'progress': {
            'total':
            {'total': 1,
                'job_ids': []},
        }}
    workflow_status_publisher.publish_workflow_status(workflow_id,
                                                      status,
                                                      message=message)
    workflow_status_publisher.close()
    expected = json.dumps({
        'workflow_uuid': workflow_id,
        'logs': '',
        'status': status,
        'message': message
    })
    consume_queue(consumer, limit=1)
    consumer.on_message.assert_called_once_with(
        expected, ANY)
