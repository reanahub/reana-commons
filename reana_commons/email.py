# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2020, 2022, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons email util."""

from distutils.util import strtobool
from email.message import EmailMessage
import logging
import os
import smtplib
import ssl

from reana_commons.errors import REANAEmailNotificationError

# Email configuration
REANA_NOTIFICATIONS_ENABLED = bool(
    strtobool(os.getenv("REANA_NOTIFICATIONS_ENABLED", "True"))
)
REANA_EMAIL_SMTP_SERVER = os.getenv("REANA_EMAIL_SMTP_SERVER")
REANA_EMAIL_SMTP_PORT = os.getenv("REANA_EMAIL_SMTP_PORT")
REANA_EMAIL_LOGIN = os.getenv("REANA_EMAIL_LOGIN")
REANA_EMAIL_SENDER = os.getenv("REANA_EMAIL_SENDER")
REANA_EMAIL_RECEIVER = os.getenv("REANA_EMAIL_RECEIVER")
REANA_EMAIL_PASSWORD = os.getenv("REANA_EMAIL_PASSWORD")
REANA_EMAIL_SMTP_SSL = bool(strtobool(os.getenv("REANA_EMAIL_SMTP_SSL", "False")))
REANA_EMAIL_SMTP_STARTTLS = bool(
    strtobool(os.getenv("REANA_EMAIL_SMTP_STARTTLS", "True"))
)


def send_email(
    receiver_email,
    subject,
    body,
    login_email=REANA_EMAIL_LOGIN,
    sender_email=REANA_EMAIL_SENDER,
):
    """Send emails from REANA platform.

    :param receiver_email: Email address of the receiver.
    :param subject: Subject of the email.
    :param body: Body of the email.
    :param login_email: Email address of the logged user.
    :param sender_email: Email address of the sender.
    :raises REANAEmailNotificationError: If email cannot be sent, e.g. due to
        missing configuration.
    """
    message = EmailMessage()
    message["From"] = f"REANA platform <{sender_email}>"
    message["To"] = receiver_email
    message["Subject"] = subject
    message.set_content(body)

    if not REANA_NOTIFICATIONS_ENABLED:
        raise REANAEmailNotificationError(
            "An email was about to be sent, but REANA notifications are disabled, "
            "therefore it won't be dispatched."
        )

    if not (REANA_EMAIL_SMTP_SERVER and REANA_EMAIL_SMTP_PORT):
        raise REANAEmailNotificationError(
            "Cannot send email, missing server and port configuration. "
            "Please provide the following environment variables:\n"
            "REANA_EMAIL_SMTP_SERVER\nREANA_EMAIL_SMTP_PORT"
        )

    context = ssl.create_default_context()
    if REANA_EMAIL_SMTP_SSL:
        smtp_server = smtplib.SMTP_SSL(
            REANA_EMAIL_SMTP_SERVER, REANA_EMAIL_SMTP_PORT, context=context
        )
    else:
        smtp_server = smtplib.SMTP(REANA_EMAIL_SMTP_SERVER, REANA_EMAIL_SMTP_PORT)

    with smtp_server:
        if REANA_EMAIL_SMTP_STARTTLS:
            smtp_server.starttls(context=context)
        if login_email or REANA_EMAIL_PASSWORD:
            smtp_server.login(login_email, REANA_EMAIL_PASSWORD)
        smtp_server.send_message(message)

    logging.info(
        f"Email sent, login: {login_email}, "
        f"sender: {sender_email}, receiver: {receiver_email}\n"
        f"Body:\n{message}"
    )
