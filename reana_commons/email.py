# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2020 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons email util."""

import logging
import os
import smtplib
import ssl

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
    headers = "From: REANA platform <{from_}>\nTo: {to}\nSubject: {subject}".format(
        from_=sender_email, to=receiver_email, subject=subject
    )
    message = "{headers}\n\n{body}".format(headers=headers, body=body)

    context = ssl.create_default_context()
    with smtplib.SMTP(REANA_EMAIL_SMTP_SERVER, REANA_EMAIL_SMTP_PORT) as server:
        if os.getenv("FLASK_ENV") != "development":
            server.starttls(context=context)
            server.login(login_email, REANA_EMAIL_PASSWORD)
        server.sendmail(sender_email, receiver_email, message)
        logging.info(
            "Email sent, login: {}, sender: {}, receiver: {}".format(
                login_email, sender_email, receiver_email
            )
        )
        logging.info("Body:\n{}".format(message))
