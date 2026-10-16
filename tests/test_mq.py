# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2020, 2021, 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons message queue publisher tests."""

import json
import threading

import pytest
from kombu import Connection, Exchange, Queue
from kombu.exceptions import OperationalError
from mock import ANY, patch

from reana_commons.publisher import WorkflowStatusPublisher

pytest_plugins = ["pytester"]


def test_consume_msg(
    ConsumerBaseOnMessageMock,
    in_memory_queue_connection,
    default_queue,
    default_in_memory_producer,
    consume_queue,
):
    """Test message is consumed from the queue."""
    consumer = ConsumerBaseOnMessageMock(
        connection=in_memory_queue_connection, queue=default_queue
    )
    default_in_memory_producer.publish({"hello": "REANA"}, declare=[default_queue])
    consume_queue(consumer, limit=1)
    consumer.on_message.assert_called_once_with({"hello": "REANA"}, ANY)


@pytest.mark.parametrize("fail_first_test", [False, True])
def test_in_memory_queue_connection_isolated_between_tests(
    pytester, monkeypatch, fail_first_test
):
    """Test teardown after passing and failing tests in an isolated pytest run."""
    # Own the test order and plugin set so selection, shuffling or parallel
    # execution of the outer suite cannot turn this regression into a no-op.
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    test_file = pytester.makepyfile(
        """
        from queue import Empty

        import pytest

        from reana_commons.testing.fixtures import in_memory_queue_connection


        def test_leave_message(in_memory_queue_connection):
            queue = in_memory_queue_connection.SimpleQueue("fixture-isolation")
            queue.put({"hello": "previous test"})
            assert queue.qsize() == 1
            assert in_memory_queue_connection.transport.state.exchanges
            if FAIL_FIRST_TEST:
                pytest.fail("Intentional failure to exercise fixture teardown")


        def test_next_connection_is_clean(in_memory_queue_connection):
            transport = in_memory_queue_connection.transport
            assert not transport.Channel.queues
            assert not transport.state.exchanges
            assert not transport.state.bindings
            queue = in_memory_queue_connection.SimpleQueue("fixture-isolation")
            with pytest.raises(Empty):
                queue.get(block=False)
        """.replace(
            "FAIL_FIRST_TEST", repr(fail_first_test)
        )
    )
    result = pytester.runpytest_subprocess(
        "-q",
        f"{test_file}::test_leave_message",
        f"{test_file}::test_next_connection_is_clean",
        timeout=30,
    )
    result.assert_outcomes(passed=2 - int(fail_first_test), failed=int(fail_first_test))
    if fail_first_test:
        result.stdout.fnmatch_lines(
            ["*Failed: Intentional failure to exercise fixture teardown*"]
        )


def test_server_unreachable(ConsumerBase, default_queue):
    """Test consumer never starts because server is unreachable."""
    unreachable_connection = Connection("amqp://unreachable:5672")
    consumer = ConsumerBase(queue=default_queue, connection=unreachable_connection)
    with pytest.raises(OperationalError):
        # Typically we will leave by default the connection max retires since
        # the BaseConsumer takes care of recovering connection through
        # ``kombu.mixins.ConsumerMixin`` but for the sake of the test we set
        # it to 1.
        consumer.connect_max_retries = 1
        consumer.run()


def test_workflow_status_publish(
    ConsumerBaseOnMessageMock, in_memory_queue_connection, default_queue, consume_queue
):
    """Test WorkflowStatusPublisher."""
    consumer = ConsumerBaseOnMessageMock(
        connection=in_memory_queue_connection, queue=default_queue
    )
    workflow_status_publisher = WorkflowStatusPublisher(
        connection=in_memory_queue_connection,
        routing_key=default_queue.routing_key,
        exchange=default_queue.exchange.name,
        queue=default_queue.name,
    )
    workflow_id = "test"
    status = 1
    message = {
        "progress": {
            "total": {"total": 1, "job_ids": []},
        }
    }
    workflow_status_publisher.publish_workflow_status(
        workflow_id, status, message=message
    )
    workflow_status_publisher.close()
    expected = json.dumps(
        {"workflow_uuid": workflow_id, "logs": "", "status": status, "message": message}
    )
    consume_queue(consumer, limit=1)
    consumer.on_message.assert_called_once_with(expected, ANY)
