# This file is part of REANA.
# Copyright (C) 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

Feature: test workflow
    Scenario: Run duration
        When the workflow is finished
        Then the workflow run duration should be less than 5 minutes

    Scenario: Job run duration
        When the workflow is finished
        Then the duration of the step "jobname" should be less than 5 minutes