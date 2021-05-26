# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA Yadage Workflow utils."""

import os
import json
import yadageschemas
from jsonschema import ValidationError

from reana_commons.config import SHARED_VOLUME_PATH


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


def yadage_load_from_workspace(workspace_path, workflow_file, toplevel, **kwargs):
    """Load yadage workflow specification from workspace path."""
    workflow_workspace = "{0}/{1}".format(SHARED_VOLUME_PATH, workspace_path)
    workflow_file_abs_path = os.path.join(workflow_workspace, workflow_file)
    if not os.path.exists(workflow_file_abs_path):
        message = f"Workflow file {workflow_file} does not exist"
        raise Exception(message)

    if not toplevel.startswith("github:"):
        toplevel = os.path.join(workflow_workspace, toplevel)

    return yadage_load(workflow_file, toplevel=toplevel, **kwargs)
