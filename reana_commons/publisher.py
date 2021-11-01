# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2020, 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons module to manage AMQP connections on REANA."""

import json
import logging

from kombu import Connection, Exchange, Queue

from .config import (
    MQ_CONNECTION_STRING,
    MQ_DEFAULT_EXCHANGE,
    MQ_DEFAULT_FORMAT,
    MQ_DEFAULT_QUEUES,
    MQ_PRODUCER_MAX_RETRIES,
)


class BasePublisher(object):
    """Base publisher to MQ."""

    def __init__(
        self,
        queue,
        routing_key,
        connection=None,
        exchange=None,
        durable=False,
        max_priority=None,
    ):
        """Initialise the BasePublisher class.

        :param connection: A :class:`kombu.Connection`, if not provided a
            :class:`kombu.Connection` with the default configuration will
            be instantiated.
        :param queue: String which represents the queue the messages will
            be sent to.
        :param routing_key: String which represents the routing key which
            will be used to send the messages, if not provided default
            routing key will be used.
        :param exchange: A :class:`kombu.Exchange` where the messages will
            be delivered to, if not provided, it will be instantiated with
            the default configuration.
        """
        self._routing_key = routing_key
        self._exchange = (
            exchange
            if isinstance(exchange, Exchange)
            else Exchange(name=exchange or MQ_DEFAULT_EXCHANGE, type="direct")
        )
        self._queue = (
            queue
            if isinstance(queue, Queue)
            else Queue(
                queue,
                durable=durable,
                exchange=self._exchange,
                routing_key=self._routing_key,
                max_priority=max_priority,
            )
        )
        self._connection = connection or Connection(MQ_CONNECTION_STRING)
        self.producer = self._build_producer()

    def _build_producer(self):
        """Instantiate a :class:`kombu.Producer`."""
        return self._connection.Producer(serializer=MQ_DEFAULT_FORMAT)

    def __error_callback(self, exception, interval):
        """Execute when there is an error while sending a message.

        :param exception: Exception which has been thrown while trying to send
            the message.
        :param interval: Interval in which the message delivery will be
            retried.
        """
        logging.error("Error while publishing {}".format(exception))
        logging.info("Retry in %s seconds.", interval)

    def _publish(self, msg, priority=None):
        """Publish, handling retries, a message in the queue.

        :param msg: Object which represents the message to be sent in
            the queue. Note that this object should be serializable in the
            configured format (by default JSON).
        :param priority: Message priority.
        """
        connection = self._connection.clone()
        publish = connection.ensure(
            self.producer,
            self.producer.publish,
            errback=self.__error_callback,
            max_retries=MQ_PRODUCER_MAX_RETRIES,
        )
        publish(
            json.dumps(msg),
            exchange=self._exchange,
            routing_key=self._routing_key,
            declare=[self._queue],
            priority=priority,
        )
        logging.debug("Publisher: message sent: %s", msg)

    def close(self):
        """Close connection."""
        logging.debug("Publisher: closing queue connection")
        self._connection.release()


class WorkflowStatusPublisher(BasePublisher):
    """Progress publisher to MQ."""

    def __init__(self, **kwargs) -> None:
        """Initialise the WorkflowStatusPublisher class."""
        queue = "jobs-status"
        if "queue" not in kwargs:
            kwargs["queue"] = "jobs-status"
        if "routing_key" not in kwargs:
            kwargs["routing_key"] = MQ_DEFAULT_QUEUES[queue]["routing_key"]
        if "durable" not in kwargs:
            kwargs["durable"] = MQ_DEFAULT_QUEUES[queue]["durable"]
        if "max_priority" not in kwargs:
            kwargs["max_priority"] = MQ_DEFAULT_QUEUES[queue]["max_priority"]
        super(WorkflowStatusPublisher, self).__init__(**kwargs)

    def publish_workflow_status(
        self, workflow_uuid, status, logs="", message=None
    ) -> None:
        """Publish workflow status.

        `Status` parameter is also used as a
        priority number in the queue. This allows messages with a bigger
        status number to be prioritized faster.

        :param workflow_uuid: String which represents the workflow UUID.
        :param status: Integer which represents the status of the workflow,
            this is defined in the `reana-db` `Workflow` models.
        :param logs: String which represents the logs which the workflow
            has produced as output.
        :param message: Dictionary which includes additional information
            can be attached such as the overall progress of the workflow.
        """
        msg = {
            "workflow_uuid": workflow_uuid,
            "logs": logs,
            "status": status,
            "priority": status,
            "message": message,
        }
        self._publish(msg)


class WorkflowSubmissionPublisher(BasePublisher):
    """Workflow submission publisher."""

    def __init__(self, **kwargs) -> None:
        """Initialise the WorkflowSubmissionPublisher class."""
        queue = "workflow-submission"
        super(WorkflowSubmissionPublisher, self).__init__(
            queue,
            MQ_DEFAULT_QUEUES[queue]["routing_key"],
            durable=MQ_DEFAULT_QUEUES[queue]["durable"],
            max_priority=MQ_DEFAULT_QUEUES[queue]["max_priority"],
            **kwargs
        )

    def publish_workflow_submission(
        self, user_id, workflow_id_or_name, parameters, priority=0, min_job_memory=0,
    ) -> None:
        """Publish workflow submission parameters."""
        msg = {
            "user": user_id,
            "workflow_id_or_name": workflow_id_or_name,
            "parameters": parameters,
            "priority": priority,
            "min_job_memory": min_job_memory,
        }
        self._publish(msg, priority)
