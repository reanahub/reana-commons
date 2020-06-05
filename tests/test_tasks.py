# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018, 2019 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons Task tests."""

from mock import patch

from reana_commons.tasks import reana_ready


def test_reana_ready():
    """Test that reana_ready task checks all conditions."""
    with patch(
        "reana_commons.config.REANA_READY_CONDITIONS",
        {
            "pytest_reana.fixtures": [
                "sample_condition_for_starting_queued_workflows",
                "sample_condition_for_starting_queued_workflows",
                "sample_condition_for_requeueing_workflows",
            ]
        },
    ):
        assert not reana_ready()

    with patch(
        "reana_commons.config.REANA_READY_CONDITIONS",
        {"pytest_reana.fixtures": ["sample_condition_for_starting_queued_workflows"]},
    ):
        assert reana_ready()
