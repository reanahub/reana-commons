# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons utilities testing."""

import os
from hashlib import md5
from pathlib import Path

from pytest import raises
from pytest_reana.fixtures import sample_workflow_workspace

from reana_commons.utils import (calculate_file_access_time,
                                 calculate_hash_of_dir,
                                 calculate_job_input_hash, click_table_printer,
                                 format_cmd)


def test_click_table_printer(capsys):
    """Test click_table_printer."""
    headers = ['header_one']
    sample_data = [['very_very_long_row_one'],
                   ['very_very_long_row_two']]
    click_table_printer(headers, [], sample_data)
    out, err = capsys.readouterr()
    assert out == 'HEADER_ONE            \nvery_very_long_row_one' + \
                  '\nvery_very_long_row_two\n'


def test_calculate_hash_of_dir(sample_workflow_workspace):
    """Test calculate_hash_of_dir."""
    non_existing_dir_hash = calculate_hash_of_dir('a/b/c')
    assert non_existing_dir_hash == -1
    sample_workflow_workspace_path = next(sample_workflow_workspace('sample'))
    dir_hash = calculate_hash_of_dir(sample_workflow_workspace_path)
    assert dir_hash == '8d287a3e2240b1762862d485a424363c'
    include_only_path = os.path.join(sample_workflow_workspace_path,
                                     'code', 'worldpopulation.ipynb')
    hash_of_single_file = calculate_hash_of_dir(sample_workflow_workspace_path,
                                                [include_only_path])
    assert hash_of_single_file == '18ce945e21ab4db472525abe1e0f8080'
    empty_dir_hash = calculate_hash_of_dir(sample_workflow_workspace_path,
                                           [])
    md5_hash = md5()
    assert empty_dir_hash == md5_hash.hexdigest()


def test_calculate_job_input_hash():
    """Test calculate_job_input_hash."""
    job_spec_1 = {'workflow_workspace': 'test'}
    workflow_json = {}
    job_spec_2 = {}
    assert calculate_job_input_hash(
        job_spec_1,
        workflow_json) == calculate_job_input_hash(job_spec_2,
                                                   workflow_json)


def test_calculate_file_access_time(sample_workflow_workspace):
    """Test calculate_file_access_time."""
    sample_workflow_workspace_path = next(sample_workflow_workspace('sample'))
    access_times = calculate_file_access_time(sample_workflow_workspace_path)
    all_file_paths = list(Path(sample_workflow_workspace_path).rglob("*.*"))
    for file_path in all_file_paths:
        assert str(file_path) in access_times


def test_format_cmd():
    """Test format_cmd."""
    test_cmd = "ls -l"
    test_cmd_fail = 12
    assert isinstance(format_cmd(test_cmd), list)
    with raises(ValueError):
        format_cmd(test_cmd_fail)
