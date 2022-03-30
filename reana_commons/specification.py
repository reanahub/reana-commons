# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022 CERN.
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


def load_reana_spec(filepath, workspace_path=None):
    """Load reana specification file.

    :raises IOError: Error while reading REANA spec file from given `filepath`.
    """

    def _prepare_kwargs(reana_yaml):
        kwargs = {}
        workflow_type = reana_yaml["workflow"]["type"]
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

    try:
        with open(filepath) as f:
            reana_yaml = yaml.load(f.read(), Loader=yaml.FullLoader)
        workflow_type = reana_yaml["workflow"]["type"]
        workflow_file = reana_yaml["workflow"].get("file")
        reana_yaml["workflow"]["specification"] = load_workflow_spec(
            workflow_type,
            workflow_file,
            **_prepare_kwargs(reana_yaml),
        )

        if (
            workflow_type == "cwl" or workflow_type == "snakemake"
        ) and "inputs" in reana_yaml:
            input_file = reana_yaml["inputs"]["parameters"]["input"]
            if workspace_path and input_file:
                input_file = os.path.join(workspace_path, input_file)
            with open(input_file) as f:
                reana_yaml["inputs"]["parameters"] = yaml.load(
                    f, Loader=yaml.FullLoader
                )
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
