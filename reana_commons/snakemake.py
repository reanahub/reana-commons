# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021, 2022, 2023, 2024, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Snakemake Workflow utils."""

import os
import sys
from itertools import filterfalse, chain
from typing import Any, Dict, List, Optional
from pathlib import Path

if sys.version_info >= (3, 11):
    from snakemake.api import SnakemakeApi
    from snakemake.settings.enums import Quietness
    from snakemake.settings.types import (
        ResourceSettings,
        WorkflowSettings,
        ConfigSettings,
        OutputSettings,
        StorageSettings,
        DeploymentSettings,
    )
    from snakemake.common.configfile import load_configfile
    from snakemake.utils import update_config
else:
    from snakemake import snakemake
    from snakemake.dag import DAG
    from snakemake.io import load_configfile
    from snakemake.jobs import Job
    from snakemake.persistence import Persistence
    from snakemake.rules import Rule
    from snakemake.utils import update_config
    from snakemake.workflow import Workflow

from reana_commons.errors import REANAValidationError
from reana_commons.config import SNAKEMAKE_MAX_PARALLEL_JOBS


def _invalid_snakemake_message(error):
    """Build an actionable "invalid Snakemake" message including the cause.

    The underlying Snakemake error usually names the real problem -- most
    importantly a referenced ``include:``/config file that is missing, which
    matters now that the client uploads only a *scoped* bundle (the
    ``workflow.file`` sub-tree). Surfacing it tells the user to co-locate the
    file instead of leaving them with an opaque "invalid" message.
    """
    detail = " ".join(str(error).split())
    if not detail:
        return "Snakemake specification is invalid."
    return "Snakemake specification is invalid: {}".format(detail)


def _invalid_parameter_file_message(error):
    """Build an actionable "invalid parameter file" message including the cause.

    Snakemake's reader reports the real problem -- a mapping-less top level, a
    YAML syntax error, a failed YTE expansion -- and its wording is lost if the
    exception is replaced wholesale.
    """
    detail = " ".join(str(error).split())
    message = "The workflow parameter file must contain a YAML or JSON mapping."
    if detail:
        message = "{} {}".format(message, detail)
    return message


def snakemake_configuration(
    parameter_file: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve the configuration a Snakemake workflow is loaded and run with.

    REANA gives Snakemake a single ``config`` mapping and no configuration
    file: the workflow engine starts a run from the persisted
    ``inputs.parameters`` alone, as ``ConfigSettings(config=...)``. Resolving
    the external parameter file here, instead of forwarding it to the loaders
    as ``configfiles``, is what lets load time and run time see the same
    configuration.

    The file is read with Snakemake's own reader so that it keeps its runtime
    semantics -- JSON as well as YAML, and YTE templating for files that opt
    in -- and the direct overrides are merged recursively, as Snakemake itself
    merges ``--configfile`` with ``--config``, so that a partial override of a
    nested mapping does not drop the siblings it does not mention.

    Note that a Snakefile's own ``configfile:`` directive is deliberately left
    to Snakemake, so that its defaults stay internal to the workflow instead of
    being promoted into the REANA-visible parameters.

    :param parameter_file: Path to the external workflow parameter file.
    :param overrides: Direct parameter overrides, winning over the file.
    :returns: The resolved configuration mapping.
    :raises OSError: The parameter file cannot be read.
    :raises REANAValidationError: The parameter file is not a valid mapping.
    """
    config: Dict[str, Any] = dict()
    if parameter_file:
        # Reading the file here also pins down what a *missing* one raises:
        # Snakemake 7 wraps it in a ``WorkflowError`` while Snakemake 9 lets
        # ``FileNotFoundError`` through, and ``load_reana_spec`` reports a
        # missing file by catching ``IOError``.
        with open(parameter_file) as f:
            is_empty = not f.read().strip()
        # An empty parameter file means "no parameters", as it did when REANA
        # read it with ``yaml.safe_load``; both Snakemake readers reject it for
        # having no keys at the top level.
        if not is_empty:
            try:
                config = load_configfile(parameter_file)
            except OSError:
                raise
            except Exception as e:
                raise REANAValidationError(_invalid_parameter_file_message(e)) from e
    update_config(config, overrides or dict())
    return config


def snakemake_validate(
    workflow_file: str,
    configfiles: List[str],
    workdir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
):
    """Validate Snakemake workflow."""
    if sys.version_info >= (3, 11):
        snakemake_validate_v8(workflow_file, configfiles, workdir, config)
    else:
        snakemake_validate_v7(workflow_file, configfiles, workdir, config)


def snakemake_load(workflow_file: str, **kwargs: Any):
    """Load Snakemake specification."""
    if sys.version_info >= (3, 11):
        return snakemake_load_v8(workflow_file, **kwargs)
    else:
        return snakemake_load_v7(workflow_file, **kwargs)


def snakemake_validate_v7(
    workflow_file: str,
    configfiles: List[str],
    workdir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
):
    """Snakemake 7 workflow validation function, necessary for Python versions < 3.11.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string
    :param configfiles: List of config files paths.
    :type configfiles: List
    :param workdir: Path to working directory.
    :type workdir: string or None
    :param config: Direct config overrides, taking precedence over `configfiles`.
    :type config: Dict or None
    """
    # Snakemake 7 logs most workflow errors and returns ``False`` instead of
    # raising, so the cause is collected from its log records.
    log_records = []
    try:
        valid = snakemake(
            snakefile=workflow_file,
            configfiles=configfiles,
            config=config or dict(),
            workdir=workdir,
            dryrun=True,
            quiet=True,
            log_handler=[log_records.append],
        )
    except Exception as e:
        raise REANAValidationError(_invalid_snakemake_message(e)) from e
    if not valid:
        errors = [
            str(record.get("msg", ""))
            for record in log_records
            if record.get("level") == "error"
        ]
        raise REANAValidationError(_invalid_snakemake_message(" ".join(errors)))


def snakemake_validate_v8(
    workflow_file: str,
    configfiles: List[str],
    workdir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
):
    """Snakemake 8 workflow validation function for Python versions >= 3.11.

    Note that we may move to using snakemake --dry-run when the validation process will be fully moved to the server side.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string
    :param configfiles: List of config files paths.
    :type configfiles: List
    :param workdir: Path to working directory.
    :type workdir: string or None
    :param config: Direct config overrides, taking precedence over `configfiles`.
    :type config: Dict or None
    """
    # Snakemake's WorkflowApi expects Path objects (it calls e.g.
    # ``workdir.exists()``), so convert from str.
    workflow_file = Path(workflow_file)
    if workdir:
        workdir = Path(workdir)
    with SnakemakeApi(
        OutputSettings(
            quiet={Quietness.ALL},
        )
    ) as snakemake_api:
        try:
            workflow_api = snakemake_api.workflow(
                resource_settings=ResourceSettings(nodes=SNAKEMAKE_MAX_PARALLEL_JOBS),
                config_settings=ConfigSettings(
                    configfiles=configfiles, config=config or dict()
                ),
                storage_settings=StorageSettings(),
                storage_provider_settings=dict(),
                workflow_settings=WorkflowSettings(),
                deployment_settings=DeploymentSettings(),
                snakefile=workflow_file,
                workdir=workdir,
            )

            workflow_api.dag()

        except Exception as e:
            snakemake_api.print_exception(e)
            raise REANAValidationError(_invalid_snakemake_message(e)) from e


def snakemake_load_v7(workflow_file: str, **kwargs: Any):
    """Load Snakemake workflow specification into an internal representation. Used for python <3.11 and it is needed since snakemake8 dropped support for python 3.11.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string

    :returns: Dictonary containing relevant workflow metadata.
    """

    def _create_snakemake_dag(snakefile: str, **kwargs: Any) -> DAG:
        """Create ``snakemake.dag.DAG`` instance.

        The code of this function comes from the Snakemake codebase and is adapted
        to fullfil REANA purposes of getting the needed metadata.

        If `workdir` is passed as a keyword argument, then this function will change the
        CWD to `workdir`.

        :param snakefile: Path to Snakefile.
        :type snakefile: string
        :param kwargs: Snakemake args.
        :type kwargs: Any
        """
        workflow = Workflow(
            snakefile=snakefile,
            overwrite_configfiles=[],
            overwrite_config=dict(kwargs.get("config") or dict()),
        )

        workdir = kwargs.get("workdir")
        if workdir:
            workflow.workdir(workdir)

        workflow.include(snakefile=snakefile, overwrite_default_target=True)
        workflow.check()

        # code copied and adapted from `snakemake.workflow.Workflow.execute()`
        # in order to build the DAG and calculate the job dependencies.
        # https://github.com/snakemake/snakemake/blob/75a544ba528b30b43b861abc0ad464db4d6ae16f/snakemake/workflow.py#L525
        def rules(items):
            return map(
                workflow._rules.__getitem__,
                filter(workflow.is_rule, items),
            )

        if kwargs.get("keep_target_files"):

            def files(items):
                return filterfalse(workflow.is_rule, items)

        else:

            def files(items):
                def relpath(f):
                    return (
                        f
                        if os.path.isabs(f) or f.startswith("root://")
                        else os.path.relpath(f)
                    )

                return map(relpath, filterfalse(workflow.is_rule, items))

        if not kwargs.get("targets"):
            targets = (
                [workflow.default_target]
                if workflow.default_target is not None
                else list()
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

        if hasattr(workflow, "_persistence"):
            workflow._persistence = Persistence(dag=dag)
        else:
            # for backwards compatibility (Snakemake < 7 for Python 3.6)
            workflow.persistence = Persistence(dag=dag)
        dag.init()
        dag.update_checkpoint_dependencies()
        dag.check_dynamic()
        return dag

    workdir = kwargs.get("workdir")
    if workdir:
        workflow_file = os.path.join(workdir, workflow_file)

    # The external parameter file has already been resolved into ``config`` by
    # ``snakemake_configuration``, so the workflow is loaded in the same shape
    # the runtime engine runs it: a config mapping and no config file.
    snakemake_validate(
        workflow_file=workflow_file,
        configfiles=[],
        workdir=workdir,
        config=kwargs.get("config"),
    )

    # save the cwd to restore it after _create_snakemake_dag, because this function
    # changes the cwd if `workdir` is in `kwargs`
    prev_cwd = os.getcwd()
    try:
        snakemake_dag = _create_snakemake_dag(workflow_file, **kwargs)
    finally:
        os.chdir(prev_cwd)

    job_dependencies = {
        str(job): list(map(str, deps.keys()))
        for job, deps in snakemake_dag.dependencies.items()
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
                "commands": [rule.shellcmd] if rule.shellcmd else [],
                "compute_backend": rule.resources.get("compute_backend"),
                "kubernetes_memory_limit": rule.resources.get(
                    "kubernetes_memory_limit"
                ),
                "kubernetes_uid": rule.resources.get("kubernetes_uid"),
            }
            for rule in snakemake_dag.rules
            if not rule.norun
        ],
    }


def snakemake_load_v8(workflow_file: str, **kwargs: Any):
    """Load Snakemake workflow specification into an internal representation.

    :param workflow_file: A specification file compliant with
        `snakemake` workflow specification.
    :type workflow_file: string

    :returns: Dictonary containing relevant workflow metadata.
    """
    workdir = kwargs.get("workdir")
    if workdir:
        workflow_file = os.path.join(workdir, workflow_file)
        # Snakemake's WorkflowApi expects a Path workdir (it calls
        # ``workdir.exists()``), so convert from str.
        workdir = Path(workdir)

    workflow_file = Path(workflow_file)  # convert str to Path
    # See ``snakemake_load_v7``: the parameter file is already resolved into
    # ``config``, matching the runtime engine's ``ConfigSettings(config=...)``.
    config = kwargs.get("config") or dict()

    def resource_value(rule, name):
        """Return a concrete Snakemake resource value or None when unset."""
        return rule.resources.get(name).value

    with SnakemakeApi(OutputSettings(quiet={Quietness.ALL})) as snakemake_api:
        try:
            workflow_api = snakemake_api.workflow(
                resource_settings=ResourceSettings(nodes=SNAKEMAKE_MAX_PARALLEL_JOBS),
                config_settings=ConfigSettings(configfiles=[], config=config),
                storage_settings=StorageSettings(),
                storage_provider_settings=dict(),
                workflow_settings=WorkflowSettings(),
                deployment_settings=DeploymentSettings(),
                snakefile=workflow_file,
                workdir=workdir,
            )
            workflow_api.dag()
            rules = workflow_api._workflow.rules
        except Exception as e:
            raise REANAValidationError(_invalid_snakemake_message(e)) from e

    return {
        "job_dependencies": {},
        "steps": [
            {
                "name": rule.name,
                "environment": (rule.container_img or "").replace("docker://", ""),
                "inputs": dict(rule._input),
                "params": dict(rule._params),
                "outputs": dict(rule._output),
                "commands": [rule.shellcmd] if rule.shellcmd else [],
                "compute_backend": resource_value(rule, "compute_backend"),
                "kubernetes_memory_limit": resource_value(
                    rule, "kubernetes_memory_limit"
                ),
                "kubernetes_uid": resource_value(rule, "kubernetes_uid"),
            }
            for rule in rules
            if not rule.norun
        ],
    }
