# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2021, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration for REANA-Commons."""

import pytest
from unittest.mock import create_autospec
from reana_commons.gherkin_parser.data_fetcher import DataFetcherBase


@pytest.fixture()
def dummy_snakefile():
    """Get dummy Snakemake specification file, ie. Snakefile content."""
    return """
rule all:
    input:
        "results/foo.txt",
        "results/bar.txt",
        "results/baz.txt"
    default_target: True

rule foo:
    input:
        "input.txt"
    output:
        "results/foo.txt"
    container:
        "docker://docker.io/library/python:3.10.0-buster"
    resources:
        kubernetes_memory_limit="256Mi"
    shell:
        "mkdir -p results && touch {output}"

rule bar:
    input:
        data="results/foo.txt"
    output:
        "results/bar.txt"
    container:
        "docker://docker.io/library/python:3.10.0-buster"
    resources:
        kubernetes_memory_limit="256Mi"
    shell:
        "mkdir -p results && touch {output}"

rule baz:
    input:
        "results/foo.txt",
        "results/bar.txt"
    output:
        "results/baz.txt"
    container:
        "docker://docker.io/library/python:3.10.0-buster"
    resources:
        kubernetes_memory_limit="256Mi"
    shell:
        "mkdir -p results && touch {output}"
"""


@pytest.fixture()
def mock_data_fetcher():
    """Mock data fetcher for gherkin_parser tests."""
    mock_data_fetcher = create_autospec(DataFetcherBase)
    mock_data_fetcher.get_workflow_status.return_value = {
        "logs": {
            "step-id-1": {
                "job_name": "jobname",
                "status": "finished",
                "started_at": "2018-10-29T12:51:04",
                "finished_at": "2018-10-29T12:51:37",
            }
        },
        "name": "test_workflow",
        "progress": {
            "run_started_at": "2018-10-29T12:51:04",
            "run_finished_at": "2018-10-29T12:55:01",
        },
        "created": "2018-10-29T12:51:04",
        "status": "finished",
        "user": "00000000-0000-0000-0000-000000000000",
    }
    mock_data_fetcher.get_workflow_disk_usage.return_value = {
        "disk_usage_info": [
            {
                "name": "output1.png",
                "size": {"human_readable": "12 MiB", "raw": 12580000},
            },
            {
                "name": "output/data.txt",
                "size": {"human_readable": "100 KiB", "raw": 184320},
            },
            {
                "name": "input.txt",
                "size": {"human_readable": "12 MiB", "raw": 12580000},
            },
            {"name": "", "size": {"human_readable": "24 MiB", "raw": 25344320}},
        ]
    }
    mock_data_fetcher.get_workflow_logs.return_value = {
        "logs": '{"engine_specific": "", "workflow_logs": "This is the workflow engine log output.And\\nthis\\nis a\\nmultiline string", "job_logs": {"job-id-1": {"name": "job-name-1", "logs": "Job logs of the job 1", "started_at": "2018-10-29T12:51:04", "finished_at": "2018-10-29T12:51:37"}, "job-id-2": {"name": "job-name-2", "logs": "Job logs of the job 2", "finished_at": "2018-10-29T12:55:01", "started_at": "2018-10-29T12:51:38"}}}'
    }
    mock_data_fetcher.get_workflow_specification.return_value = {
        "specification": {"outputs": {"files": ["output1.png", "output/data.txt"]}}
    }

    return mock_data_fetcher
