# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2020, 2021, 2023, 2024, 2025, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons utilities testing."""

import sys

import pytest

from reana_commons.utils import (
    click_table_printer,
    format_cmd,
    get_workflow_status_change_verb,
    get_trimmed_workflow_id,
)


def test_click_table_printer(capsys):
    """Test click_table_printer."""
    headers = ["header_one"]
    sample_data = [["very_very_long_row_one"], ["very_very_long_row_two"]]
    click_table_printer(headers, [], sample_data)
    out, err = capsys.readouterr()
    assert (
        out
        == "HEADER_ONE            \nvery_very_long_row_one"
        + "\nvery_very_long_row_two\n"
    )


def test_click_table_printer_filter(capsys):
    """Test click_table_printer with filter."""
    headers = ["header_one", "header_two"]
    sample_data = [
        ["very_very_long_row_one", "second_column"],
        ["very_very_long_row_two", "second_column"],
    ]
    click_table_printer(headers, [headers[1]], sample_data)
    out, err = capsys.readouterr()
    assert out == "HEADER_TWO   \nsecond_column\nsecond_column\n"


def test_click_table_printer_filter_wrong_header(capsys):
    """Test click_table_printer with filter when header is non existing."""
    headers = ["header_one", "header_two"]
    sample_data = [
        ["very_very_long_row_one", "second_column"],
        ["very_very_long_row_two", "second_column"],
    ]
    click_table_printer(headers, ["badheader"], sample_data)
    out, err = capsys.readouterr()
    assert out == "\n\n\n"


def test_format_cmd():
    """Test format_cmd."""
    test_cmd = "ls -l"
    test_cmd_fail = 12
    assert isinstance(format_cmd(test_cmd), list)
    with pytest.raises(ValueError):
        format_cmd(test_cmd_fail)


@pytest.mark.parametrize(
    "status,verb",
    [
        ("created", "has been"),
        ("running", "is"),
        ("finished", "has"),
        ("failed", "has"),
        ("deleted", "has been"),
        ("stopped", "has been"),
        ("queued", "has been"),
        ("pending", "is"),
    ],
)
def test_get_workflow_status_change_verb(status, verb):
    """Test get_workflow_status_change_verb."""
    assert get_workflow_status_change_verb(status) == verb


def test_get_workflow_status_change_verb_invalid():
    """Test get_workflow_status_change_verb with an invalid status."""
    with pytest.raises(ValueError, match="invalid"):
        get_workflow_status_change_verb("invalid")


@pytest.mark.parametrize(
    "workflow_id, trim_level, expected",
    [
        ("9eef9a08-5629-420d-8e97-29d498d88e20", 4, "9eef9a08"),
        ("9eef9a08-5629-420d-8e97-29d498d88e20", 3, "9eef9a08-5629"),
        ("9eef9a08-5629-420d-8e97-29d498d88e20", 2, "9eef9a08-5629-420d"),
        ("9eef9a08-5629-420d-8e97-29d498d88e20", 1, "9eef9a08-5629-420d-8e97"),
        (
            "9eef9a08-5629-420d-8e97-29d498d88e20",
            0,
            "9eef9a08-5629-420d-8e97-29d498d88e20",
        ),
    ],
)
def test_get_trimmed_workflow_id(workflow_id, trim_level, expected):
    """Test get_trimmed_workflow_id function with several different inputs."""
    assert get_trimmed_workflow_id(workflow_id, trim_level) == expected
