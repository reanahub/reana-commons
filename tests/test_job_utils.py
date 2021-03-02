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

from reana_commons.job_utils import deserialise_job_command, serialise_job_command

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
