# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Gherkin parser errors."""


class StepDefinitionNotFound(Exception):
    """The step definition was not found."""

    pass


class StepSkipped(Exception):
    """The step was skipped."""

    pass


class FeatureFileError(Exception):
    """The feature file is invalid."""

    pass
