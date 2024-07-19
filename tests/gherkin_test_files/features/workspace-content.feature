# This file is part of REANA.
# Copyright (C) 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

Feature: test workflow
    Scenario: All the outputs in the workspace
        When the workflow is finished
        Then all the outputs should be included in the workspace

    Scenario: Specific files in the workspace
        When the workflow is finished
        Then the workspace should contain "output1.png"
        And the workspace should not contain "a png file.png"

    Scenario: Workspace size
        When the workflow is finished
        Then the workspace size should be more than 20 MiB
        And the workspace size should be less than 35344320