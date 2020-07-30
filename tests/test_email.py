# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2020 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons email tests."""

import pytest

from reana_commons.email import send_email
from reana_commons.errors import REANAEmailNotificationError


def test_send_email_missing_config():
    """Test send_email failure if mail connection config is missing."""
    with pytest.raises(REANAEmailNotificationError):
        send_email(
            "sender@localhost",
            "test subject",
            "test body",
            "login",
            "notification@localhost",
        )
