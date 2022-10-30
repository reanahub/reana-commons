# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021, 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons Snakemake tests."""

import os
import pytest
import sys

from reana_commons.snakemake import snakemake_load


def test_snakemake_load(tmpdir, dummy_snakefile):
    """Test that Snakemake metadata is loaded properly."""
    if sys.version_info.major == 3 and sys.version_info.minor == 11:
        pytest.xfail(
            "Snakemake features of reana-client are not supported on Python 3.11"
        )
    workdir = tmpdir.mkdir("sub")
    # write Snakefile
    p = workdir.join("Snakefile")
    p.write(dummy_snakefile)
    # write dummy input file
    dummy_input = workdir.join("input.txt")
    dummy_input.write("Content of input.txt")
    assert len(tmpdir.listdir()) == 1
    assert len(workdir.listdir()) == 2

    os.chdir(tmpdir)
    metadata = snakemake_load(p.strpath, workdir=workdir.strpath)
    # check that the cwd is preserved
    assert os.getcwd() == tmpdir

    for step in metadata["steps"]:
        assert step["kubernetes_memory_limit"] == "256Mi"

    assert metadata["job_dependencies"] == {
        "foo": [],
        "bar": ["foo"],
        "baz": ["foo", "bar"],
        "all": ["foo", "bar", "baz"],
    }
