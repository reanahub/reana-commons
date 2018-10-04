# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons module to manage AMQP consuming on REANA."""

from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin

from reana_commons.config import (BROKER, MQ_DEFAULT_EXCHANGE,
                                  MQ_DEFAULT_QUEUE, MQ_DEFAULT_ROUTING_KEY,
                                  MQ_DEFAULT_SERIALIZER)


class REANABaseConsumer(ConsumerMixin):
    """Base RabbitMQ consumer."""

    def __init__(self, connection=None, queues=None):
        """Construct a REANAConsumer.

        :param connection: kombu.Connection object.
        :param queues: List of queues names the consumer will subscribe to.
        """
        self.queues = queues or self._build_default_queues()
        self.connection = connection or Connection(BROKER)

    def _build_default_exchange(self):
        """."""
        exchange = Exchange(MQ_DEFAULT_EXCHANGE, type='direct')
        return exchange

    def _build_default_queues(self):
        default_queue = Queue(MQ_DEFAULT_QUEUE,
                              exchange=self._build_default_exchange(),
                              routing_key=MQ_DEFAULT_ROUTING_KEY)
        return [default_queue]

    def get_consumers(self, Consumer, channel):
        """Implement providing kombu.Consumers with queues/callbacks."""
        # return [Consumer(queues=self.queues,
        #                  callbacks=[self.on_message],
        #                  accept=[MQ_DEFAULT_SERIALIZER]))]
        raise NotImplementedError('Implement this method to map which'
                                  'callbacks are connected with which queues')

    def on_message(self, body, message):
        """Implement this method to manipulate the data received."""
        # print('Got message: {0}'.format(body))
        # message.ack()
        raise NotImplementedError('Implement this method to react to events.')
