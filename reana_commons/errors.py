# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA Commons errors."""


class MissingAPIClientConfiguration(Exception):
    """REANA Server URL is not set."""


class REANASecretDoesNotExist(Exception):
    """The referenced REANA secret does not exist."""

    def __init__(self, missing_secrets_list=None):
        """Initialise REANA secret does not exist exception."""
        self.missing_secrets_list = missing_secrets_list

    def __str__(self):
        """Represent REANA secret does not exist exception as a string."""
        return "Operation cancelled. Secrets {} do not exist.".format(
            self.missing_secrets_list
        )


class REANASecretAlreadyExists(Exception):
    """The referenced secret already exists."""


class REANAValidationError(Exception):
    """Validation error."""

    def __init__(self, message):
        """Initialize REANAValidationError exception."""
        self.message = message


class REANAConfigDoesNotExist(Exception):
    """Validation error."""

    def __init__(self, message):
        """Initialize REANAConfigDoesNotExist exception."""
        self.message = message


class REANAEmailNotificationError(Exception):
    """Email notification error."""

    def __init__(self, message):
        """Initialize REANAEmailNotificationError exception."""
        self.message = message


class REANAMissingWorkspaceError(Exception):
    """Missing workspace error."""

    def __init__(self, message):
        """Initialize REANAMissingWorkspaceError exception."""
        self.message = message


class REANAQuotaExceededError(Exception):
    """Quota exceeded error."""

    def __init__(self, message="User quota exceeded."):
        """Initialize REANAQuotaExceededError exception."""
        self.message = message


class REANAKubernetesWrongMemoryFormat(Exception):
    """Kubernetes memory value has wrong format."""

    def __init__(self, message):
        """Initialize REANAKubernetesWrongMemoryFormat exception."""
        self.message = message


class REANAKubernetesMemoryLimitExceeded(Exception):
    """Kubernetes memory value exceed max limit."""

    def __init__(self, message):
        """Initialize REANAKubernetesMemoryLimitExceeded exception."""
        self.message = message


class REANAJobControllerSubmissionError(Exception):
    """REANA Job submission exception."""

    def __init__(self, message):
        """Initialize REANAJobSubmissionError exception."""
        self.message = message

    def __str__(self):
        """Represent REANA job controller submission exception as a string."""
        return "Job submission error: {}".format(self.message or "")
