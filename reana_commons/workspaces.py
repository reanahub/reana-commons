# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons workspaces util."""

from reana_commons.errors import REANAValidationError
from reana_commons.config import WORKSPACE_PATHS
import os


def validate_workspace(
    workspace_option, available_paths=list(WORKSPACE_PATHS.values())
):
    """Validate and return workspace.

    :param workspace_option: A string of the workspace to validate.
    :type workspace_option: string
    :param available_paths: A list of the available workspaces.
    :type available_paths: list
    :returns: A string of the validated workspace.
    """
    if workspace_option:
        available = any(
            os.path.join(os.path.abspath(workspace_option), "").startswith(
                os.path.join(os.path.abspath(path), "")
            )
            for path in available_paths
        )
        if not available:
            raise REANAValidationError(
                '==> ERROR: Desired workspace "{0}" not valid.\nPlease run reana-client workspaces to see the list of allowed prefix values.'.format(
                    workspace_option
                )
            )
    return workspace_option
