# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2020, 2021, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons utilities testing."""

import os
import shutil
import sys
import time
from hashlib import md5

import pytest
from pytest_reana.fixtures import sample_workflow_workspace


from reana_commons.utils import (
    calculate_file_access_time,
    calculate_hash_of_dir,
    calculate_job_input_hash,
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


def test_calculate_hash_of_dir(sample_workflow_workspace):  # noqa: F811
    """Test calculate_hash_of_dir."""
    non_existing_dir_hash = calculate_hash_of_dir("a/b/c")
    assert non_existing_dir_hash == -1

    # Get the path to the test workspace by finding the pytest_reana package location
    import pytest_reana
    import pathlib

    # Get the package path and construct test_workspace path
    package_path = pathlib.Path(pytest_reana.__file__).parent
    test_workspace_path = package_path / "test_workspace"

    sample_workflow_workspace_path = next(sample_workflow_workspace("sample"))
    shutil.rmtree(sample_workflow_workspace_path)
    shutil.copytree(test_workspace_path, sample_workflow_workspace_path)
    dir_hash = calculate_hash_of_dir(sample_workflow_workspace_path)
    assert dir_hash == "cb2669b4d7651aa717b6952fce85575f"
    include_only_path = os.path.join(
        sample_workflow_workspace_path, "code", "worldpopulation.ipynb"
    )
    hash_of_single_file = calculate_hash_of_dir(
        sample_workflow_workspace_path, [include_only_path]
    )
    assert hash_of_single_file == "18ce945e21ab4db472525abe1e0f8080"
    empty_dir_hash = calculate_hash_of_dir(sample_workflow_workspace_path, [])
    md5_hash = md5()
    assert empty_dir_hash == md5_hash.hexdigest()
    shutil.rmtree(sample_workflow_workspace_path)


def test_calculate_job_input_hash():
    """Test calculate_job_input_hash."""
    job_spec_1 = {"workflow_workspace": "test"}
    workflow_json = {}
    job_spec_2 = {}
    assert calculate_job_input_hash(
        job_spec_1, workflow_json
    ) == calculate_job_input_hash(job_spec_2, workflow_json)


def test_calculate_file_access_time(tmp_path):
    """Test calculate_file_access_time."""
    before_writing_files = time.time() - 1
    tmp_path.joinpath("a.txt").write_text("content of a")
    tmp_path.joinpath("subdir").mkdir()
    tmp_path.joinpath("subdir", "b.txt").write_text("content of b")
    tmp_path.joinpath("c.txt").symlink_to("a.txt")
    tmp_path.joinpath("another_subdir").mkdir()
    after_writing_files = time.time() + 1

    access_times = calculate_file_access_time(str(tmp_path))

    assert len(access_times) == 2
    assert str(tmp_path / "a.txt") in access_times
    assert str(tmp_path / "subdir" / "b.txt") in access_times
    for access_time in access_times.values():
        assert before_writing_files <= access_time <= after_writing_files


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
