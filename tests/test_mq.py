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
from unittest.mock import ANY, patch

import pytest
from kombu import Connection, Exchange, Queue
from kombu.exceptions import OperationalError

from conftest import REANABaseConsumerTestIMPL
from reana_commons.publisher import WorkflowStatusPublisher


def test_consume_msg(in_memory_queue_connection, default_queue,
                     default_producer):
    """Test message is consumed from the queue."""
    with patch.object(REANABaseConsumerTestIMPL,
                      'on_message') as mock_on_message:
        consumer = REANABaseConsumerTestIMPL(
            connection=in_memory_queue_connection,
            queues=[default_queue])
        default_producer.publish({'hello': 'REANA'}, declare=[default_queue])
        consumer_generator = consumer.consume(limit=1)
        next(consumer_generator)
        mock_on_message.assert_called_once_with(
            {'hello': 'REANA'}, ANY)


def test_server_server_unreachable(default_queue):
    """Test message is consumed from the queue."""
    unreachable_connection = Connection('amqp://unreachable:5672')
    consumer = REANABaseConsumerTestIMPL(connection=unreachable_connection)
    with pytest.raises(OperationalError):
        # Typically we will leave by default the connection max retires since
        # the REANABaseConsumer takes care of recovering connection through
        # ``kombu.mixins.ConsumerMixin`` but for the sake of the test we set
        # it to 1.
        consumer.connect_max_retries = 1
        consumer.run()


def test_workflow_status_publish(in_memory_queue_connection, default_queue):
    """."""
    with patch.object(REANABaseConsumerTestIMPL,
                      'on_message') as mock_on_message:
        consumer = REANABaseConsumerTestIMPL(
            connection=in_memory_queue_connection,
            queues=[default_queue])
        workflow_status_publisher = WorkflowStatusPublisher(
            connection=in_memory_queue_connection)
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
        consumer_generator = consumer.consume(limit=1)
        next(consumer_generator)
        mock_on_message.assert_called_once_with(
            expected, ANY)


def test_workflow_status_publish_multiple(in_memory_queue_connection,
                                          default_queue):
    """."""
    with patch.object(REANABaseConsumerTestIMPL,
                      'on_message') as mock_on_message:
        consumer = REANABaseConsumerTestIMPL(
            connection=in_memory_queue_connection,
            queues=[default_queue])
        workflow_status_publisher = WorkflowStatusPublisher(
            connection=in_memory_queue_connection)
        num_messages = 10
        for i in range(num_messages):
            workflow_id = 'test{}'.format(i)
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
        consumer_generator = consumer.consume(limit=num_messages)
        while True:
            try:
                next(consumer_generator)
            except StopIteration:
                # no more items to consume in the queue
                break

        assert mock_on_message.call_count == 10
