# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Gherkin test runner."""

import logging
import enum
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from gherkin.parser import Parser
from gherkin.pickles.compiler import Compiler
from parse import parse
from dataclasses import dataclass
from reana_commons.gherkin_parser.errors import (
    StepDefinitionNotFound,
    StepSkipped,
    FeatureFileError,
)
from reana_commons.gherkin_parser.functions import _get_step_definition_lists
from reana_commons.gherkin_parser.data_fetcher import DataFetcherBase


class AnalysisTestStatus(enum.Enum):
    """Enumeration of possible analysis test statuses."""

    passed = 0
    failed = 1
    skipped = 2


@dataclass
class TestResult:
    """Dataclass for storing test results."""

    scenario: str
    failed_testcase: str
    result: AnalysisTestStatus
    error_log: str
    feature: str
    checked_at: datetime


def _get_step_text(step: Dict) -> str:
    """Return the text of the step, including possible multiline arguments.

    :param step: A step dictionary, as returned by `parse_feature_file`.
    :return: The text of the step, including possible multiline arguments.
    """
    if "argument" in step.keys():
        return f'{step["text"]} "{step["argument"]["docString"]["content"]}"'
    return step["text"]


def validate_feature_file(feature_file_path: str, data_fetcher: DataFetcherBase):
    """Validate the feature file.

    :param feature_file_path: The path to the feature file to be validated.
    :return A tuple containing the feature name, the parsed feature object and the dictionary mapping
    the step texts to their function definitions.
    :raise StepDefinitionNotFound: If the feature file contains a step for which no step definition is found.
    :raise FeatureFileError: If there is an error while parsing or compiling the feature file.
    :raise FileNotFoundError: If the feature file does not exist.
    :raise IOError: If there is an error while reading the feature file.
    """
    feature_name, parsed_feature = parse_feature_file(feature_file_path)
    steps_list = get_steps_list(parsed_feature)
    step_map = map_steps_to_functions(steps_list, data_fetcher)
    return feature_name, parsed_feature, step_map


def parse_feature_file(feature_file_path: str) -> Tuple[str, List[Dict]]:
    """Parse the feature file and return the list of scenarios.

    :param feature_file_path: The path to the feature file to be parsed.
    :return: A tuple containing the feature name and a list of dictionaries,
             each corresponding to one scenario of the feature file.
             Example:
             {
                "name": "Scenario name",
                "steps": List of steps, each containing at least the step type and the step text.
             }
    :raise FileNotFoundError: If the feature file does not exist.
    :raise IOError: If there is an error while reading the feature file.
    :raise FeatureFileError: If there is an error while parsing or compiling the feature file.
    """
    try:
        with open(feature_file_path) as f:
            file_content = f.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"The file '{feature_file_path}' was not found: {e.strerror}"
        )
    except IOError as e:
        raise IOError(f"Error reading the file '{feature_file_path}': {e.strerror}")

    try:
        parser = Parser()
        compiler = Compiler()
        gherkin_document = parser.parse(file_content)
        feature_name = gherkin_document["feature"]["name"]
        gherkin_document["uri"] = feature_file_path
        pickles = compiler.compile(gherkin_document)
        return feature_name, pickles
    except Exception as e:
        raise FeatureFileError(
            f"Unexpected error during parsing or compiling of the test file '{feature_file_path}' \n{e}"
        )


def get_steps_list(feature_file: List[Dict]) -> List[Tuple[str, str]]:
    """Return a list of all steps in the feature file.

    :param feature_file: The parsed feature file, as returned by `parse_feature_file`.
    :return: A list of tuples, each containing the step type and the step text.
             The step type can be one of "Context" (Given), "Action" (When), or "Outcome" (Then).
             The step text returned by this method contains also the multiline arguments, if any.
             Example:
             [
                ("Context", "I have a file"),
                ("Action", "I run the analysis"),
                ("Outcome", "the log should contain 'blah' ")
                ("Outcome", "the log should contain 'bleh' ")
             ]
    """
    steps = []
    for scenario in feature_file:
        for step in scenario["steps"]:
            steps.append((step["type"].strip(), _get_step_text(step)))
    return steps


def map_steps_to_functions(steps: list, data_fetcher: DataFetcherBase):
    """Map each step to the corresponding step definition (function).

    :param steps: A list of tuples, each containing the step type, and the step text.
    :return: A dictionary mapping each step to the corresponding step definition (function).
            Example:
            {
                "Action": {
                    "The workflow status is finished": {
                        "function": <function check_workflow_status at 0x7f7f7f7f7f7f>,
                        "arguments": {"status_workflow": "finished"}
                    }
                },
                ...,
            }
    :raise StepDefinitionNotFound: If the feature file contains a step for which no step definition is found.
    """
    step_mapping = {"Context": {}, "Action": {}, "Outcome": {}}
    for step_type, step_text in steps:
        found = False
        # Get the list of all step definitions, divided by step type.
        step_definitions = _get_step_definition_lists(data_fetcher)
        for func in step_definitions[step_type]:
            # Check if the step text matches any of the patterns.
            parse_results = [
                parse(pattern, step_text) for pattern in func._step_pattern
            ]
            result = next((r for r in parse_results if r is not None), None)
            # Check if there was at least one non-None result.
            if result is not None:
                step_mapping[step_type][step_text] = {}
                step_mapping[step_type][step_text]["function"] = func
                step_mapping[step_type][step_text]["arguments"] = result.named
                found = True
                break
        if not found:
            logging.error(f"No step definition found for step: {step_text}")
            raise StepDefinitionNotFound(
                f"No step definition found for step: {step_text}"
            )
    return step_mapping


def run_tests(
    workflow: str,
    feature_name: str,
    feature_file,
    step_mapping: Dict,
) -> List[TestResult]:
    """Run all the tests in the parsed feature file.

    :param feature_name: The name of the feature inside the feature file.
    :param workflow: The name of the workflow in REANA
    :param feature_file: The parsed and compiled feature file, as returned by `parse_feature_file`.
    :param step_mapping: A dictionary mapping each step to the corresponding step definition (function).
    :return: A list of dictionaries, each corresponding to one scenario of the feature file.
    """
    test_results = []
    for scenario in feature_file:
        logging.info(f"Running scenario: {scenario['name']}...")
        result = AnalysisTestStatus.passed
        failed_testcase = None
        error_log = None
        for step in scenario["steps"]:
            logging.debug(f"Running step: {step['text']} ({step['type']})...")
            step_type = step["type"].strip()
            step_text = _get_step_text(step)
            function = step_mapping[step_type].get(step_text).get("function")
            arguments = step_mapping[step_type].get(step_text).get("arguments")
            if function is not None:
                try:
                    function(workflow, **arguments)
                except StepSkipped:
                    logging.info(f"Scenario skipped! Current testcase: {step_text}")
                    result = AnalysisTestStatus.skipped
                    break
                except Exception as e:
                    # Catches all exceptions, including AssertionError.
                    result = AnalysisTestStatus.failed
                    failed_testcase = step_text
                    error_log = str(e)
                    logging.error(f"Scenario failed! Failed testcase: {step_text}")
                    logging.error(f"Error log: {e}")
                    break
        test_results.append(
            TestResult(
                scenario=scenario["name"],
                failed_testcase=failed_testcase,
                result=result,
                error_log=error_log,
                feature=feature_name,
                checked_at=datetime.now(timezone.utc),
            )
        )
        if result == AnalysisTestStatus.passed:
            logging.info(f"Scenario `{scenario['name']}` passed!")

    return test_results


def parse_and_run_tests(
    feature_file_path: str,
    workflow: str,
    data_fetcher: DataFetcherBase,
) -> Tuple[str, List]:
    """Parse the feature file and run all the tests in it.

    :param workflow: The name of the workflow on REANA.
    :param feature_file_path: The path to the feature file to be parsed.
    :return: A tuple in which the first element is the feature name, and the second is
         a list of dictionaries, each corresponding to the test result of one scenario of the feature file.
    :raise StepDefinitionNotFound: If the feature file contains a step for which no step definition is found.
    :raise FeatureFileError: If there is an error while parsing or compiling the feature file.
    :raise FileNotFoundError: If the feature file does not exist.
    :raise IOError: If there is an error while reading the feature file.
    """
    feature_name, parsed_feature, step_mapping = validate_feature_file(
        feature_file_path, data_fetcher
    )
    results = run_tests(
        workflow=workflow,
        feature_name=feature_name,
        feature_file=parsed_feature,
        step_mapping=step_mapping,
    )
    return feature_name, results
