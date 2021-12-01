# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration for REANA-Commons."""

import pytest


@pytest.fixture()
def dummy_snakefile():
    """Get dummy Snakemake specification file, ie. Snakefile content."""
    return """
rule all:
    input:
        "results/foo.txt",
        "results/bar.txt",
        "results/baz.txt"

rule foo:
    output:
        "results/foo.txt"
    container:
        "docker://python:3.10.0-buster"
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
        "docker://python:3.10.0-buster"
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
        "docker://python:3.10.0-buster"
    resources:
        kubernetes_memory_limit="256Mi"
    shell:
        "mkdir -p results && touch {output}"
"""
