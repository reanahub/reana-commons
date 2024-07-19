# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


# This file provides primitives required for gherkin_parser/functions.py, allowing for different
# implementations in both the client side (api calls) and server side (database access). This avoids
# circular dependencies between reana-commons and reana-client.
"""Base class for fetching data related to a workflow."""

from abc import ABC, abstractmethod


class DataFetcherBase(ABC):
    """Base class for fetching date related to a workflow."""

    @abstractmethod
    def list_files(self, workflow, file_name=None, page=None, size=None, search=None):
        """Return the list of files for a given workflow workspace.

        :param workflow: name or id of the workflow.
        :param file_name: file name(s) (glob) to list.
        :param page: page number of returned file list.
        :param size: page size of returned file list.
        :param search: filter search results by parameters.
        :returns: a list of dictionaries that have the ``name``, ``size`` and
                    ``last-modified`` keys.
        """
        pass

    @abstractmethod
    def get_workflow_disk_usage(self, workflow, parameters):
        """Display disk usage workflow.

        :param workflow: name or id of the workflow.
        :param parameters: a dictionary to customize the response. It has the following
            (optional) keys:

            - ``summarize``: a boolean value to indicate whether to summarize the response
            to include only the total workspace disk usage
            - ``search``: a string to filter the response by file name

        :return: a dictionary containing the ``workflow_id``, ``workflow_name``, and the ``user`` ID, with
                a ``disk_usage_info`` keys that contains a list of dictionaries, each of one corresponding
                to a file, with the ``name`` and ``size`` keys.
        """
        pass

    @abstractmethod
    def get_workflow_logs(self, workflow, steps=None, page=None, size=None):
        """Get logs from a workflow engine.

        :param workflow: name or id of the workflow.
        :param steps: list of step names to get logs for.
        :param page: page number of returned log list.
        :param size: page size of returned log list.

        :return: a dictionary with a ``logs`` key containing a JSON string that
                contains the requested logs.
        """
        pass

    @abstractmethod
    def get_workflow_status(self, workflow):
        """Get status of previously created workflow.

        :param workflow: name or id of the workflow.
        :return: a dictionary with the information about the workflow status.
                The dictionary has the following keys: ``id``, ``logs``, ``name``,
                ``progress``, ``status``, ``user``.
        """
        pass

    @abstractmethod
    def get_workflow_specification(self, workflow):
        """Get specification of previously created workflow.

        :param workflow: name or id of the workflow.
        :returns: a dictionary that cointains two top-level keys: ``parameters``, and
                ``specification`` (which contains a dictionary created from the workflow specification).
        """
        pass

    @abstractmethod
    def download_file(self, workflow, file_name):
        """Download the requested file if it exists.

        :param workflow: name or id of the workflow.
        :param file_name: file name or path to the file requested.
        :return: a tuple containing file binary content, filename and whether
            the returned file is a zip archive containing multiple files.
        """
        pass
