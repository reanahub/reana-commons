# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons job utils."""

import base64


def serialise_job_command(command):
    """Serialise job command."""
    return base64.b64encode(command.encode()).decode("utf-8")


def deserialise_job_command(command):
    """Deserialise job commands received through REST API."""
    return base64.b64decode(command).decode("utf-8")
