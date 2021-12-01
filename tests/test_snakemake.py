# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons Snakemake tests."""

from reana_commons.snakemake import snakemake_load


def test_snakemake_load(tmpdir, dummy_snakefile):
    """Test that Snakemake metadata is loaded properly."""
    p = tmpdir.mkdir("sub").join("Snakefile")
    p.write(dummy_snakefile)
    assert len(tmpdir.listdir()) == 1
    metadata = snakemake_load(p.strpath)

    for step in metadata["steps"]:
        assert step["kubernetes_memory_limit"] == "256Mi"

    assert metadata["job_dependencies"] == {
        "foo": [],
        "bar": ["foo"],
        "baz": ["foo", "bar"],
        "all": ["foo", "bar", "baz"],
    }
