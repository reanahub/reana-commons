# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


# This file provides primitives required for gherkin_parser/functions.py, allowing for different
# implementations in both the client side (api calls) and server side (database access). This avoids
# circular dependencies between reana-commons and reana-client.


from abc import ABC, abstractmethod


class DataFetcherInterface(ABC):
    """Interface for fetching date related to a workflow"""

    @abstractmethod
    def list_files(
        self, workflow, access_token, file_name=None, page=None, size=None, search=None
    ):
        pass

    @abstractmethod
    def get_workflow_disk_usage(self, workflow, parameters, access_token):
        pass

    @abstractmethod
    def get_workflow_logs(
        self, workflow, access_token, steps=None, page=None, size=None
    ):
        pass

    @abstractmethod
    def get_workflow_status(self, workflow, access_token):
        pass

    @abstractmethod
    def get_workflow_specification(self, workflow, access_token):
        pass

    @abstractmethod
    def download_file(self, workflow, file_name, access_token):
        pass
