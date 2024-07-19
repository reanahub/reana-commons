# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


# This script contains the step definitions for the Gherkin feature file tests.
#
# It should be not run directly. Rather, the functions defined here should be imported and
# mapped to the corresponding steps in the feature file.
#
# An example of this is done in the `parse_and_run_tests` function of the
#  `gherkin_parser/parser.py` method.

# This module is not commented using a docstring to avoid it becoming part of the Sphinx documentation page.
# noqa: D100

import hashlib
import json
import re
import zlib
import inspect
from functools import partial, update_wrapper
from typing import List, Dict
from reana_commons.gherkin_parser.errors import StepSkipped
from reana_commons.gherkin_parser.data_fetcher import DataFetcherBase
from datetime import datetime
from reana_commons.config import WORKFLOW_TIME_FORMAT as DATETIME_FORMAT


def given(step_pattern):
    """Decorate to mark a function as a given step."""

    def wrapper(func):
        func._step_keyword = "given"
        func._step_type = "Context"
        try:
            func._step_pattern.append(step_pattern)
        except Exception:
            func._step_pattern = [step_pattern]
        return func

    return wrapper


def when(step_pattern):
    """Decorate to mark a function as a given step."""

    def wrapper(func):
        func._step_keyword = "when"
        func._step_type = "Action"
        try:
            func._step_pattern.append(step_pattern)
        except Exception:
            func._step_pattern = [step_pattern]
        return func

    return wrapper


def then(step_pattern):
    """Decorate to mark a function as a given step."""

    def wrapper(func):
        func._step_keyword = "then"
        func._step_type = "Outcome"
        try:
            func._step_pattern.append(step_pattern)
        except Exception:
            func._step_pattern = [step_pattern]

        return func

    return wrapper


def _get_step_definition_lists(fetcher: DataFetcherBase):
    """Return a dictionary containing the lists of all the step definitions in this module.

    The dictionary has three keys: "Outcome", "Action", and "Context".
    Each key contains a list of functions (step definitions) for that step type.
    """
    step_definition_list = {
        "Outcome": [],
        "Action": [],
        "Context": [],
    }
    for type in step_definition_list.keys():
        step_definition_list[type] = [
            (
                update_wrapper(partial(f, data_fetcher=fetcher), f)
                if "data_fetcher" in (inspect.signature(f).parameters)
                else f
            )
            for f in globals().values()
            if callable(f) and hasattr(f, "_step_type") and (f._step_type == type)
        ]
    return step_definition_list


def _get_single_file_size(workflow, filename, data_fetcher) -> Dict:
    """Return a dictionary with the size of a single file.

    The dictionary has two keys: "raw" and "human_readable", which contain the size
    in bytes and in human-readable format, respectively.
    """
    files_info = data_fetcher.list_files(workflow, file_name=filename)
    if len(files_info) == 1:
        return files_info[0]["size"]
    else:
        raise Exception(
            f"The specified file name ({filename}) is not in the workspace!"
        )


def _get_total_workspace_size(workflow, data_fetcher) -> int:
    """Return the total workspace size, as raw number of bytes."""
    disk_usage = data_fetcher.get_workflow_disk_usage(workflow, {"summarize": True})[
        "disk_usage_info"
    ][0]
    return disk_usage["size"]["raw"]


def _human_readable_to_raw(dim: str) -> int:
    """Convert the size to the raw number of bytes, whether it's in a human-readable format or not.

    Allowed formats are:
    - raw number of bytes (e.g. 1024)
    - human-readable units B/KiB/MiB/GiB/TiB/PiB (e.g. 1 KiB, 1MiB, 1.5GiB, 1TiB, 1PiB)
    - "bytes" suffix (e.g. 1234 bytes, 156632 bytes)
    The conversion is carried out considering multiples of 1024, as per the IEC standard.

    :param dim: The string that represents the size (in human-readable format or raw)
    :return: The equivalent number of bytes
    """
    # Conversion factors
    units = {
        "": 1,
        "bytes": 1,
        "B": 1,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
        "PiB": 1024**5,
    }

    # Regex pattern to extract size and unit
    pattern = r"(\d+(\.\d+)?)\s*([A-Za-z]*)"
    match = re.match(pattern, dim)

    if match:
        size = float(match.group(1))
        unit = match.group(3)

        # Ensure the unit is supported
        if unit in units:
            return int(size * units[unit])
        else:
            raise ValueError(f'Unknown unit "{unit}"')

    raise ValueError(f'Unable to parse "{dim}"')


def _is_file_in_workspace(workflow: str, filename: str, data_fetcher) -> bool:
    """Check whether a file is in the workspace of the workflow."""
    parameters = {"summarize": False}
    disk_usage_info = data_fetcher.get_workflow_disk_usage(workflow, parameters)[
        "disk_usage_info"
    ]
    workflow_files = [file["name"] for file in disk_usage_info]
    # When checking, try to add a trailing slash, in case the user forgot it
    return filename in workflow_files or f"/{filename}" in workflow_files


def _strip_quotes(string: str) -> str:
    """Delete the leading and trailing quotes from a string, if present.

    :param string:
    :return: The string without quotes
    """
    return string.strip('"')


def _remove_prefix(string: str, prefix: str) -> str:
    """Remove the prefix from the string, if present.

    :param string: The string from which the prefix has to be removed
    :param prefix: The prefix to be removed
    """
    if string.startswith(prefix):
        return string[len(prefix) :]
    return string


def _remove_prefixes(string: str, prefixes: List[str]) -> str:
    """Remove any of the prefix in the arguments, if present.

    :param string: The string from which the prefix has to be removed
    :param prefixes: The list of prefixes to be removed
    """
    for prefix in prefixes:
        string = _remove_prefix(string, prefix)
    return string


def _job_logs_contain(workflow, content, data_fetcher):
    log_data = data_fetcher.get_workflow_logs(workflow)["logs"]
    job_logs = json.loads(log_data)["job_logs"]
    for step_info in job_logs.values():
        if content in step_info["logs"]:
            return True
    return False


def _engine_logs_contain(workflow, content, data_fetcher):
    log_data = data_fetcher.get_workflow_logs(workflow)["logs"]
    engine_log = (json.loads(log_data)["workflow_logs"] or "") + (
        json.loads(log_data)["engine_specific"] or ""
    )
    return content in engine_log


@when("the workflow execution completes")
def _check_workflow_finished(workflow, data_fetcher):
    """
    .. container:: testcase-title.

        Workflow execution completed

    | ``When the workflow execution completes``

    The tests in this scenario will run only if the workflow has completed its execution (regardless of whether
    the execution was successful or not).
    """
    response = data_fetcher.get_workflow_status(workflow)
    if response["status"] not in [
        "finished",
        "failed",
    ]:
        raise StepSkipped(
            f'The execution of the workflow "{workflow}" has not completed yet. Its status is "{response["status"]}"'
        )


@when("the workflow is {status_workflow}")
@when("the workflow status is {status_workflow}")
def _check_workflow_status(workflow, status_workflow, data_fetcher):
    """
    .. container:: testcase-title.

       Status of the workflow

    | ``When the workflow status is {status_workflow}``

    :param status_workflow: The status in which the workflow run has to be in order to run the tests from the scenario

    The tests in this scenario will run only if the workflow is in the specified status.
    """
    status_workflow = _strip_quotes(status_workflow)
    response = data_fetcher.get_workflow_status(workflow)
    if response["status"] != status_workflow:
        raise StepSkipped(
            f'The workflow "{workflow}" is not "{status_workflow}" status. Its status is "{response["status"]}".'
        )


@then("the workflow should be {status_workflow}")
@then("the workflow status should be {status_workflow}")
def _test_workflow_status(workflow, status_workflow, data_fetcher):
    """
    .. container:: testcase-title.

       Status of the workflow

    | ``Then the workflow should be {status_workflow}``
    | ``Then the workflow status should be {status_workflow}``

    :param status_workflow: The status in which the workflow run has to be

    This test will pass only if the workflow is in the specified status.
    """
    status_workflow = _strip_quotes(status_workflow)
    response = data_fetcher.get_workflow_status(workflow)
    assert (
        response["status"] == status_workflow
    ), f'The workflow "{workflow}" is not "{status_workflow}". Its status is "{response["status"]}".'


@then("the outputs should be included in the workspace")
@then("all the outputs should be included in the workspace")
def workspace_include_all_outputs(workflow, data_fetcher):
    """
    .. container:: testcase-title.

        Presence of all the outputs in the workspace

    | ``Then all the outputs should be included in the workspace``
    | ``Then the outputs should be included in the workspace``

    This test will pass only if the workspace contains all the files and directories
    specified under the "output" section of the REANA specification file.
    """
    specs = data_fetcher.get_workflow_specification(workflow)
    spec_outputs = specs.get("specification", {}).get("outputs", {})
    outputs = (
        spec_outputs.get("files", []) or [] + spec_outputs.get("directories", []) or []
    )
    for filename in outputs:
        assert (
            _is_file_in_workspace(workflow, filename, data_fetcher) is True
        ), f'The workspace does not contain "{filename}"!'


@then('the workspace should include "{filename}"')
@then('the workspace should contain "{filename}"')
@then("{filename} should be in the workspace")
def workspace_include_specific_file(workflow, filename, data_fetcher):
    """
    .. container:: testcase-title.

        Presence of a specific file in the workspace

    | ``Then the workspace should include {filename}``
    | ``Then the workspace should contain {filename}``
    | ``Then {filename} should be in the workspace``

    :param filename: The path of the file in the workspace.

    This test will pass only if the workspace contains ``{filename}``.
    """
    assert (
        _is_file_in_workspace(workflow, filename, data_fetcher) is True
    ), f'The workspace does not contain "{filename}"!'


@then("the workspace should not include {filename}")
@then("the workspace should not contain {filename}")
@then("{filename} should not be in the workspace")
def workspace_do_not_include_specific_file(workflow, filename, data_fetcher):
    """
    .. container:: testcase-title.

        Absence of a specific file in the workspace

    | ``Then the workspace should not include {filename}``
    | ``Then the workspace should not contain {filename}``
    | ``Then {filename} should not be in the workspace``

    :param filename: The path of the file in the workspace.

    This test will pass only if the workspace does not contain ``{filename}``.
    """
    assert (
        _is_file_in_workspace(workflow, filename, data_fetcher) is False
    ), f'The workspace contains "{filename}"!'


@then('the logs should contain "{content}"')
def logs_contain(workflow, content, data_fetcher):
    """
    .. container:: testcase-title.

        Content of the logs of the workflow

    | ``Then the logs should contain "{content}"``

    :param content: The content that should be inside the logs. Note that this parameter
         MUST be surrounded by quotes.

    This test will pass only if the logs (either engine or job logs) contain ``{content}``.
    """
    assert _engine_logs_contain(workflow, content, data_fetcher) or _job_logs_contain(
        workflow, content, data_fetcher
    ), f'The logs do not contain "{content}"!'


@then('the engine logs should contain "{content}"')
def logs_engine_contain(workflow, content, data_fetcher):
    """
    .. container:: testcase-title.

        Content of the engine logs of the workflow

    | ``Then the engine logs should contain "{content}"``

    :param content: The content that should be inside the engine logs. Note that this parameter
         MUST be surrounded by quotes.

    This test will pass only if the engine logs contain ``{content}``.
    """
    assert _engine_logs_contain(
        workflow, content, data_fetcher
    ), f'The engine logs do not contain "{content}"!'


@then('the job logs should contain "{content}"')
def logs_job_contain(workflow, content, data_fetcher):
    """
    .. container:: testcase-title.

        Content of the job logs of the workflow

    | ``Then the job logs should contain "{content}"``

    :param content: The content that should be inside the engine logs. Note that this parameter
         MUST be surrounded by quotes.

    This test will pass only if the job logs contain ``{content}``.
    """
    assert _job_logs_contain(
        workflow, content, data_fetcher
    ), f'The job logs do not contain "{content}"!'


@then('the job logs for the step {step_name} should contain "{content}"')
@then('the job logs for the {step_name} step should contain "{content}"')
def logs_step_contain(workflow, step_name, content, data_fetcher):
    """
    .. container:: testcase-title.

        Content of the job logs for a particular step

    | ``Then the job logs for the step "{step_name}" should contain "{content}"``
    | ``Then the job logs for the "{step_name}" step should contain "{content}"``

    :param step_name: The name of the step whose logs have to be checked.
    :param content: The content that should be inside the logs. Note that this parameter
         MUST be surrounded by quotes.

    This test will pass only if the job logs relative to the step ``{step_name}`` contain ``{content}``.
    """
    step_name = _strip_quotes(step_name)
    logs_contain(workflow, content, data_fetcher)
    try:
        _, logs_for_step = json.loads(
            data_fetcher.get_workflow_logs(workflow, steps=[step_name])["logs"]
        )["job_logs"].popitem()
    except KeyError:
        # The dictionary is empty, thus the step name is invalid
        raise Exception("The specified step name is invalid!")
    assert (
        content in logs_for_step["logs"]
    ), f'The logs for the step "{step_name}" do not contain the specified content "{content}". Logs: "{logs_for_step["logs"]}"'


@then('the file {filename} should include "{content}"')
@then('the file {filename} should contain "{content}"')
def file_content_contain(workflow, filename, content, data_fetcher):
    """
    .. container:: testcase-title.

        Content of a specific file in the workspace

    | ``Then the file {filename} should include "{content}"``
    | ``Then the file {filename} should include "{content}"``

    :param filename: The path of the file in the workspace.
    :param content: The content that should be inside the file. Note that this parameter
         MUST be surrounded by quotes.

    This test will pass only if the specified file (which has to be in the workspace)
    contains the required ``{content}``.
    """
    filename = _strip_quotes(filename)
    if not filename.startswith("/"):
        filename = f"/{filename}"  # Add leading slash if needed
    (file_content, file_name, is_archive) = data_fetcher.download_file(
        workflow, filename
    )
    if is_archive:
        raise StepSkipped("This test is not supported for archive files.")
    assert content in file_content.decode(
        "utf-8"
    ), f'The file does not contain "{content}"!'


@then("the {algorithm} checksum of the file {filename} should be {checksum}")
def file_checksum(workflow, algorithm, filename, checksum, data_fetcher):
    """
    .. container:: testcase-title.

        Checksum of a specific file in the workspace

    | ``Then the {algorithm} checksum of the file {filename} should be {checksum}``

    :param algorithm: The algorithm to use for the checksum. Algorithms supported: ``sha256``, ``sha512``, ``md5``, ``adler32``.
    :param filename: The path of the file in the workspace.
    :param checksum: The expected checksum of the file.

    This test will pass only if the specified file (which has to be in the workspace)
    has the required ``{checksum}``.
    """
    filename = _strip_quotes(filename)
    checksum = _strip_quotes(checksum)
    algorithm = _strip_quotes(algorithm)
    supported_algorithms = {"sha256", "sha512", "md5", "adler32"}
    if algorithm.lower() not in supported_algorithms:
        raise Exception(
            f"The specified checksum algorithm is not supported! Supported algorithms: {supported_algorithms}"
        )
    (file_content, file_name, is_archive) = data_fetcher.download_file(
        workflow, filename
    )
    # Checksum the file content
    if algorithm.lower() == "adler32":
        h = zlib.adler32(file_content)
        computed_hash = hex(h)[2:]
        checksum = _remove_prefix(checksum.lower(), "0x")
    else:
        h = hashlib.new(algorithm.upper())
        h.update(file_content)
        computed_hash = h.hexdigest()
    assert (
        computed_hash == checksum
    ), f'The checksum of the file "{filename}" is not "{checksum}"! Actual checksum: "{computed_hash}"'


@then("the workflow run duration should be less than {n_minutes} minutes")
def duration_minimum_workflow(workflow, n_minutes, data_fetcher):
    """
    .. container:: testcase-title.

        Minimum duration of the workflow

    | ``Then the workflow run duration should be less than {n_minutes} minutes``

    :param n_minutes: The maximum duration, in minutes, of the analysis run.

    This test will pass only if the analysis run took less than ``{n_minutes}`` minutes.
    """
    n_minutes = _strip_quotes(n_minutes)
    status = data_fetcher.get_workflow_status(workflow)
    run_finished_at = datetime.strptime(
        status["progress"]["run_finished_at"], DATETIME_FORMAT
    )
    run_started_at = datetime.strptime(
        status["progress"]["run_started_at"], DATETIME_FORMAT
    )
    duration = (run_finished_at - run_started_at).total_seconds()
    assert duration / 60 < float(
        n_minutes
    ), f"The workflow took more than {n_minutes} minutes to complete! Run duration: {duration / 60} minutes"


@then("the duration of the step {step_name} should be less than {n_minutes} minutes")
def duration_minimum_step(workflow, step_name, n_minutes, data_fetcher):
    """
    .. container:: testcase-title.

        Minimum duration of each step of the workflow

    | ``Then the duration of the step {step_name} should be less than {n_minutes} minutes``

    :param step_name: The name of the step whose duration has to be checked.
    :param n_minutes: The maximum duration, in minutes, of the analysis run.

    This test will pass only if the step ``{step_name}`` of the analysis took less than
    ``{n_minutes}`` minutes.
    """
    step_name = _strip_quotes(step_name)
    n_minutes = _strip_quotes(n_minutes)
    _, logs_for_step = json.loads(
        data_fetcher.get_workflow_logs(workflow, steps=[step_name])["logs"]
    )["job_logs"].popitem()
    try:
        _, logs_for_step = json.loads(
            data_fetcher.get_workflow_logs(workflow, steps=[step_name])["logs"]
        )["job_logs"].popitem()
    except KeyError:
        # The dictionary is empty, thus the step name is invalid
        raise Exception("The specified step name is invalid!")

    duration = (
        datetime.strptime(logs_for_step["finished_at"], DATETIME_FORMAT)
        - datetime.strptime(logs_for_step["started_at"], DATETIME_FORMAT)
    ).total_seconds()
    assert duration / 60 < float(
        n_minutes
    ), f"The step took more than {n_minutes} minutes to complete! Run duration: {duration / 60} minutes"


@then("the size of the file {filename} should be exactly {dim}")
def exact_file_size(workflow, filename, dim, data_fetcher):
    """
    .. container:: testcase-title.

        Exact size of a specific file in the workspace

    | ``Then the size of the file {filename} should be {dim} bytes``

    :param filename: The path of the file in the workspace.
    :param dim: The size of the file. This parameter can be expressed either as raw number of bytes or in a human-readable format (e.g. ``1.5 GiB``).

    This test will pass only if the specified file (which has to be in the workspace)
    has the required size ``{dim}``.
    """
    dim = _human_readable_to_raw(_strip_quotes(dim))
    filename = _remove_prefixes(_strip_quotes(filename), ["./", "/"])
    file_size_dict = _get_single_file_size(workflow, filename, data_fetcher)
    assert (
        file_size_dict["raw"] == dim
    ), f'The size of the file "{filename}" is not {dim}! Actual size: {file_size_dict["raw"]} bytes ({file_size_dict["human_readable"]})'


@then("the size of the file {filename} should be between {dim1} and {dim2}")
def approximate_file_size(workflow, filename, dim1, dim2, data_fetcher):
    """
    .. container:: testcase-title.

        Approximate size of a specific file in the workspace

    | ``Then the size of the file be between {dim1} and {dim2}``
    | ``Then the size of the file be between {dim1} and {dim2} bytes``

    :param filename: The path of the file in the workspace.
    :param dim1: The lower bound of the file size. This parameter can be expressed as raw number of bytes (e.g. 14336) or as a human-readable string (e.g. 14KiB).
    :param dim2: The upper bound of the file size. This parameter can be expressed as raw number of bytes (e.g. 14336) or as a human-readable string (e.g. 14KiB).

    This test will pass only if the specified file (which has to be in the workspace)
    has a size between ``{dim1}`` and ``{dim2}``.
    """
    dim1_raw = _human_readable_to_raw(_strip_quotes(dim1))
    dim2_raw = _human_readable_to_raw(_strip_quotes(dim2))
    # Reorder the dimensions if needed
    if dim1_raw > dim2_raw:
        dim1_raw, dim2_raw = dim2_raw, dim1_raw
    filename = _remove_prefixes(_strip_quotes(filename), ["./", "/"])
    file_size_dict = _get_single_file_size(workflow, filename, data_fetcher)
    assert (
        dim1_raw <= file_size_dict["raw"] <= dim2_raw
    ), f'The size of the file "{filename}" is not between {dim1} and {dim2} bytes! Actual size: {file_size_dict["raw"]} bytes ({file_size_dict["human_readable"]}).'


@then("the workspace size should be less than {dim}")
def workspace_size_maximum(workflow, dim, data_fetcher):
    """
    .. container:: testcase-title.

        Maximum workspace size

    | ``Then the workspace size should be less than {dim}``

    :param dim: The maximum size of the workspace. This parameter may be expressed either as raw number of bytes (e.g. 14000), or as a human-readable string, in the "X YiB" format (e.g. 15 MiB)

    This test will pass only if the total size of the workspace is less than ``{dim}``.
    """
    dim_raw = _human_readable_to_raw(_strip_quotes(dim))
    workspace_dim = _get_total_workspace_size(workflow, data_fetcher)
    assert (
        workspace_dim <= dim_raw
    ), f"The workspace size is more than {dim}! Workspace size: {workspace_dim} bytes"


@then("the workspace size should be more than {dim}")
def workspace_size_minimum(workflow, dim, data_fetcher):
    """
    .. container:: testcase-title.

        Minimum workspace size

    | ``Then the workspace size should be more than {dim}``

    :param dim: The minimum size of the workspace. This parameter may be expressed either as raw number of bytes (e.g. 14000), or as a human-readable string, in the "X YiB" format (e.g. 15 MiB)

    This test will pass only if the total size of the workspace is more than ``{dim}``.
    """
    dim_raw = _human_readable_to_raw(_strip_quotes(dim))
    workspace_dim = _get_total_workspace_size(workflow, data_fetcher)
    assert (
        workspace_dim >= dim_raw
    ), f"The workspace size is less than {dim}! Workspace size: {workspace_dim} bytes"
