# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Snakemake Workflow utils."""

import os
from snakemake import snakemake
from snakemake.io import load_configfile
from snakemake.workflow import Workflow

from reana_commons.errors import REANAValidationError


def snakemake_load(workflow_file, **kwargs):
    """Validate Snakemake workflow specification.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string

    :returns: Empty dict as the workflow spec remains in the Snakefile.
    """

    def _create_snakemake_workflow(snakefile, configfiles=None):
        """Create ``snakemake.workflow.Workflow`` instance.

        :param snakefile: Path to Snakefile.
        :type snakefile: string
        :param configfiles: List of config files paths.
        :type configfiles: List
        """
        overwrite_config = dict()
        if configfiles is None:
            configfiles = []
        for f in configfiles:
            # get values to override. Later configfiles override earlier ones.
            overwrite_config.update(load_configfile(f))
        # convert provided paths to absolute paths
        configfiles = list(map(os.path.abspath, configfiles))
        snakemake_workflow = Workflow(
            snakefile=snakefile,
            overwrite_configfiles=configfiles,
            overwrite_config=overwrite_config,
        )

        snakemake_workflow.include(snakefile=snakefile)
        return snakemake_workflow

    configfiles = [kwargs.get("input")]
    valid = snakemake(
        snakefile=workflow_file,
        configfiles=[kwargs.get("input")],
        dryrun=True,
        quiet=True,
    )
    if not valid:
        raise REANAValidationError("Snakemake specification is invalid.")

    snakemake_workflow = _create_snakemake_workflow(
        workflow_file, configfiles=configfiles
    )

    return {
        "steps": [
            {
                "name": rule.name,
                "environment": (rule._container_img or "").replace("docker://", ""),
                "inputs": dict(rule._input),
                "params": dict(rule._params),
                "outputs": dict(rule._output),
                "commands": [rule.shellcmd],
                "kubernetes_uid": rule.resources.get("kubernetes_uid"),
            }
            for rule in snakemake_workflow.rules
            if not rule.norun
        ]
    }
