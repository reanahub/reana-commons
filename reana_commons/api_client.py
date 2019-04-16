# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA REST API base client."""

import json
import os

import pkg_resources
from bravado.client import RequestsClient, SwaggerClient
from bravado.exception import (HTTPBadRequest, HTTPInternalServerError,
                               HTTPNotFound)

from reana_commons.config import OPENAPI_SPECS
from reana_commons.errors import MissingAPIClientConfiguration


class BaseAPIClient(object):
    """REANA API client code."""

    def __init__(self, service, http_client=None):
        """Create an OpenAPI client."""
        self._load_config_from_env()
        server_url, spec_file = OPENAPI_SPECS[service]
        json_spec = self._get_spec(spec_file)
        self._client = SwaggerClient.from_spec(
            json_spec,
            http_client=http_client or RequestsClient(ssl_verify=False),
            config={'also_return_response': True})
        if server_url is None:
            raise MissingAPIClientConfiguration(
                'Configuration to connect to {} is missing.'.format(service)
            )
        self._client.swagger_spec.api_url = server_url
        self.server_url = server_url

    def _load_config_from_env(self):
        """Override configuration from environment."""
        OPENAPI_SPECS['reana-server'] = (os.getenv('REANA_SERVER_URL'),
                                         'reana_server.json')

    def _get_spec(self, spec_file):
        """Get json specification from package data."""
        spec_file_path = os.path.join(
            pkg_resources.
            resource_filename(
                'reana_commons',
                'openapi_specifications'),
            spec_file)

        with open(spec_file_path) as f:
            json_spec = json.load(f)
        return json_spec


class JobControllerAPIClient(BaseAPIClient):
    """REANA-Job-Controller http client class."""

    def submit(self,
               workflow_uuid='',
               experiment='',
               image='',
               cmd='',
               prettified_cmd='',
               workflow_workspace='',
               job_name='',
               cvmfs_mounts='false'):
        """Submit a job to RJC API.

        :param name: Name of the job.
        :param experiment: Experiment the job belongs to.
        :param image: Identifier of the Docker image which will run the job.
        :param cmd: String which represents the command to execute. It can be
            modified by the workflow engine i.e. prepending ``cd /some/dir/``.
        :prettified_cmd: Original command submitted by the user.
        :workflow_workspace: Path to the workspace of the workflow.
        :cvmfs_mounts: String with CVMFS volumes to mount in job pods.
        :return: Returns a dict with the ``job_id``.
        """
        job_spec = {
            'experiment': experiment,
            'docker_img': image,
            'cmd': cmd,
            'prettified_cmd': prettified_cmd,
            'env_vars': {},
            'workflow_workspace': workflow_workspace,
            'job_name': job_name,
            'cvmfs_mounts': cvmfs_mounts,
            'workflow_uuid': workflow_uuid
        }

        response, http_response = self._client.jobs.create_job(job=job_spec).\
            result()
        if http_response.status_code == 400:
            raise HTTPBadRequest('Bad request to create a job. Error: {}'.
                                 format(http_response.data))
        elif http_response.status_code == 500:
            raise HTTPInternalServerError('Internal Server Error. Error: {}'.
                                          format(http_response.data))
        return response

    def check_status(self, job_id):
        """Check status of a job."""
        response, http_response = self._client.jobs.get_job(job_id=job_id).\
            result()
        if http_response.status_code == 404:
            raise HTTPNotFound('The given job ID was not found. Error: {}'.
                               format(http_response.data))
        return response

    def get_logs(self, job_id):
        """Get logs of a job."""
        response, http_response = self._client.jobs.get_logs(job_id=job_id).\
            result()
        if http_response.status_code == 404:
            raise HTTPNotFound('The given job ID was not found. Error: {}'.
                               format(http_response.data))
        return http_response.text

    def check_if_cached(self, job_spec, step, workflow_workspace):
        """Check if job result is in cache."""
        response, http_response = self._client.job_cache.check_if_cached(
            job_spec=json.dumps(job_spec),
            workflow_json=json.dumps(step),
            workflow_workspace=workflow_workspace).\
            result()
        if http_response.status_code == 400:
            raise HTTPBadRequest('Bad request to check cache. Error: {}'.
                                 format(http_response.data))
        elif http_response.status_code == 500:
            raise HTTPInternalServerError('Internal Server Error. Error: {}'.
                                          format(http_response.data))
        return http_response


def get_current_api_client(component):
    """Proxy which returns current API client for a given component."""
    rwc_api_client = BaseAPIClient(component)

    return rwc_api_client._client
