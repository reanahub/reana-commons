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

from reana_commons.config import (MQ_CONNECTION_STRING, MQ_DEFAULT_EXCHANGE,
                                  MQ_DEFAULT_FORMAT, MQ_DEFAULT_QUEUE,
                                  MQ_DEFAULT_ROUTING_KEY)


class BaseConsumer(ConsumerMixin):
    """Base RabbitMQ consumer."""

    def __init__(self, connection=None, queues=None,
                 message_default_format=None):
        """Construct a BaseConsumer.

        :param connection: A :class:`kombu.Connection`, if not provided a
            :class:`kombu.Connection` with the default configuration will
            be instantiated.
        :param queues: List of :class:`kombu.Queue` where the messages will
            be consumed from, if not provided, it will be instantiated with
            the default configuration.
        :param message_default_format: Defines the format the consuemer is
            configured to deserialize the messages to.
        """
        self.queues = queues or self._build_default_queues()
        self.connection = connection or Connection(MQ_CONNECTION_STRING)
        self.message_default_format = message_default_format or \
            MQ_DEFAULT_FORMAT

    def _build_default_exchange(self):
        """Build :class:`kombu.Exchange` with default values."""
        return Exchange(MQ_DEFAULT_EXCHANGE, type='direct')

    def _build_default_queues(self):
        """Build :class:`kombu.Queue` with default values."""
        default_queue = Queue(MQ_DEFAULT_QUEUE,
                              durable=False,
                              exchange=self._build_default_exchange(),
                              routing_key=MQ_DEFAULT_ROUTING_KEY)
        return [default_queue]

    def get_consumers(self, Consumer, channel):
        """Map consumers to specific queues.

        :param Consumer: A :class:`kombu.Consumer` to use for instantiating
            consumers.
        :param channel: A :class:`kombu.transport.virtual.AbstractChannel`.
        """
        # return [Consumer(queues=self.queues,
        #                  callbacks=[self.on_message],
        #                  accept=[MQ_DEFAULT_FORMAT]))]
        raise NotImplementedError('Implement this method to map which'
                                  'callbacks are connected with which queues')

    def on_message(self, body, message):
        """Implement this method to manipulate the data received.

        :param body: The received message already decoded in the specified
            format.
        :param message: A :class:`kombu.transport.virtual.Message`.
        """
        raise NotImplementedError('Implement this method to react to events.')
