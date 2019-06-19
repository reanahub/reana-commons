# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons utils."""


import json
import os
import shutil
import subprocess
import time
from hashlib import md5

import click
import requests

from reana_commons.config import (CVMFS_REPOSITORIES, REANA_CVMFS_PVC_TEMPLATE,
                                  REANA_CVMFS_SC_TEMPLATE)


def click_table_printer(headers, _filter, data):
    """Generate space separated output for click commands."""
    _filter = [h.lower() for h in _filter] + [h.upper() for h in _filter]
    headers = [h for h in headers if not _filter or h in _filter]
    # Maximum header width
    header_widths = [len(h) for h in headers]

    for row in data:
        for idx in range(len(headers)):
            # If a row contains an element which is wider update maximum width
            if header_widths[idx] < len(str(row[idx])):
                header_widths[idx] = len(str(row[idx]))
    # Prepare the format string with the maximum widths
    formatted_output_parts = ['{{:<{0}}}'.format(hw)
                              for hw in header_widths]
    formatted_output = '   '.join(formatted_output_parts)
    # Print the table with the headers capitalized
    click.echo(formatted_output.format(*[h.upper() for h in headers]))
    for row in data:
        click.echo(formatted_output.format(*row))


def calculate_hash_of_dir(directory, file_list=None):
    """Calculate hash of directory."""
    md5_hash = md5()
    if not os.path.exists(directory):
        return -1

    try:
        for subdir, dirs, files in os.walk(directory):
            for _file in files:
                file_path = os.path.join(subdir, _file)
                if file_list is not None and file_path not in file_list:
                    continue
                try:
                    _file_object = open(file_path, 'rb')
                except Exception:
                    # You can't open the file for some reason
                    _file_object.close()
                    # We return -1 since we cannot ensure that the file that
                    # can not be read, will not change from one execution to
                    # another.
                    return -1
                while 1:
                    # Read file in little chunks
                    buf = _file_object.read(4096)
                    if not buf:
                        break
                    md5_hash.update(md5(buf).hexdigest().encode())
                _file_object.close()
    except Exception:
        return -1
    return md5_hash.hexdigest()


def calculate_job_input_hash(job_spec, workflow_json):
    """Calculate md5 hash of job specification and workflow json."""
    if 'workflow_workspace' in job_spec:
        del job_spec['workflow_workspace']
    job_md5_buffer = md5()
    job_md5_buffer.update(json.dumps(job_spec).encode('utf-8'))
    job_md5_buffer.update(json.dumps(workflow_json).encode('utf-8'))
    return job_md5_buffer.hexdigest()


def calculate_file_access_time(workflow_workspace):
    """Calculate access times of files in workspace."""
    access_times = {}
    for subdir, dirs, files in os.walk(workflow_workspace):
        for file in files:
            file_path = os.path.join(subdir, file)
            access_times[file_path] = os.stat(file_path).st_atime
    return access_times


def copy_openapi_specs(output_path, component):
    """Copy generated and validated openapi specs to reana-commons module."""
    if component == 'reana-server':
        file = 'reana_server.json'
    elif component == 'reana-workflow-controller':
        file = 'reana_workflow_controller.json'
    elif component == 'reana-job-controller':
        file = 'reana_job_controller.json'
    if os.environ.get('REANA_SRCDIR'):
        reana_srcdir = os.environ.get('REANA_SRCDIR')
    else:
        reana_srcdir = os.path.join('..')
    try:
        reana_commons_specs_path = os.path.join(
            reana_srcdir,
            'reana-commons',
            'reana_commons',
            'openapi_specifications')
        if os.path.exists(reana_commons_specs_path):
            if os.path.isfile(output_path):
                shutil.copy(output_path,
                            os.path.join(reana_commons_specs_path,
                                         file))
                # copy openapi specs file as well to docs
                shutil.copy(output_path,
                            os.path.join('docs', 'openapi.json'))
    except Exception as e:
        click.echo('Something went wrong, could not copy openapi '
                   'specifications to reana-commons \n{0}'.format(e))


def get_workflow_status_change_verb(status):
    """Give the correct verb conjugation depending on status tense.

    :param status: String which represents the status the workflow changed to.
    """
    verb = ''
    if status.endswith('ing'):
        verb = 'is'
    elif status.endswith('ed'):
        verb = 'has been'
    else:
        raise ValueError('Unrecognised status {}'.format(status))

    return verb


def build_progress_message(total=None,
                           running=None,
                           finished=None,
                           failed=None,
                           cached=None):
    """Build the progress message with correct formatting."""
    progress_message = {}
    if total:
        progress_message['total'] = total
    if running:
        progress_message['running'] = running
    if finished:
        progress_message['finished'] = finished
    if failed:
        progress_message['failed'] = failed
    if cached:
        progress_message['cached'] = cached
    return progress_message


def build_caching_info_message(job_spec,
                               job_id,
                               workflow_workspace,
                               workflow_json,
                               result_path):
    """Build the caching info message with correct formatting."""
    caching_info_message = {
        "job_spec": job_spec,
        "job_id": job_id,
        "workflow_workspace": workflow_workspace,
        "workflow_json": workflow_json,
        "result_path": result_path
    }
    return caching_info_message


def get_workspace_disk_usage(workspace, summarize=False):
    """Retrieve disk usage information of a workspace."""
    command = ['du', '-h']
    if summarize:
        command.append('-s')
    else:
        command.append('-a')
    command.append(workspace)
    disk_usage_info = subprocess.check_output(command).decode().split()
    # create pairs of (size, filename)
    filesize_pairs = list(zip(disk_usage_info[::2], disk_usage_info[1::2]))
    filesizes = []
    for filesize_pair in filesize_pairs:
        size, name = filesize_pair
        # trim workspace path in every file name
        filesizes.append({'name': name[len(workspace):],
                          'size': size})
    return filesizes


def render_cvmfs_pvc(cvmfs_volume):
    """Render REANA_CVMFS_PVC_TEMPLATE."""
    name = CVMFS_REPOSITORIES[cvmfs_volume]
    rendered_template = dict(REANA_CVMFS_PVC_TEMPLATE)
    rendered_template['metadata']['name'] = 'csi-cvmfs-{}-pvc'.format(name)
    rendered_template['spec']['storageClassName'] = "csi-cvmfs-{}".format(name)
    return rendered_template


def render_cvmfs_sc(cvmfs_volume):
    """Render REANA_CVMFS_SC_TEMPLATE."""
    name = CVMFS_REPOSITORIES[cvmfs_volume]
    rendered_template = dict(REANA_CVMFS_SC_TEMPLATE)
    rendered_template['metadata']['name'] = "csi-cvmfs-{}".format(name)
    rendered_template['parameters']['repository'] = cvmfs_volume
    return rendered_template


def create_cvmfs_storage_class(cvmfs_volume):
    """Create CVMFS storage class."""
    from kubernetes.client.rest import ApiException
    from reana_commons.k8s.api_client import current_k8s_storagev1_api_client

    try:
        current_k8s_storagev1_api_client.\
            create_storage_class(
                render_cvmfs_sc(cvmfs_volume)
            )
    except ApiException as e:
        if e.status != 409:
            raise e


def create_cvmfs_persistent_volume_claim(cvmfs_volume):
    """Create CVMFS persistent volume claim."""
    from kubernetes.client.rest import ApiException
    from reana_commons.k8s.api_client import current_k8s_corev1_api_client

    try:
        current_k8s_corev1_api_client.\
            create_namespaced_persistent_volume_claim(
                "default",
                render_cvmfs_pvc(cvmfs_volume)
            )
    except ApiException as e:
        if e.status != 409:
            raise e


def format_cmd(cmd):
    """Return command in a valid format."""
    if isinstance(cmd, str):
        cmd = [cmd]
    elif not isinstance(cmd, list):
        raise ValueError('Command should be a list or a string and not {}'
                         .format(type(cmd)))
    return cmd


def check_connection_to_job_controller(port=5000):
    """Check connection from workflow engine to job controller."""
    url = 'http://localhost:{}/jobs'.format(port)
    retry_counter = 0
    while retry_counter < 5:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(10)
        retry_counter += 1
    else:
        raise Exception('Job controller is not reachable.')
