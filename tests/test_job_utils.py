# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA Job Controller API client tests."""

import subprocess

import pytest

from reana_commons.job_utils import (
    deserialise_job_command,
    kubernetes_memory_to_bytes,
    serialise_job_command,
    validate_kubernetes_memory,
)

TEST_COMMAND_SIMPLE_ONELINE = dict(
    command="echo 'Hello world'", output="Hello world\n",
)

TEST_COMMAND_COMPLEX_ONELINE = dict(
    command="cat -e <(printf 'Line 1\nLine 2\n') && echo 'The end.'",
    output="""Line 1$
Line 2$
The end.
""",
)

TEST_COMMAND_SIMPLE_SCRIPT = dict(
    command="""word=Hello

echo "Saying hello many times."

for i in {1..3}; do
    echo "$word $i";
done;

echo "Shutting down..."
""",
    output="Saying hello many times.\nHello 1\nHello 2\nHello 3\nShutting down...\n",
)


@pytest.mark.parametrize(
    "command_string, expected_output",
    [
        (TEST_COMMAND_SIMPLE_ONELINE["command"], TEST_COMMAND_SIMPLE_ONELINE["output"]),
        (
            TEST_COMMAND_COMPLEX_ONELINE["command"],
            TEST_COMMAND_COMPLEX_ONELINE["output"],
        ),
        (TEST_COMMAND_SIMPLE_SCRIPT["command"], TEST_COMMAND_SIMPLE_SCRIPT["output"]),
    ],
)
def test_job_serialisation_deserialisation(command_string, expected_output):
    """Test command serialisation when sending job commands strings to RJC."""
    serialised_command = serialise_job_command(command_string)
    deserialised_command = deserialise_job_command(serialised_command)
    # Assert command transferred correctly
    assert command_string in deserialised_command
    # Assert that the command is executable
    assert expected_output == subprocess.check_output(
        ["bash", "-c", deserialised_command]
    ).decode("utf-8")


@pytest.mark.parametrize(
    "memory,output",
    [
        ("2048", True),
        ("100K", True),
        ("8Mi", True),
        ("1.5Gi", True),
        ("7Gi", True),
        ("1.9T", True),
        ("3T", True),
        ("50Pi", True),
        ("2Ei", True),
        ("1E", True),
        ("1.33E", True),
        ("2KI", False),
        ("4096KiB", False),
        ("8Kib", False),
        ("8Mb", False),
        ("2GB", False),
        ("50Tb", False),
        ("24Exabyte", False),
        ("10i", False),
    ],
)
def test_validate_kubernetes_memory_format(memory, output):
    """Test validation of K8s memory format."""
    assert validate_kubernetes_memory(memory) is output


@pytest.mark.parametrize(
    "k8s_memory,bytes_",
    [
        (100, 100),
        ("2048", 2048),
        ("100K", 100000),
        ("8Mi", 8 * 1024 ** 2),
        ("3.5Gi", 3.5 * 1024 ** 3),
        ("7Gi", 7 * 1024 ** 3),
        ("3T", 3 * 1000 ** 4),
        ("3.1416T", 3.1416 * 1000 ** 4),
        ("50Pi", 50 * 1024 ** 5),
        ("0.2Ei", 0.2 * 1024 ** 6),
        ("2Ei", 2 * 1024 ** 6),
        ("1E", 1000 ** 6),
    ],
)
def test_kubernetes_memory_to_bytes(k8s_memory, bytes_):
    """Test conversion of k8s memory format to bytes."""
    assert kubernetes_memory_to_bytes(k8s_memory) == bytes_
