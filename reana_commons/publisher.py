# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons module to manage AMQP connections on REANA."""

import json
import logging

from kombu import Connection, Exchange, Queue

from .config import (BROKER, BROKER_PASS, BROKER_PORT, BROKER_URL, BROKER_USER,
                     EXCHANGE, MQ_DEFAULT_EXCHANGE, MQ_DEFAULT_QUEUE,
                     MQ_DEFAULT_ROUTING_KEY, MQ_DEFAULT_SERIALIZER,
                     MQ_PRODUCER_MAX_RETRIES, ROUTING_KEY, STATUS_QUEUE)


class WorkflowStatusPublisher():
    """Progress publisher to MQ."""

    def __init__(self, connection=None, routing_key=None, exchange=None):
        """Initialise the Publisher class."""
        self._routing_key = routing_key or MQ_DEFAULT_ROUTING_KEY
        self._exchange = Exchange(name=exchange or MQ_DEFAULT_EXCHANGE,
                                  type='direct')
        self._queue = Queue(MQ_DEFAULT_QUEUE, exchange=MQ_DEFAULT_EXCHANGE,
                            routing_key=self._routing_key)
        self._connection = connection or Connection(BROKER)
        self.producer = self._producer()

    def _producer(self):
        """Instantiate the ``kombu.Producer``."""
        return self._connection.Producer(serializer=MQ_DEFAULT_SERIALIZER)

    def __error_callback(self, exception, interval):
        """."""
        logging.error('Error while publishing {}'.format(
            exception))
        logging.info('Retry in %s seconds.', interval)

    def _publish(self, msg):
        """."""
        connection = self._connection.clone()
        publish = connection.ensure(self.producer, self.producer.publish,
                                    errback=self.__error_callback,
                                    max_retries=MQ_PRODUCER_MAX_RETRIES)
        publish(json.dumps(msg), exchange=self._exchange,
                routing_key=self._routing_key, declare=[self._queue])

    def publish_workflow_status(self, workflow_uuid, status,
                                logs='', message=None):
        """."""
        msg = {
            "workflow_uuid": workflow_uuid,
            "logs": logs,
            "status": status,
            "message": message
        }
        self._publish(msg)
        logging.debug('Publisher: message sent: %s', msg)

    def close(self):
        """Close connection."""
        logging.debug('Publisher: closing queue connection')
        self._connection.release()
