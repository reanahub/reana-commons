# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for REANA Commons Serial workflow validation helpers."""

import pytest

from reana_commons.serial import (
    HTCONDOR_REQUEST_INTEGER_FIELDS,
    HTCONDOR_REQUEST_QUANTITY_FIELDS,
    check_htcondor_request_parameters,
)


def _spec(step):
    return {"steps": [step]}


# --- htcondor_request_cpus (positive integer string only) ---------------------


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_INTEGER_FIELDS)
def test_htcondor_request_integer_field_accepts_positive_int_string(field):
    """Positive integer strings pass the check for htcondor_request_cpus."""
    assert check_htcondor_request_parameters(_spec({field: "4"})) is True


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_INTEGER_FIELDS)
@pytest.mark.parametrize("bad_value", ["0", "-1", "1.5", "4 GB", "abc", " "])
def test_htcondor_request_integer_field_rejects_invalid(field, bad_value):
    """Non-positive-integer strings are rejected for htcondor_request_cpus."""
    assert check_htcondor_request_parameters(_spec({field: bad_value})) is False


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_INTEGER_FIELDS)
def test_htcondor_request_integer_field_absence_is_allowed(field):
    """Omitting htcondor_request_cpus passes validation."""
    assert check_htcondor_request_parameters(_spec({})) is True


# --- htcondor_request_memory / htcondor_request_disk (quantity strings) -------


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_QUANTITY_FIELDS)
@pytest.mark.parametrize(
    "value",
    ["4096", "4GB", "4 GB", "4 gb", "10TB", "10 TB"],
)
def test_htcondor_request_quantity_field_accepts_valid(field, value):
    """Valid HTCondor quantity strings pass the check for memory/disk."""
    assert check_htcondor_request_parameters(_spec({field: value})) is True


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_QUANTITY_FIELDS)
@pytest.mark.parametrize(
    "bad_value",
    ["0", "-1", "1.5GB", "4Gi", "4 XB", "GB", " ", "abc"],
)
def test_htcondor_request_quantity_field_rejects_invalid(field, bad_value):
    """Invalid quantity strings are rejected for memory/disk."""
    assert check_htcondor_request_parameters(_spec({field: bad_value})) is False


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_QUANTITY_FIELDS)
def test_htcondor_request_quantity_field_absence_is_allowed(field):
    """Omitting a quantity field passes validation."""
    assert check_htcondor_request_parameters(_spec({})) is True


# --- htcondor_requirements ----------------------------------------------------


def test_htcondor_requirements_accepts_non_empty_string():
    """A non-empty string passes the htcondor_requirements check."""
    assert (
        check_htcondor_request_parameters(
            _spec({"htcondor_requirements": '(Arch =?= "aarch64")'})
        )
        is True
    )


def test_htcondor_requirements_rejects_empty_string():
    """An explicitly empty htcondor_requirements is rejected."""
    assert (
        check_htcondor_request_parameters(_spec({"htcondor_requirements": "   "}))
        is False
    )


def test_htcondor_requirements_absence_is_allowed():
    """Omitting htcondor_requirements passes validation."""
    assert check_htcondor_request_parameters(_spec({})) is True


def test_multiple_steps_all_validated():
    """All steps are individually checked."""
    spec = {
        "steps": [
            {"htcondor_request_cpus": "4"},
            {"htcondor_request_memory": "1.5GB"},
        ]
    }
    assert check_htcondor_request_parameters(spec) is False
