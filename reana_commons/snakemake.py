# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Snakemake Workflow utils."""

from snakemake import snakemake

from reana_commons.errors import REANAValidationError


def snakemake_load(workflow_file, **kwargs):
    """Validate Snakemake workflow specification.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string

    :returns: Empty dict as the workflow spec remains in the Snakefile.
    """
    valid = snakemake(
        snakefile=workflow_file,
        configfiles=[kwargs.get("input")],
        dryrun=True,
        quiet=True,
    )
    if not valid:
        raise REANAValidationError("Snakemake specification is invalid.")

    return {}
