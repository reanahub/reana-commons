# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA Yadage Workflow utils."""

import os
import copy
import yadageschemas
from jsonschema import ValidationError


def yadage_load(workflow_file, toplevel=".", **kwargs):
    """Validate and return yadage workflow specification.

    :param workflow_file: A specification file compliant with
        `yadage` workflow specification.
    :type workflow_file: string
    :param toplevel: URL/path for the workflow file
    :type toplevel: string

    :returns: A dictionary which represents the valid `yadage` workflow.
    """
    schema_name = "yadage/workflow-schema"
    schemadir = None

    specopts = {
        "toplevel": toplevel,
        "schema_name": schema_name,
        "schemadir": schemadir,
        "load_as_ref": False,
    }

    validopts = {
        "schema_name": schema_name,
        "schemadir": schemadir,
    }

    try:
        return yadageschemas.load(
            spec=workflow_file, specopts=specopts, validopts=validopts, validate=True,
        )
    except ValidationError as e:
        e.message = str(e)
        raise e


def yadage_load_from_workspace(workspace_path, reana_specification, toplevel, **kwargs):
    """Load yadage workflow specification from workspace path.

    :returns: Updated reana specification with loaded `yadage` workflow.
    """
    workflow_file = reana_specification["workflow"].get("file")
    workflow_file_abs_path = os.path.join(workspace_path, workflow_file)
    if not os.path.exists(workflow_file_abs_path):
        message = "Workflow file {} does not exist".format(workflow_file)
        raise Exception(message)

    if not toplevel.startswith("github:"):
        toplevel = os.path.join(workspace_path, toplevel)

    workflow_spec = yadage_load(workflow_file, toplevel=toplevel, **kwargs)
    reana_spec = copy.deepcopy(reana_specification)
    reana_spec["workflow"]["specification"] = workflow_spec
    return reana_spec
