# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons workflow specification utils."""

import json
import logging
import os
import subprocess
import yaml

from reana_commons.serial import serial_load
from reana_commons.snakemake import snakemake_load
from reana_commons.yadage import yadage_load


def cwl_load(workflow_file, **kwargs):
    """Validate and return cwl workflow specification.

    :param workflow_file: A specification file compliant with
        `cwl` workflow specification.
    :returns: A dictionary which represents the valid `cwl` workflow.
    """
    basedir = kwargs.get("basedir")
    if basedir:
        workflow_file = os.path.join(basedir, workflow_file)
    result = subprocess.check_output(["cwltool", "--pack", "--quiet", workflow_file])
    value = result.decode("utf-8")
    return json.loads(value)


def load_workflow_spec(workflow_type, workflow_file, **kwargs):
    """Validate and return machine readable workflow specifications.

    :param workflow_type: A supported workflow specification type.
    :param workflow_file: A workflow file compliant with `workflow_type`
        specification.
    :returns: A dictionary which represents the valid workflow specification.
    """
    workflow_load = {
        "yadage": yadage_load,
        "cwl": cwl_load,
        "serial": serial_load,
        "snakemake": snakemake_load,
    }

    """Dictionary to extend with new workflow specification loaders."""
    load_function = workflow_load.get(workflow_type)
    if load_function:
        return load_function(workflow_file, **kwargs)
    return {}


def load_workflow_spec_from_reana_yaml(reana_yaml, workspace_path=None):
    """Load the workflow specification from the REANA specification.

    For example, for a Snakemake workflow, load and return the Snakefile
    in a dictionary-like format.

    :param reana_yaml: A dictionary which represents the REANA specification.
    :param workspace_path: A path to the workspace where the workflow is located.
    :returns: A dictionary which represents the valid workflow specification.
    """

    def _prepare_kwargs(reana_yaml):
        workflow_type = reana_yaml["workflow"]["type"]
        kwargs = {}
        if workflow_type == "serial":
            kwargs["specification"] = reana_yaml["workflow"].get("specification")
            kwargs["parameters"] = reana_yaml.get("inputs", {}).get("parameters", {})
            kwargs["original"] = True
        if "options" in reana_yaml.get("inputs", {}):
            kwargs.update(reana_yaml["inputs"]["options"])
        if workflow_type == "cwl":
            kwargs["basedir"] = workspace_path
        if workflow_type == "snakemake":
            input_file = reana_yaml.get("inputs", {}).get("parameters", {}).get("input")
            if workspace_path and input_file:
                input_file = os.path.join(workspace_path, input_file)
            kwargs["input"] = input_file
            kwargs["workdir"] = workspace_path
        if workflow_type == "yadage":
            kwargs["toplevel"] = workspace_path or "."
        return kwargs

    workflow_type = reana_yaml["workflow"]["type"]
    workflow_file = reana_yaml["workflow"].get("file")
    return load_workflow_spec(
        workflow_type, workflow_file, **_prepare_kwargs(reana_yaml)
    )


def load_input_parameters(reana_yaml, workspace_path=None):
    """Load the input parameters from the REANA specifications.

    At the moment, this is needed only for CWL and Snakemake workflows.
    The input parameters are loaded from the file specified in the
    `inputs.parameters.input` field of the REANA specification.

    :param reana_yaml: A dictionary which represents the REANA specification.
    :param workspace_path: A path to the workspace where the workflow is located.
    :returns: A dictionary which represents the input parameters.
    """
    workflow_type = reana_yaml["workflow"]["type"]
    if workflow_type in ("cwl", "snakemake"):
        input_file = reana_yaml.get("inputs", {}).get("parameters", {}).get("input")
        if input_file:
            if workspace_path:
                input_file = os.path.join(workspace_path, input_file)
            with open(input_file) as f:
                return yaml.safe_load(f)
    return None


def load_reana_spec(filepath, workspace_path=None):
    """Load reana specification file.

    :raises IOError: Error while reading REANA spec file from given `filepath`.
    """
    try:
        with open(filepath) as f:
            reana_yaml = yaml.safe_load(f)
        reana_yaml["workflow"]["specification"] = load_workflow_spec_from_reana_yaml(
            reana_yaml, workspace_path
        )
        input_params = load_input_parameters(reana_yaml, workspace_path)
        if input_params is not None:
            reana_yaml["inputs"]["parameters"] = input_params
        return reana_yaml
    except IOError as e:
        logging.info(
            "Something went wrong when reading specifications file from "
            "{filepath} : \n"
            "{error}".format(filepath=filepath, error=e.strerror)
        )
        raise e
    except Exception as e:
        raise e
