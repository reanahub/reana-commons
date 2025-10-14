# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2025 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons kubernetes queues validation."""

from reana_commons.errors import REANAValidationError


def validate_kubernetes_queues(
    reana_yaml: dict,
    kueue_enabled: bool,
    supported_queues: list[str],
    default_queue: str | None,
) -> None:
    """Validate Kubernetes queues in REANA specification file.

    :param reana_yaml: dictionary which represents REANA specification file.
    :param kueue_enabled: whether Kueue is enabled.
    :param supported_queues: list of supported Kubernetes queues.
    :param default_queue: default Kubernetes queue.

    :raises REANAValidationError: Given Kubernetes queue specified in REANA spec file does not validate against
        supported Kubernetes queues or an unsupported workflow type is found.
    """
    workflow = reana_yaml["workflow"]
    workflow_type = workflow["type"]
    if workflow_type == "serial" or workflow_type == "snakemake":
        workflow_steps = workflow["specification"]["steps"]
    elif workflow_type == "yadage":
        workflow_steps = workflow["specification"]["stages"]
    elif workflow_type == "cwl":
        workflow_steps = workflow.get("specification", {}).get("$graph", workflow)
    else:
        raise REANAValidationError(f"Unsupported workflow type: {workflow_type}")

    for step in workflow_steps:
        queue = step.get("kubernetes_queue")
        if queue:
            if not kueue_enabled:
                raise REANAValidationError(
                    f'Kubernetes queue "{queue}" found in step "{step.get("name")}" but Kueue is not enabled.'
                )
            if queue not in supported_queues:
                raise REANAValidationError(
                    f'Kubernetes queue "{queue}" in step "{step.get("name")}" is not in list of supported queues: {", ".join(supported_queues)}'
                )
        elif kueue_enabled and not default_queue:
            raise REANAValidationError(
                f'Kubernetes queue expected in step "{step.get("name")}" since Kueue is enabled and no default queue is set.'
            )
