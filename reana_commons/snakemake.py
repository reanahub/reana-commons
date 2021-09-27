# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Snakemake Workflow utils."""

import os
from itertools import filterfalse, chain
from typing import Any, Dict, List, NoReturn, Optional

from snakemake import snakemake
from snakemake.dag import DAG
from snakemake.io import load_configfile
from snakemake.jobs import Job
from snakemake.persistence import Persistence
from snakemake.rules import Rule
from snakemake.workflow import Workflow

from reana_commons.errors import REANAValidationError


def snakemake_validate(workflow_file: str, configfiles: List[str]) -> NoReturn:
    """Validate Snakemake workflow specification.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string
    :param configfiles: List of config files paths.
    :type configfiles: List
    """
    valid = snakemake(
        snakefile=workflow_file, configfiles=configfiles, dryrun=True, quiet=True,
    )
    if not valid:
        raise REANAValidationError("Snakemake specification is invalid.")


def snakemake_load(workflow_file: str, **kwargs: Any) -> Dict:
    """Load Snakemake workflow specification into an internal representation.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string

    :returns: Dictonary containing relevant workflow metadata.
    """

    def _create_snakemake_dag(
        snakefile: str, configfiles: Optional[List[str]] = None, **kwargs: Any
    ) -> DAG:
        """Create ``snakemake.dag.DAG`` instance.

        The code of this function comes from the Snakemake codebase and is adapted
        to fullfil REANA purposes of getting the needed metadata.

        :param snakefile: Path to Snakefile.
        :type snakefile: string
        :param configfiles: List of config files paths.
        :type configfiles: List
        :param kwargs: Snakemake args.
        :type kwargs: Any
        """
        overwrite_config = dict()
        if configfiles is None:
            configfiles = []
        for f in configfiles:
            # get values to override. Later configfiles override earlier ones.
            overwrite_config.update(load_configfile(f))
        # convert provided paths to absolute paths
        configfiles = list(map(os.path.abspath, configfiles))
        workflow = Workflow(
            snakefile=snakefile,
            overwrite_configfiles=configfiles,
            overwrite_config=overwrite_config,
        )

        workflow.include(snakefile=snakefile, overwrite_first_rule=True)
        workflow.check()

        # code copied and adapted from `snakemake.workflow.Workflow.execute()`
        # in order to build the DAG and calculate the job dependencies.
        # https://github.com/snakemake/snakemake/blob/75a544ba528b30b43b861abc0ad464db4d6ae16f/snakemake/workflow.py#L525
        def rules(items):
            return map(workflow._rules.__getitem__, filter(workflow.is_rule, items),)

        if kwargs.get("keep_target_files"):

            def files(items):
                return filterfalse(workflow.is_rule, items)

        else:

            def files(items):
                relpath = (
                    lambda f: f
                    if os.path.isabs(f) or f.startswith("root://")
                    else os.path.relpath(f)
                )
                return map(relpath, filterfalse(workflow.is_rule, items))

        if not kwargs.get("targets"):
            targets = (
                [workflow.first_rule] if workflow.first_rule is not None else list()
            )

        prioritytargets = kwargs.get("prioritytargets", [])
        forcerun = kwargs.get("forcerun", [])
        until = kwargs.get("until", [])
        omit_from = kwargs.get("omit_from", [])

        priorityrules = set(rules(prioritytargets))
        priorityfiles = set(files(prioritytargets))
        forcerules = set(rules(forcerun))
        forcefiles = set(files(forcerun))
        untilrules = set(rules(until))
        untilfiles = set(files(until))
        omitrules = set(rules(omit_from))
        omitfiles = set(files(omit_from))

        targetrules = set(
            chain(
                rules(targets),
                filterfalse(Rule.has_wildcards, priorityrules),
                filterfalse(Rule.has_wildcards, forcerules),
                filterfalse(Rule.has_wildcards, untilrules),
            )
        )
        targetfiles = set(chain(files(targets), priorityfiles, forcefiles, untilfiles))
        dag = DAG(
            workflow,
            workflow.rules,
            targetrules=targetrules,
            targetfiles=targetfiles,
            omitfiles=omitfiles,
            omitrules=omitrules,
        )

        workflow.persistence = Persistence(dag=dag)
        dag.init()
        dag.update_checkpoint_dependencies()
        dag.check_dynamic()
        return dag

    configfiles = [kwargs.get("input")]
    snakemake_validate(workflow_file=workflow_file, configfiles=configfiles)
    snakemake_dag = _create_snakemake_dag(
        workflow_file, configfiles=configfiles, **kwargs
    )

    job_dependencies = {
        str(job): list(map(str, deps.keys()))
        for job, deps in snakemake_dag.dependencies.items()
        if type(job) is Job
    }

    return {
        "job_dependencies": job_dependencies,
        "steps": [
            {
                "name": rule.name,
                "environment": (rule._container_img or "").replace("docker://", ""),
                "inputs": dict(rule._input),
                "params": dict(rule._params),
                "outputs": dict(rule._output),
                "commands": [rule.shellcmd],
                "kubernetes_memory_limit": rule.resources.get(
                    "kubernetes_memory_limit"
                ),
                "kubernetes_uid": rule.resources.get("kubernetes_uid"),
            }
            for rule in snakemake_dag.rules
            if not rule.norun
        ],
    }
