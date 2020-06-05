# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Kubernetes volumes."""

import os

from reana_commons.config import (
    REANA_SHARED_PVC_NAME,
    REANA_STORAGE_BACKEND,
    SHARED_VOLUME_PATH,
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


def get_k8s_cvmfs_volume(repository):
    """Render k8s CVMFS volume template.

    :param repository: CVMFS repository to be mounted.
    :returns: k8s CVMFS volume spec as a dictionary.
    """
    return {
        "name": "{}-cvmfs-volume".format(repository),
        "persistentVolumeClaim": {"claimName": "csi-cvmfs-{}-pvc".format(repository)},
        "readOnly": True,
    }


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
