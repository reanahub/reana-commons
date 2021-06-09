# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Kubernetes API Client."""

from functools import partial

from kubernetes import client
from kubernetes import config as k8s_config
from werkzeug.local import LocalProxy


# FIXME: monkeypatch to avoid `Invalid value for `names`, must not be `None``
# error when calling `current_k8s_corev1_api_client.list_node()`.
# After new Kubernetes release this should not be needed.
# https://github.com/reanahub/reana-commons/issues/197
# https://github.com/kubernetes-client/python/issues/895
# https://github.com/kubernetes/kubernetes/pull/102159
from kubernetes.client.models.v1_container_image import V1ContainerImage


def names(self, names):
    """Monkeypatch."""
    self._names = names


V1ContainerImage.names = V1ContainerImage.names.setter(names)


def create_api_client(api="BatchV1"):
    """Create Kubernetes API client using config.

    :param api: String which represents which Kubernetes API to spawn. By
        default BatchV1.
    :returns: Kubernetes python client object for a specific API i.e. BatchV1.
    """
    k8s_config.load_incluster_config()
    api_configuration = client.Configuration()
    api_configuration.verify_ssl = False
    if api == "extensions/v1beta1":
        api_client = client.ExtensionsV1beta1Api()
    elif api == "CoreV1":
        api_client = client.CoreV1Api()
    elif api == "StorageV1":
        api_client = client.StorageV1Api()
    elif api == "AppsV1":
        api_client = client.AppsV1Api()
    elif api == "networking.k8s.io/v1beta1":
        api_client = client.NetworkingV1beta1Api()
    elif api == "CustomObjectsApi":
        api_client = client.CustomObjectsApi()
    else:
        api_client = client.BatchV1Api()
    return api_client


current_k8s_batchv1_api_client = LocalProxy(create_api_client)
current_k8s_corev1_api_client = LocalProxy(partial(create_api_client, api="CoreV1"))
current_k8s_networking_v1beta1 = LocalProxy(
    partial(create_api_client, api="networking.k8s.io/v1beta1")
)
current_k8s_storagev1_api_client = LocalProxy(
    partial(create_api_client, api="StorageV1")
)
current_k8s_appsv1_api_client = LocalProxy(partial(create_api_client, api="AppsV1"))
current_k8s_custom_objects_api_client = LocalProxy(
    partial(create_api_client, api="CustomObjectsApi")
)
