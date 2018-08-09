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
# You should have received a copy of the GNU General Public License along with
# REANA; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307, USA.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization or
# submit itself to any jurisdiction.
"""REANA-Commons module to manage AMQP connections on REANA."""

import json
import logging

import pika

from .config import (BROKER_PASS, BROKER_PORT, BROKER_URL, BROKER_USER,
                     EXCHANGE, ROUTING_KEY, STATUS_QUEUE)


class Publisher:
    """Progress publisher to MQ."""

    def __init__(self):
        """Initialise the Publisher class."""
        self.broker_credentials = pika.PlainCredentials(BROKER_USER,
                                                        BROKER_PASS)
        self._params = pika.connection.ConnectionParameters(
            BROKER_URL, BROKER_PORT, '/', self.broker_credentials)
        self._conn = None
        self._channel = None

    def connect(self):
        """Connect to MQ channel."""
        if not self._conn or self._conn.is_closed:
            self._conn = pika.BlockingConnection(self._params)
            self._channel = self._conn.channel()
            self._channel.queue_declare(queue=STATUS_QUEUE)

    def _publish(self, msg):
        self._channel.basic_publish(exchange=EXCHANGE,
                                    routing_key=ROUTING_KEY,
                                    body=json.dumps(msg))
        logging.debug('Publisher: message sent: %s', msg)

    def publish_workflow_status(self, workflow_uuid, status,
                                logs='', message=None):
        """Publish msg, reconnecting if necessary."""
        try:
            msg = {"workflow_uuid": workflow_uuid,
                   "logs": logs,
                   "status": status,
                   "message": message}
            self._publish(msg)
        except pika.exceptions.ConnectionClosed:
            logging.debug('Publisher: ConnectionClosed, reconnecting.')
            print('Publisher: ConnectionClosed, reconnecting.')
            self.connect()
            self._publish(msg)

    def close(self):
        """Close AMQP connection."""
        if self._conn and self._conn.is_open:
            logging.debug('Publisher: closing queue connection')
            self._conn.close()
