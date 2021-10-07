# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons workspaces util."""

import os
from typing import List

from reana_commons.config import WORKSPACE_PATHS
from reana_commons.errors import REANAValidationError


def validate_workspace(
    workspace_option: str, available_paths: List[str] = list(WORKSPACE_PATHS.values())
) -> str:
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
                f'Desired workspace "{workspace_option}" not valid.\n'
                "Please run `reana-client info` to see the list of allowed prefix values."
            )
    return workspace_option
