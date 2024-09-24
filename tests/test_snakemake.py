# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021, 2022, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons Snakemake tests."""

import os
import pytest
import sys
from pathlib import Path

from reana_commons.snakemake import snakemake_load


@pytest.mark.xfail(
    sys.version_info >= (3, 11),
    reason="Test expected to fail for python versions 3.11 and above as we currently return only empty dictionary in snakemake_load function for python >= 3.11.",
)
def test_snakemake_load(tmpdir, dummy_snakefile):
    """Test that Snakemake metadata is loaded properly."""
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
    metadata = snakemake_load(Path(p.strpath), workdir=Path(workdir.strpath))
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
