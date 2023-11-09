# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019, 2020, 2021, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Kubernetes volumes."""

import os

from kubernetes.client.rest import ApiException
from reana_commons.k8s.api_client import current_k8s_corev1_api_client

from reana_commons.config import (
    REANA_CVMFS_PVC,
    REANA_CVMFS_PVC_NAME,
    REANA_RUNTIME_KUBERNETES_NAMESPACE,
    REANA_SHARED_PVC_NAME,
    REANA_STORAGE_BACKEND,
    SHARED_VOLUME_PATH,
    WORKSPACE_PATHS,
)

REANA_SHARED_VOLUME_NAME = "reana-shared-volume"


def get_reana_shared_volume():
    """Return REANA shared volume as k8s spec.

    Depending on the configured storage backend REANA will
    use just a local volume in the host VM or a persistent
    volume claim which provides access to a network file system.

    :returns: k8s shared volume spec as a dictionary.
    """
    if REANA_STORAGE_BACKEND == "network":
        volume = {
            "name": REANA_SHARED_VOLUME_NAME,
            "persistentVolumeClaim": {"claimName": REANA_SHARED_PVC_NAME},
            "readOnly": False,
        }
    else:
        volume = {
            "name": REANA_SHARED_VOLUME_NAME,
            "hostPath": {"path": SHARED_VOLUME_PATH},
        }
    return volume


def create_cvmfs_persistent_volume_claim():
    """Create CVMFS persistent volume claim."""
    try:
        current_k8s_corev1_api_client.create_namespaced_persistent_volume_claim(
            REANA_RUNTIME_KUBERNETES_NAMESPACE,
            REANA_CVMFS_PVC,
        )
    except ApiException as e:
        # If PVC already exists, ignore the exception
        if e.status != 409:
            raise e


def get_k8s_cvmfs_volumes(cvmfs_repositories):
    """Get volume mounts and volumes need to mount CVMFS in pods.

    :param cvmfs_repositories: List of CVMFS repositories to be mounted.
    """
    if not cvmfs_repositories:
        return [], []

    # Since CVMFS CSI v2 supports automounting, only one PVC is needed
    volumes = [
        {
            "name": "cvmfs",
            "persistentVolumeClaim": {"claimName": REANA_CVMFS_PVC_NAME},
            "readOnly": True,
        }
    ]
    # Mount the `cvmfs` volume once per each repository, each time at the correct subPath
    volume_mounts = [
        {
            "name": "cvmfs",
            "mountPath": f"/cvmfs/{repository}",
            "subPath": repository,
            "mountPropagation": "HostToContainer",
            "readOnly": True,
        }
        for repository in cvmfs_repositories
    ]
    return volume_mounts, volumes


def get_shared_volume(workflow_workspace):
    """Get shared CephFS/hostPath volume to a given job spec.

    :param workflow_workspace: Absolute path to the job's workflow workspace.
    :returns: Tuple consisting of the Kubernetes volumeMount and the volume.
    """
    workflow_workspace_relative_to_owner = workflow_workspace
    if os.path.isabs(workflow_workspace):
        workflow_workspace_relative_to_owner = os.path.relpath(
            workflow_workspace, SHARED_VOLUME_PATH
        )
    mount_path = os.path.join(SHARED_VOLUME_PATH, workflow_workspace_relative_to_owner)

    volume_mount = {
        "name": REANA_SHARED_VOLUME_NAME,
        "mountPath": mount_path,
        "subPath": workflow_workspace_relative_to_owner,
    }

    volume = get_reana_shared_volume()
    return volume_mount, volume


def get_workspace_volume(workflow_workspace):
    """Get shared CephFS/hostPath workspace volume to a given job spec.

    :param workflow_workspace: Absolute path to the job's workflow workspace.
    :returns: Tuple consisting of the Kubernetes volumeMount and the volume.
    """
    if SHARED_VOLUME_PATH in workflow_workspace:
        return get_shared_volume(workflow_workspace)
    volume_mount = {"name": "reana-workspace-volume", "mountPath": workflow_workspace}
    host_workspace_path = workflow_workspace
    for host_path, mounted_path in WORKSPACE_PATHS.items():
        if host_workspace_path.startswith(mounted_path):
            host_workspace_path = host_workspace_path.replace(mounted_path, host_path)
    volume = {
        "name": "reana-workspace-volume",
        "hostPath": {"path": host_workspace_path},
    }
    return volume_mount, volume
