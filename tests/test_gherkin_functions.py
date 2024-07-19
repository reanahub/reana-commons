# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import pytest
import os
from reana_commons.gherkin_parser.parser import parse_and_run_tests, AnalysisTestStatus
from reana_commons.gherkin_parser.functions import _human_readable_to_raw

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize(
    "human_readable, expected_raw",
    [
        ("12345", 12345),
        ("5656 B", 5656),
        ("89 bytes", 89),
        ("1.0KiB", 1024),
        ("3.2 GiB", 3435973836),
    ],
)
def test_human_readable_to_raw(human_readable, expected_raw):
    """Test the conversion to raw number of bytes."""
    assert _human_readable_to_raw(human_readable) == expected_raw


@pytest.mark.parametrize(
    "workflow_status_response,expected_tests_result",
    [
        ({"status": "finished"}, AnalysisTestStatus.passed),
        ({"status": "failed"}, AnalysisTestStatus.failed),
        ({"status": "running"}, AnalysisTestStatus.skipped),
    ],
)
def test_workflow_execution_completes(
    workflow_status_response, expected_tests_result, mock_data_fetcher
):
    """Test the step definitions relative to the workflow execution completion.

    The tests should be skipped if the workflow is not finished, but should be run
    otherwise.
    """
    feature_file_path = os.path.join(
        current_dir,
        "gherkin_test_files",
        "features",
        "workflow-execution-completes.feature",
    )
    mock_data_fetcher.get_workflow_status.return_value = workflow_status_response
    _, test_results = parse_and_run_tests(
        feature_file_path,
        "test-workflow",
        mock_data_fetcher,
    )
    for scenario in test_results:
        assert scenario.result == expected_tests_result


def test_log_content(mock_data_fetcher):
    """Test the step definitions relative to the log content."""

    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "log-content.feature"
    )
    _, test_results = parse_and_run_tests(
        feature_file_path, "test-workflow", mock_data_fetcher
    )
    for scenario in test_results:
        assert scenario.result in (
            AnalysisTestStatus.passed,
            AnalysisTestStatus.skipped,
        )


def test_workflow_duration(mock_data_fetcher):
    """Test the step definitions relative to the workflow duration."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "workflow-duration.feature"
    )
    _, test_results = parse_and_run_tests(
        feature_file_path,
        "test-workflow",
        mock_data_fetcher,
    )
    for scenario in test_results:
        assert scenario.result in (
            AnalysisTestStatus.passed,
            AnalysisTestStatus.skipped,
        )


def test_workspace_content(mock_data_fetcher):
    """Test the step definitions relative to the workspace content."""

    def get_mocked_workflow_disk_usage(workflow, parameters):
        if parameters.get("summarize", False):
            return {
                "disk_usage_info": [
                    {"name": "", "size": {"human_readable": "24 MiB", "raw": 25344320}},
                ]
            }
        else:
            return mock_data_fetcher.get_workflow_disk_usage.return_value

    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "workspace-content.feature"
    )

    mock_data_fetcher.get_workflow_disk_usage.side_effect = (
        get_mocked_workflow_disk_usage
    )
    _, test_results = parse_and_run_tests(
        feature_file_path, "test-workflow", mock_data_fetcher
    )

    for scenario in test_results:
        assert scenario.result in (
            AnalysisTestStatus.passed,
            AnalysisTestStatus.skipped,
        )
