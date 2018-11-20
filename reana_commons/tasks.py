# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA common Celery tasks."""

import logging

from celery import shared_task
from celery.task.control import revoke

from reana_commons.api_client import JobControllerAPIClient

log = logging.getLogger(__name__)


@shared_task(name='tasks.stop_workflow',
             ignore_result=True)
def stop_workflow(workflow_uuid, job_list):
    """Stop a workflow.

    :param workflow_uuid: UUID of the workflow to be stopped.
    :param job_list: List of job identifiers which where created by the given
        workflow.
    """
    rjc_api_client = JobControllerAPIClient('reana-job-controller')
    try:
        log.info('Stopping workflow {} Celery task ...'.format(workflow_uuid))
        revoke(workflow_uuid, terminate=True)
        for job_id in job_list:
            log.info('Stopping job {} from workflow {} ...'.format(
                job_id, workflow_uuid))
            response, http_response = rjc_api_client._client.jobs.delete_job(
                job_id=job_id).result()
            log.info(response)
            log.info(http_response)
    except Exception as e:
        log.error('Something went wrong while stopping workflow {} ...'.format(
            workflow_uuid
        ))
        log.error(e)
