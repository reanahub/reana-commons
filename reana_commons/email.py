# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2020, 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons email util."""

from email.message import EmailMessage
import logging
import os
import smtplib
import ssl

from reana_commons.errors import REANAEmailNotificationError

# Email configuration
REANA_EMAIL_SMTP_SERVER = os.getenv("REANA_EMAIL_SMTP_SERVER")
REANA_EMAIL_SMTP_PORT = os.getenv("REANA_EMAIL_SMTP_PORT")
REANA_EMAIL_LOGIN = os.getenv("REANA_EMAIL_LOGIN")
REANA_EMAIL_SENDER = os.getenv("REANA_EMAIL_SENDER")
REANA_EMAIL_PASSWORD = os.getenv("REANA_EMAIL_PASSWORD")


def send_email(
    receiver_email,
    subject,
    body,
    login_email=REANA_EMAIL_LOGIN,
    sender_email=REANA_EMAIL_SENDER,
):
    """Send emails from REANA platform."""
    message = EmailMessage()
    message["From"] = f"REANA platform <{sender_email}>"
    message["To"] = receiver_email
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    if not (REANA_EMAIL_SMTP_SERVER and REANA_EMAIL_SMTP_PORT):
        raise REANAEmailNotificationError(
            "Cannot send email, missing server and port configuration. "
            "Please provide the following environment variables:\n"
            "REANA_EMAIL_SMTP_SERVER\nREANA_EMAIL_SMTP_PORT"
        )
    with smtplib.SMTP(REANA_EMAIL_SMTP_SERVER, REANA_EMAIL_SMTP_PORT) as server:
        if os.getenv("FLASK_ENV") != "development":
            server.starttls(context=context)
            server.login(login_email, REANA_EMAIL_PASSWORD)
        server.send_message(message)
        logging.info(
            "Email sent, login: {}, sender: {}, receiver: {}".format(
                login_email, sender_email, receiver_email
            )
        )
        logging.info("Body:\n{}".format(message))
