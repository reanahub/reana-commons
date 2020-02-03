# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2019 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA Kubernetes volumes."""

import os

import json

from reana_commons.config import (REANA_CEPHFS_PVC_NAME,
                                  REANA_STORAGE_BACKEND, SHARED_VOLUME_PATH)

REANA_SHARED_VOLUME_NAME = "reana-shared-volume"


def get_k8s_cephfs_volume():
    """Return k8s CephFS volume template.

    :returns: k8s CephFS volume spec as a dictionary.
    """
    return {
        "name": REANA_SHARED_VOLUME_NAME,
        "persistentVolumeClaim": {
            "claimName": REANA_CEPHFS_PVC_NAME
        },
        "readOnly": False
    }


def get_k8s_cvmfs_volume(repository):
    """Render k8s CVMFS volume template.

    :param repository: CVMFS repository to be mounted.
    :returns: k8s CVMFS volume spec as a dictionary.
    """
    return {
        "name": "{}-cvmfs-volume".format(repository),
        "persistentVolumeClaim": {
            "claimName": "csi-cvmfs-{}-pvc".format(repository)
        },
        "readOnly": True
    }


def get_k8s_hostpath_volume(root_path):
    """Render k8s HostPath volume template.

    :param root_path: Root path in the host machine to be mounted.
    :returns: k8s HostPath spec as a dictionary.
    """
    return {
        "name": REANA_SHARED_VOLUME_NAME,
        "hostPath": {
            "path": root_path
        }
    }


def get_shared_volume(workflow_workspace):
    """Get shared CephFS/hostPath volume to a given job spec.

    :param workflow_workspace: Absolute path to the job's workflow workspace.
    :returns: Tuple consisting of the Kubernetes volumeMount and the volume.
    """
    workflow_workspace_relative_to_owner = workflow_workspace
    if os.path.isabs(workflow_workspace):
        workflow_workspace_relative_to_owner = \
            os.path.relpath(workflow_workspace, SHARED_VOLUME_PATH)
    mount_path = os.path.join(SHARED_VOLUME_PATH,
                              workflow_workspace_relative_to_owner)
    volume_mount = {
        "name": REANA_SHARED_VOLUME_NAME,
        "mountPath": mount_path,
        "subPath": workflow_workspace_relative_to_owner}

    if REANA_STORAGE_BACKEND == "cephfs":
        volume = get_k8s_cephfs_volume()
    else:
        volume = get_k8s_hostpath_volume(SHARED_VOLUME_PATH)

    return volume_mount, volume
