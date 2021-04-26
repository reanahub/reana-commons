# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons job utils."""

import base64
import re

from reana_commons.config import KUBERNETES_MEMORY_FORMAT
from reana_commons.errors import REANAKubernetesWrongMemoryFormat


def serialise_job_command(command):
    """Serialise job command."""
    return base64.b64encode(command.encode()).decode("utf-8")


def deserialise_job_command(command):
    """Deserialise job commands received through REST API."""
    return base64.b64decode(command).decode("utf-8")


def validate_kubernetes_memory(memory):
    """Verify that provided value matches the Kubernetes memory format."""
    return re.match(KUBERNETES_MEMORY_FORMAT, memory) is not None


def kubernetes_memory_to_bytes(memory):
    """Convert Kubernetes memory format to bytes."""
    match = re.match(KUBERNETES_MEMORY_FORMAT, str(memory))
    if not match:
        raise REANAKubernetesWrongMemoryFormat(
            "Kubernetes memory value '{}' has wrong format.".format(memory)
        )
    memory_values = match.groupdict()
    if memory_values.get("value_bytes"):
        return int(memory_values.get("value_bytes"))

    unit = memory_values.get("unit")
    value = float(memory_values.get("value_unit"))
    power = "binary" if memory_values.get("binary") else "decimal"
    multiplier = {
        "E": {"decimal": 1000 ** 6, "binary": 1024 ** 6},
        "P": {"decimal": 1000 ** 5, "binary": 1024 ** 5},
        "T": {"decimal": 1000 ** 4, "binary": 1024 ** 4},
        "G": {"decimal": 1000 ** 3, "binary": 1024 ** 3},
        "M": {"decimal": 1000 ** 2, "binary": 1024 ** 2},
        "K": {"decimal": 1000, "binary": 1024},
    }

    return value * multiplier[unit][power]
