# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2020, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons email tests."""

import logging
import socket
import time

import pytest

from reana_commons import email
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


@pytest.fixture
def smtp_config(monkeypatch):
    """Configure send_email for a local SMTP server without TLS or login."""
    monkeypatch.setattr(email, "REANA_EMAIL_SMTP_SERVER", "127.0.0.1")
    monkeypatch.setattr(email, "REANA_EMAIL_SMTP_SSL", False)
    monkeypatch.setattr(email, "REANA_EMAIL_SMTP_STARTTLS", False)
    monkeypatch.setattr(email, "REANA_EMAIL_PASSWORD", None)


@pytest.mark.parametrize("ssl", [False, True])
def test_send_email_stalled_server_times_out(smtp_config, monkeypatch, ssl):
    """Test that send_email fails when the SMTP server stops responding."""
    with socket.socket() as stalled_server:
        # accept connections, but never send the SMTP greeting
        stalled_server.bind(("127.0.0.1", 0))
        stalled_server.listen()
        monkeypatch.setattr(
            email, "REANA_EMAIL_SMTP_PORT", stalled_server.getsockname()[1]
        )
        monkeypatch.setattr(email, "REANA_EMAIL_SMTP_SSL", ssl)
        monkeypatch.setattr(email, "REANA_EMAIL_SMTP_TIMEOUT", 0.5)

        start = time.monotonic()
        with pytest.raises(OSError):
            send_email("receiver@localhost", "test subject", "test body")
        assert time.monotonic() - start < 5


def test_send_email_does_not_log_body(smtp_config, monkeypatch, caplog):
    """Test that send_email does not write the email body to the logs."""

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            self.sent = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, message):
            self.sent.append(message)

    monkeypatch.setattr(email, "REANA_EMAIL_SMTP_PORT", 25)
    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)

    with caplog.at_level(logging.DEBUG):
        send_email("receiver@localhost", "test subject", "secret-body-4f2a")

    assert "receiver@localhost" in caplog.text
    assert "secret-body-4f2a" not in caplog.text
