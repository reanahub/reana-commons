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
    get_htcondor_request_parameter_errors,
    serial_load,
)


def _spec(step):
    return {"steps": [step]}


# --- Detailed validation errors -----------------------------------------------


def test_get_htcondor_request_parameter_errors_valid():
    """Valid HTCondor request parameters produce no errors."""
    assert (
        get_htcondor_request_parameter_errors(
            _spec({"c4p_cpu_cores": "4", "c4p_gpu_count": "2"})
        )
        == []
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("c4p_cpu_cores", "two"),
        ("c4p_gpu_count", "0"),
    ],
)
def test_get_htcondor_request_parameter_errors_one_field_not_valid(field, value):
    """Invalid HTCondor request parameters produce error messages."""
    errors = get_htcondor_request_parameter_errors(_spec({field: value}))

    assert len(errors) == 1
    assert "In step 0:" in errors[0]
    assert field in errors[0]
    assert repr(value) in errors[0]
    assert "positive integer" in errors[0]


def test_get_htcondor_request_parameter_errors_two_fields_not_valid():
    """Invalid HTCondor request parameters produce error messages."""
    errors = get_htcondor_request_parameter_errors(
        _spec({"c4p_cpu_cores": "two", "c4p_gpu_count": "0"})
    )

    assert len(errors) == 2
    assert any("c4p_cpu_cores" in error for error in errors)
    assert any("c4p_gpu_count" in error for error in errors)


@pytest.mark.parametrize(
    "field,value",
    [
        ("c4p_cpu_cores", "two"),
        ("c4p_gpu_count", "two"),
        ("c4p_gpu_count", "0"),
    ],
)
def test_serial_load_raises_htcondor_request_parameter_errors(field, value):
    """Invalid HTCondor request parameters raise detailed exceptions."""
    specification = {"steps": [{field: value}]}

    with pytest.raises(Exception) as exception_info:
        serial_load(None, specification)

    error_message = str(exception_info.value)

    assert field in error_message
    assert repr(value) in error_message
    assert "positive integer" in error_message


def test_serial_load_raises_multiple_htcondor_request_parameter_errors():
    """Multiple invalid HTCondor request parameters raise detailed exceptions."""
    specification = {
        "steps": [
            {
                "c4p_cpu_cores": "two",
                "c4p_gpu_count": "two",
            }
        ]
    }

    with pytest.raises(Exception) as exception_info:
        serial_load(None, specification)

    error_message = str(exception_info.value)

    assert "c4p_cpu_cores" in error_message
    assert "'two'" in error_message
    assert "c4p_gpu_count" in error_message
    assert "'two'" in error_message
    assert "; " in error_message


# --- htcondor_request_cpus (positive integer string only) ---------------------


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_INTEGER_FIELDS)
def test_htcondor_request_integer_field_accepts_positive_int_string(field):
    """Positive integer strings pass the check for htcondor_request_cpus."""
    assert check_htcondor_request_parameters(_spec({field: "4"})) is True


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_INTEGER_FIELDS)
@pytest.mark.parametrize("bad_value", ["0", "-1", "1.5", "4 GB", "abc", " ", "02"])
def test_htcondor_request_integer_field_rejects_invalid(field, bad_value):
    """Non-positive-integer strings are rejected for htcondor_request_cpus."""
    assert check_htcondor_request_parameters(_spec({field: bad_value})) is False


@pytest.mark.parametrize("field", HTCONDOR_REQUEST_INTEGER_FIELDS)
def test_htcondor_request_integer_field_rejects_non_string(field):
    """Non-string values are rejected for integer fields."""
    assert check_htcondor_request_parameters(_spec({field: 2})) is False


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
