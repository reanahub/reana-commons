# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# REANA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# REANA; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307, USA.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization or
# submit itself to any jurisdiction.
"""REANA REST API base client."""

import json
import os

import pkg_resources
from bravado.client import SwaggerClient
from bravado.exception import (HTTPBadRequest, HTTPInternalServerError,
                               HTTPNotFound)

from reana_commons.config import OPENAPI_SPECS


class BaseAPIClient(object):
    """REANA API client code."""

    def __init__(self, service, http_client=None):
        """Create an OpenAPI client."""
        server_url, spec_file = OPENAPI_SPECS[service]
        json_spec = self._get_spec(spec_file)
        self._client = SwaggerClient.from_spec(
            json_spec,
            http_client=http_client,
            config={'also_return_response': True})
        self._client.swagger_spec.api_url = server_url
        self.server_url = server_url

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
               experiment='',
               image='',
               cmd='',
               prettified_cmd='',
               workflow_workspace='',
               job_name=''):
        """Submit a job to RJC API.

        :param name: Name of the job.
        :param experiment: Experiment the job belongs to.
        :param image: Identifier of the Docker image which will run the job.
        :param cmd: String which represents the command to execute. It can be
            modified by the workflow engine i.e. prepending ``cd /some/dir/``.
        :prettified_cmd: Original command submitted by the user.
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
