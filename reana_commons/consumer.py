# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons module to manage AMQP consuming on REANA."""

import pika

from .config import BROKER_PASS, BROKER_PORT, BROKER_URL, BROKER_USER


class Consumer:
    """Base MQ Consumer."""

    def __init__(self, queue):
        """Constructor."""
        self.broker_credentials = pika.PlainCredentials(BROKER_USER,
                                                        BROKER_PASS)
        self._params = pika.connection.ConnectionParameters(
            BROKER_URL, BROKER_PORT, '/', self.broker_credentials)
        self._conn = None
        self._channel = None
        self._queue = queue

    def connect(self):
        """Connect to MQ channel."""
        if not self._conn or self._conn.is_closed:
            self._conn = pika.BlockingConnection(self._params)
            self._channel = self._conn.channel()
            self._channel.basic_qos(prefetch_count=1)
            self._channel.queue_declare(queue=self._queue)

    def on_message(self, channel, method_frame, header_frame, body):
        """On new message event handler."""
        # this method should be overriden by the inheriting class
        pass

    def consume(self):
        """Start consuming incoming messages."""
        while True:
            self.connect()
            self._channel.basic_consume(self.on_message, self._queue)
            try:
                self._channel.start_consuming()
            except KeyboardInterrupt:
                self._channel.stop_consuming()
                self._conn.close()
            except pika.exceptions.ConnectionClosedByBroker:
                # Uncomment this to make the example not attempt recovery
                # from server-initiated connection closure, including
                # when the node is stopped cleanly
                # except pika.exceptions.ConnectionClosedByBroker:
                #     pass
                continue
