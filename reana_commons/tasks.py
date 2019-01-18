# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA common Celery tasks."""

import importlib
import logging

from celery import shared_task
from kubernetes.client.rest import ApiException

from reana_commons.api_client import JobControllerAPIClient
from reana_commons.config import K8S_MAXIMUM_CONCURRENT_JOBS
from reana_commons.k8s.api_client import (current_k8s_batchv1_api_client,
                                          current_k8s_corev1_api_client)

log = logging.getLogger(__name__)


def reana_ready():
    """Check if reana can start new workflows."""
    from reana_commons.config import REANA_READY_CONDITIONS
    for module_name, condition_list in REANA_READY_CONDITIONS.items():
        for condition_name in condition_list:
            module = importlib.import_module(module_name)
            condition_func = getattr(module, condition_name)
            if not condition_func():
                return False
    return True


def check_predefined_conditions():
    """Check k8s predefined conditions for the nodes."""
    try:
        node_info = current_k8s_corev1_api_client.list_node()
        for node in node_info.items:
            # check based on the predefined conditions about the
            # node status: MemoryPressure, OutOfDisk, KubeletReady
            #              DiskPressure, PIDPressure,
            for condition in node.status.conditions:
                if not condition.status:
                    return False
    except ApiException as e:
        log.error('Something went wrong while getting node information.')
        log.error(e)
        return False
    return True


def check_running_job_count():
    """Check upper limit on running jobs."""
    try:
        job_list = current_k8s_batchv1_api_client.\
            list_job_for_all_namespaces()
        if len(job_list.items) > K8S_MAXIMUM_CONCURRENT_JOBS:
            return False
    except ApiException as e:
        log.error('Something went wrong while getting running job list.')
        log.error(e)
        return False
    return True
