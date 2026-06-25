# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons Dask resources validation."""

from typing import Dict

from reana_commons.errors import (
    REANAKubernetesWrongMemoryFormat,
    REANAValidationError,
)
from reana_commons.job_utils import kubernetes_memory_to_bytes


def _memory_to_bytes(value: str) -> int:
    """Parse a Kubernetes memory string, as a validation error on bad input.

    ``kubernetes_memory_to_bytes`` raises ``REANAKubernetesWrongMemoryFormat``
    (a plain ``Exception``) on a malformed value. This wrapper re-raises it as a
    ``REANAValidationError`` so it is recorded as a structured report entry by
    :func:`reana_commons.validation.report._check` instead of escaping as an
    unhandled 500 -- this covers both the user-supplied ``single_worker_memory``
    and the operator-provided cluster ``max_*`` limits (the latter are not
    schema-validated anywhere).
    """
    try:
        return kubernetes_memory_to_bytes(value)
    except REANAKubernetesWrongMemoryFormat as e:
        raise REANAValidationError(str(e)) from e


def validate_dask_limits(reana_yaml: Dict, dask_config: Dict) -> None:
    """Validate that Dask is allowed and requested resources are within limits.

    The cluster-specific limits are passed in via ``dask_config`` so that this
    function stays free of any service configuration import and can be reused
    both by reana-server and by the sandboxed workflow validator.

    :param reana_yaml: REANA specification.
    :param dask_config: Dictionary with the cluster Dask configuration. Expected
        keys: ``enabled`` (bool), ``max_memory_limit`` (str),
        ``default_number_of_workers`` (int), ``max_number_of_workers`` (int),
        ``default_single_worker_memory`` (str),
        ``max_single_worker_memory`` (str),
        ``default_single_worker_threads`` (int),
        ``max_single_worker_threads`` (int).
    :raises REANAValidationError: If Dask is not allowed in the cluster or one of
        the requested resources exceeds the configured limit.
    """
    dask_resources = reana_yaml["workflow"].get("resources", {}).get("dask", {})

    # Validate Dask workflows are allowed in the cluster
    if not dask_config["enabled"] and dask_resources != {}:
        raise REANAValidationError("Dask workflows are not allowed in this cluster.")

    if not dask_resources:
        return

    # Validate Dask memory limit requested for a single worker
    single_worker_memory = dask_resources.get(
        "single_worker_memory", dask_config["default_single_worker_memory"]
    )
    if _memory_to_bytes(single_worker_memory) > _memory_to_bytes(
        dask_config["max_single_worker_memory"]
    ):
        raise REANAValidationError(
            f'The "single_worker_memory" provided in the dask resources exceeds the '
            f'limit ({dask_config["max_single_worker_memory"]}).'
        )

    number_of_workers = int(
        dask_resources.get(
            "number_of_workers", dask_config["default_number_of_workers"]
        )
    )
    if number_of_workers > dask_config["max_number_of_workers"]:
        raise REANAValidationError(
            f"The number of requested Dask workers ({number_of_workers}) exceeds the "
            f'maximum limit ({dask_config["max_number_of_workers"]}).'
        )

    single_worker_threads = dask_resources.get(
        "single_worker_threads", dask_config["default_single_worker_threads"]
    )
    if single_worker_threads > dask_config["max_single_worker_threads"]:
        raise REANAValidationError(
            f'The "single_worker_threads" provided in the dask resources exceeds the '
            f'limit ({dask_config["max_single_worker_threads"]}).'
        )

    requested_dask_cluster_memory = (
        _memory_to_bytes(single_worker_memory) * number_of_workers
    )
    if requested_dask_cluster_memory > _memory_to_bytes(
        dask_config["max_memory_limit"]
    ):
        raise REANAValidationError(
            f'The "memory" requested in the dask resources exceeds the limit '
            f'({dask_config["max_memory_limit"]}).\nDecrease the number of workers '
            "requested or amount of memory consumed by a single worker."
        )
