# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for offline runtime-environment checks."""

import pytest

from reana_commons.validation.environments import (
    check_environment_tags,
    iter_environment_tag_warnings,
    parse_image_reference,
)


@pytest.mark.parametrize(
    "image,expected",
    [
        ("python", ("docker.io", "library/python", "latest", None)),
        ("python:3.12", ("docker.io", "library/python", "3.12", None)),
        ("org/img:tag", ("docker.io", "org/img", "tag", None)),
        ("quay.io/org/img:1", ("quay.io", "org/img", "1", None)),
        ("registry:5000/img:1", ("registry:5000", "img", "1", None)),
        ("localhost/img", ("localhost", "img", "latest", None)),
        (
            "ubuntu@sha256:abc",
            ("docker.io", "library/ubuntu", None, "sha256:abc"),
        ),
    ],
)
def test_parse_image_reference(image, expected):
    assert parse_image_reference(image) == expected


def test_check_environment_tags_is_offline_and_deduplicates():
    """Only floating tags warn, with no registry or container-runtime access."""
    findings = check_environment_tags(
        [
            "python",
            "python",
            "python:3.12",
            "ubuntu@sha256:abc",
            "quay.io/org/image",
        ]
    )

    assert [(finding["image"], finding["code"]) for finding in findings] == [
        ("python", "image_tag"),
        ("quay.io/org/image", "image_tag"),
    ]


def test_environment_tag_warning_iterator_is_lazy():
    """Bounded callers may stop before traversing all image references."""

    def images():
        yield "python"
        raise AssertionError("bounded consumer traversed beyond its budget")

    warnings = iter_environment_tag_warnings(images())
    assert next(warnings)["image"] == "python"
