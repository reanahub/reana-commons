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
        return 'Operation cancelled. Secrets {} '
        'do not exist.'.format(self.missing_secrets_list)


class REANASecretAlreadyExists(Exception):
    """The referenced secret already exists."""
