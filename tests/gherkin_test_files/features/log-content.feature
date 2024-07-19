
# This file is part of REANA.
# Copyright (C) 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

Feature: test workflow
    Scenario: Log content
        When the workflow is finished
        Then the logs should contain "log output"

    Scenario: Engine log content
        When the workflow is finished
        Then the engine logs should contain "workflow engine log output"
        And the engine logs should contain
            """
            And
            this
            is a
            multiline
            """

    Scenario: Job log content
        When the workflow is finished
        Then the job logs should contain "Job logs"