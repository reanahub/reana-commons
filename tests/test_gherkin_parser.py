# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
from unittest.mock import patch
import pytest
import os
from reana_commons.gherkin_parser.parser import (
    parse_feature_file,
    get_steps_list,
    map_steps_to_functions,
    run_tests,
    parse_and_run_tests,
    AnalysisTestStatus,
)
from reana_commons.gherkin_parser.errors import StepDefinitionNotFound

current_dir = os.path.dirname(os.path.abspath(__file__))


def test_parse_feature_file_okay():
    """Test for the parse_feature_file method."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "test-gherkin-syntax.feature"
    )

    feature_name, feature = parse_feature_file(feature_file_path)
    assert feature_name == "Test Feature"
    assert len(feature) == 2
    assert feature[0]["name"] == "scenario 1"
    assert len(feature[0]["steps"]) == 4
    assert feature[1]["name"] == "scenario 2"
    assert len(feature[1]["steps"]) == 2


def test_parse_feature_file_non_existing():
    """Test parsing a feature file that does not exist."""
    with pytest.raises(FileNotFoundError):
        parse_feature_file("non-existing-feature.feature")


def test_get_steps_list():
    """Test for the get_steps_list method."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "test-gherkin-syntax.feature"
    )
    _, feature = parse_feature_file(feature_file_path)
    steps = get_steps_list(feature)
    assert len(steps) == 6
    assert steps[0] == ("Context", "this is a context clause")
    assert steps[1] == ("Action", "this is an action clause")
    assert steps[2] == ("Outcome", "this is an outcome clause")
    assert steps[3] == ("Outcome", "this is another outcome clause")
    assert steps[4] == ("Action", "the workflow is finished")
    assert steps[5] == ("Outcome", "this should be tested")


@patch("reana_commons.gherkin_parser.data_fetcher.DataFetcherBase")
def test_map_steps_to_functions(mock_data_fetcher):
    """Test for the map_steps_to_functions method."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "log-content.feature"
    )
    _, feature = parse_feature_file(feature_file_path)
    steps = get_steps_list(feature)
    step_mapping = map_steps_to_functions(steps, mock_data_fetcher)
    assert len(step_mapping["Context"]) == 0
    assert len(step_mapping["Action"]) == 1
    assert step_mapping["Action"].keys() == {"the workflow is finished"}
    assert len(step_mapping["Outcome"]) == 4


def test_run_tests(mock_data_fetcher):
    """Test for the run_tests method."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "workflow-duration.feature"
    )
    feature_name, feature = parse_feature_file(feature_file_path)
    steps = get_steps_list(feature)
    step_mapping = map_steps_to_functions(steps, mock_data_fetcher)
    test_results = run_tests(
        workflow="test_wf",
        feature_name=feature_name,
        feature_file=feature,
        step_mapping=step_mapping,
    )
    # Assert that each of the test results has a status of "passed"
    for test_result in test_results:
        assert test_result.result == AnalysisTestStatus.passed


def test_run_tests_no_feature_file():
    """Test for the parse_and_run_tests method when the feature file doesn't exist."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "non-existing.feature"
    )
    with pytest.raises(FileNotFoundError):
        _, test_results = parse_and_run_tests(
            feature_file_path=feature_file_path,
            workflow="test_wf",
            data_fetcher=None,
        )


def test_step_definition_not_found():
    """Test what happens when a step definition is not found."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "test-gherkin-syntax.feature"
    )
    _, feature = parse_feature_file(feature_file_path)
    steps = get_steps_list(feature)
    # Assert that the step mapping throws a StepDefinitionNotFound exception, since
    # the steps are not defined
    with pytest.raises(StepDefinitionNotFound):
        map_steps_to_functions(steps, None)


def test_test_result_fail(mock_data_fetcher):
    """Test that a failing test is detected."""
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "failing-test.feature"
    )

    _, test_results = parse_and_run_tests(
        feature_file_path,
        "test-workflow",
        mock_data_fetcher,
    )
    assert test_results[0].result == AnalysisTestStatus.passed
    assert test_results[1].result == AnalysisTestStatus.failed
    assert test_results[2].result == AnalysisTestStatus.passed


@pytest.mark.parametrize(
    "workflow_status_response,expected_tests_result,expected_error_log",
    [
        (
            {"status": "finished"},
            AnalysisTestStatus.failed,
            'The workflow "test-workflow" is not "failed". Its status is "finished".',
        ),
        ({"status": "failed"}, AnalysisTestStatus.passed, None),
    ],
)
def test_test_expected_workflow_fail_not_skipped(
    workflow_status_response,
    expected_tests_result,
    expected_error_log,
    mock_data_fetcher,
):
    """Test what happens with expected failures.

    When the workflow status is "finished", the test should fail.
    When the workflow status is "failed", the test should pass.
    """
    feature_file_path = os.path.join(
        current_dir, "gherkin_test_files", "features", "expected-failure.feature"
    )
    mock_data_fetcher.get_workflow_status.return_value = workflow_status_response
    _, test_results = parse_and_run_tests(
        feature_file_path,
        "test-workflow",
        mock_data_fetcher,
    )
    for scenario in test_results:
        assert scenario.result == expected_tests_result
        assert scenario.error_log == expected_error_log
