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
REANA_EMAIL_SMTP_SERVER = os.getenv('REANA_EMAIL_SMTP_SERVER')
REANA_EMAIL_SMTP_PORT = os.getenv('REANA_EMAIL_SMTP_PORT')
REANA_EMAIL_LOGIN = os.getenv('REANA_EMAIL_LOGIN')
REANA_EMAIL_SENDER = os.getenv('REANA_EMAIL_SENDER')
REANA_EMAIL_PASSWORD = os.getenv('REANA_EMAIL_PASSWORD')


def send_email(receiver_email, subject, body, login_email=REANA_EMAIL_LOGIN,
               sender_email=REANA_EMAIL_SENDER):
    """Send emails from REANA platform."""
    message = 'Subject: {subject}\n\n{body}'.format(subject=subject, body=body)
    if os.getenv('FLASK_ENV') == 'development':
        logging.info('Email sent, login: {}, sender: {}, receiver: {}'
                     .format(login_email, sender_email, receiver_email))
        logging.info('Body:\n{}'.format(message))
    else:
        context = ssl.create_default_context()
        with smtplib.SMTP(REANA_EMAIL_SMTP_SERVER,
                          REANA_EMAIL_SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(login_email, REANA_EMAIL_PASSWORD)
            server.sendmail(sender_email, receiver_email, message)
