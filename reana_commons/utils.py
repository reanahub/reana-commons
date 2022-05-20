# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019, 2020, 2021, 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons utils."""


import datetime
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from hashlib import md5
from pathlib import Path
from typing import Dict, Tuple, Optional

import click
import requests

from reana_commons.config import (
    CVMFS_REPOSITORIES,
    REANA_COMPONENT_NAMING_SCHEME,
    REANA_COMPONENT_PREFIX,
    REANA_COMPONENT_TYPES,
    REANA_CVMFS_PVC_TEMPLATE,
    REANA_CVMFS_SC_TEMPLATE,
    REANA_JOB_CONTROLLER_CONNECTION_CHECK_SLEEP,
)
from reana_commons.errors import REANAMissingWorkspaceError


def click_table_printer(headers, _filter, data, colours=None):
    """Generate space separated output for click commands."""
    _filter = [h.lower() for h in _filter] + [h.upper() for h in _filter]
    header_indexes = [i for i, item in enumerate(headers)]
    if _filter:
        header_indexes = [
            i for i, item in enumerate(headers) if item.upper() in _filter
        ]
    headers = [h for h in headers if not _filter or h in _filter]
    # Maximum header width
    header_widths = [len(h) for h in headers]

    for row in data:
        for i, idx in enumerate(header_indexes):
            # If a row contains an element which is wider update maximum width
            if header_widths[i] < len(str(row[idx])):
                header_widths[i] = len(str(row[idx]))
    # Prepare the format string with the maximum widths
    formatted_output_parts = ["{{:<{0}}}".format(hw) for hw in header_widths]
    formatted_output = "   ".join(formatted_output_parts)
    # Print the table with the headers capitalized
    click.echo(formatted_output.format(*[h.upper() for h in headers]))
    colours = colours if len(colours or []) == len(data) else None
    for i, row in enumerate(data):
        if header_indexes:
            row = [row[i] for i in header_indexes]
        click.secho(
            formatted_output.format(*row),
            fg=colours[i] if colours else None,
        )


def calculate_hash_of_dir(directory, file_list=None):
    """Calculate hash of directory."""
    md5_hash = md5()
    if not os.path.exists(directory):
        return -1

    sorted_by_dirs = sorted(list(os.walk(directory)), key=lambda x: x[2])
    try:
        for subdir, dirs, files in sorted_by_dirs:
            for _file in files:
                file_path = os.path.join(subdir, _file)
                if file_list is not None and file_path not in file_list:
                    continue
                try:
                    _file_object = open(file_path, "rb")
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
    if "workflow_workspace" in job_spec:
        del job_spec["workflow_workspace"]
    job_md5_buffer = md5()
    job_md5_buffer.update(json.dumps(job_spec).encode("utf-8"))
    job_md5_buffer.update(json.dumps(workflow_json).encode("utf-8"))
    return job_md5_buffer.hexdigest()


def calculate_file_access_time(workflow_workspace):
    """Calculate access times of files in workspace."""
    access_times = {}
    for subdir, dirs, files in os.walk(workflow_workspace):
        for file in files:
            file_path = os.path.join(subdir, file)
            # skip symlinks
            if os.path.islink(file_path):
                continue
            access_times[file_path] = os.stat(file_path).st_atime
    return access_times


def copy_openapi_specs(output_path, component):
    """Copy generated and validated openapi specs to reana-commons module."""
    if component == "reana-server":
        file = "reana_server.json"
    elif component == "reana-workflow-controller":
        file = "reana_workflow_controller.json"
    elif component == "reana-job-controller":
        file = "reana_job_controller.json"
    if os.environ.get("REANA_SRCDIR"):
        reana_srcdir = os.environ.get("REANA_SRCDIR")
    else:
        reana_srcdir = os.path.join("..")
    try:
        reana_commons_specs_path = os.path.join(
            reana_srcdir, "reana-commons", "reana_commons", "openapi_specifications"
        )
        if os.path.exists(reana_commons_specs_path):
            if os.path.isfile(output_path):
                shutil.copy(output_path, os.path.join(reana_commons_specs_path, file))
                # copy openapi specs file as well to docs
                shutil.copy(output_path, os.path.join("docs", "openapi.json"))
    except Exception as e:
        click.echo(
            "Something went wrong, could not copy openapi "
            "specifications to reana-commons \n{0}".format(e)
        )


def get_workflow_status_change_verb(status):
    """Give the correct verb conjugation depending on status tense.

    :param status: String which represents the status the workflow changed to.
    """
    verb = ""
    if status.endswith("ing"):
        verb = "is"
    elif status.endswith("ed"):
        verb = "has been"
    else:
        raise ValueError("Unrecognised status {}".format(status))

    return verb


def build_progress_message(
    total=None, running=None, finished=None, failed=None, cached=None
):
    """Build the progress message with correct formatting."""
    progress_message = {}
    if total:
        progress_message["total"] = total
    if running:
        progress_message["running"] = running
    if finished:
        progress_message["finished"] = finished
    if failed:
        progress_message["failed"] = failed
    if cached:
        progress_message["cached"] = cached
    return progress_message


def build_caching_info_message(
    job_spec, job_id, workflow_workspace, workflow_json, result_path
):
    """Build the caching info message with correct formatting."""
    caching_info_message = {
        "job_spec": job_spec,
        "job_id": job_id,
        "workflow_workspace": workflow_workspace,
        "workflow_json": workflow_json,
        "result_path": result_path,
    }
    return caching_info_message


def run_command(cmd, display=True, return_output=False, stderr_output=False):
    """Run given command on shell in the current directory.

    Exit in case of troubles.

    :param cmd: shell command to run
    :param display: should we display command to run?
    :param return_output: shall the output of the command be returned?
    :type cmd: str
    :type display: bool
    :type return_output: bool
    """
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    if display:
        click.secho("[{0}] ".format(now), bold=True, nl=False, fg="green")
        click.secho("{0}".format(cmd), bold=True)
    try:
        if return_output:
            stderr_flag_val = subprocess.STDOUT if stderr_output else None
            result = subprocess.check_output(cmd, stderr=stderr_flag_val, shell=True)
            return result.decode().rstrip("\r\n")
        else:
            subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as err:
        if display:
            click.secho("[{0}] ".format(now), bold=True, nl=False, fg="green")
            click.secho("{0}".format(err), bold=True, fg="red")
        if stderr_output:
            sys.exit(err.output.decode())
        sys.exit(err.returncode)


def remove_upper_level_references(path):
    """Remove upper than `./` references.

    Collapse separators/up-level references avoiding references to paths
    outside working directory.

    :param path: User provided path to a file or directory.
    :return: Returns the corresponding sanitized path.
    """
    return os.path.normpath("/" + path).lstrip("/")


def is_directory(directory_path, path):
    """Whether the given path matches a directory or not.

    :param directory_path: Directory to check files from.
    :param path: Optional wildcard pattern to use for the check.
    :return: Full path if it is a directory, False if not.
    """
    secure_path = remove_upper_level_references(path)
    full_path = Path(directory_path, secure_path)
    if full_path.is_dir():
        return full_path
    return False


def get_files_recursive_wildcard(directory_path, path):
    """Get file(s) fitting the wildcard from the workspace.

    :param directory_path: Directory to get files from.
    :param path: Wildcard pattern to use for the extraction.
    :return: list of paths sorted by length.
    """
    secure_path = remove_upper_level_references(path)
    # if `secure_path` is a directory, append `/*` to get all the files inside
    if is_directory(directory_path, secure_path):
        _rstrip_path = secure_path.rstrip("/")
        secure_path = "{}/*".format(_rstrip_path)
    posix_dir_prefix = Path(directory_path)
    paths = list(posix_dir_prefix.glob(secure_path))
    # sort paths by length to start with the leaves of the directory tree
    paths.sort(key=lambda path: len(str(path)), reverse=True)
    return paths, posix_dir_prefix


def get_disk_usage_info_paths(absolute_path, command, name_filter):
    """Retrieve the path for disk usage information.

    :param absolute_path: System path to reana filesystem.
    :param command: Command to get the disk usage from reana filesystem.
    :param name_filter: Name filter parameters if any.

    :return: List of disk usage info containing the file path and size.
    """
    if name_filter:
        path_list = []
        for _path in name_filter:
            paths, _ = get_files_recursive_wildcard(absolute_path, _path)
            if paths:
                path_list += paths
        if path_list:
            for path in path_list:
                command.append(path)
            disk_usage_info = subprocess.check_output(command).decode().split()
        else:
            disk_usage_info = []
    else:
        command.append(absolute_path)
        disk_usage_info = subprocess.check_output(command).decode().split()
    return disk_usage_info


def get_disk_usage(
    directory, summarize=False, search=None, to_human_readable_units=None
):
    """Retrieve directory disk usage information.

    :param directory: Disk usage directory.
    :param summarize: Displays a total size of a directory.
    :param search: Filter parameters to show only files that match certain filtering.
    :param to_human_readable_units: Callback to transform bytes to human
        readable units.

    :return: List of dicts with file name and size.
    """
    if not os.path.exists(directory):
        raise REANAMissingWorkspaceError("Directory does not exist.")
    command = ["du"]
    if summarize:
        command.append("-s")
    else:
        command.append("-a")
    if "Darwin" not in platform.system():
        command.append("--block-size=1")

    name_filter = None
    size_filter = None
    if search:
        search = json.loads(search)
        name_filter = search.get("name")
        size_filter = search.get("size")

    disk_usage_info = get_disk_usage_info_paths(directory, command, name_filter)
    if disk_usage_info:
        filesize_pairs = list(zip(disk_usage_info[::2], disk_usage_info[1::2]))
        filesizes = []
        for filesize_pair in filesize_pairs:
            size, name = filesize_pair
            size = int(size)
            # trim workspace path in every file name, and transform bytes if necessary
            file_data = {
                "name": name[len(directory) :],
                "size": {"raw": size},
            }
            if to_human_readable_units:
                file_data["size"]["human_readable"] = to_human_readable_units(size)
            if size_filter:
                if str(size) in size_filter:
                    filesizes.append(file_data)
            else:
                filesizes.append(file_data)
        return filesizes
    return disk_usage_info


def render_cvmfs_pvc(cvmfs_volume):
    """Render REANA_CVMFS_PVC_TEMPLATE."""
    name = CVMFS_REPOSITORIES[cvmfs_volume]
    rendered_template = dict(REANA_CVMFS_PVC_TEMPLATE)
    rendered_template["metadata"]["name"] = "csi-cvmfs-{}-pvc".format(name)
    rendered_template["spec"]["storageClassName"] = "csi-cvmfs-{}".format(name)
    return rendered_template


def render_cvmfs_sc(cvmfs_volume):
    """Render REANA_CVMFS_SC_TEMPLATE."""
    name = CVMFS_REPOSITORIES[cvmfs_volume]
    rendered_template = dict(REANA_CVMFS_SC_TEMPLATE)
    rendered_template["metadata"]["name"] = "csi-cvmfs-{}".format(name)
    rendered_template["parameters"]["repository"] = cvmfs_volume
    return rendered_template


def create_cvmfs_storage_class(cvmfs_volume):
    """Create CVMFS storage class."""
    from kubernetes.client.rest import ApiException
    from reana_commons.k8s.api_client import current_k8s_storagev1_api_client

    try:
        current_k8s_storagev1_api_client.create_storage_class(
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
        current_k8s_corev1_api_client.create_namespaced_persistent_volume_claim(
            "default", render_cvmfs_pvc(cvmfs_volume)
        )
    except ApiException as e:
        if e.status != 409:
            raise e


def format_cmd(cmd):
    """Return command in a valid format."""
    if isinstance(cmd, str):
        cmd = [cmd]
    elif not isinstance(cmd, list):
        raise ValueError(
            "Command should be a list or a string and not {}".format(type(cmd))
        )
    return cmd


def check_connection_to_job_controller(port=5000):
    """Check connection from workflow engine to job controller."""
    url = "http://localhost:{}/jobs".format(port)
    retry_counter = 0
    while retry_counter < 5:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(REANA_JOB_CONTROLLER_CONNECTION_CHECK_SLEEP)
        retry_counter += 1
    else:
        logging.error("Job controller is not reachable.", exc_info=True)


def build_unique_component_name(component_type, id=None):
    """Use REANA component type and id build a human readable component name.

    :param component_type: One of
        ``reana_commons.config.REANA_COMPONENT_TYPES``.
    :param id: Unique identifier, if not specified a new UUID4 is created.

    :return: String representing the component name, i.e. reana-run-job-123456.
    """
    if component_type not in REANA_COMPONENT_TYPES:
        raise ValueError(
            "{} not valid component type.\nChoose one of: {}".format(
                component_type, REANA_COMPONENT_TYPES
            )
        )

    return REANA_COMPONENT_NAMING_SCHEME.format(
        prefix=REANA_COMPONENT_PREFIX,
        component_type=component_type,
        id=id or str(uuid.uuid4()),
    )


def get_usage_percentage(usage: int, limit: int) -> str:
    """Usage percentage."""
    if limit == 0:
        return ""
    return "{:.0%}".format(usage / limit)


def get_quota_resource_usage(
    resource: Dict, human_readable_or_raw: str
) -> Tuple[str, Optional[str]]:
    """Return quota resource usage and health.

    :param resource: Dict representing quota resource obtained from get_quota_usage()
    :param human_readable_or_raw: One of ("human_readable", "raw")

    :return: Tuple containing quota resource usage string and resource health.
        i.e. ("1 MiB out of 10 MiB used (10%)", "healthy")

    """
    usage = resource.get("usage")
    limit = resource.get("limit")
    limit_str = ""
    health = None
    if limit and limit.get("raw", 0) > 0:
        health = resource.get("health")
        percentage = get_usage_percentage(usage.get("raw"), limit.get("raw"))
        limit_str = f"out of {limit.get(human_readable_or_raw)} used ({percentage})"
    else:
        limit_str = "used"
    return f"{usage[human_readable_or_raw]} {limit_str}", health
