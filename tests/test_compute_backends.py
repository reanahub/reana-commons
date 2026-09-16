# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons compute backend validation tests."""

import pytest

from reana_commons.errors import REANAValidationError
from reana_commons.validation.compute_backends import build_compute_backends_validator

SUPPORTED = ["kubernetes", "htcondorcern"]


def _validate(reana_yaml):
    build_compute_backends_validator(reana_yaml, SUPPORTED).validate()


def _cwl_yaml(hints, packed=False):
    steps = [{"id": "step1", "hints": hints}]
    specification = {"$graph": [{"steps": steps}]} if packed else {"steps": steps}
    return {"workflow": {"type": "cwl", "specification": specification}}


def _yadage_yaml(resources):
    return {
        "workflow": {
            "type": "yadage",
            "specification": {
                "stages": [
                    {
                        "name": "step1",
                        "scheduler": {
                            "step": {"environment": {"resources": resources}}
                        },
                    }
                ]
            },
        }
    }


@pytest.mark.parametrize(
    "hints",
    [
        [],
        [{"class": "reana", "compute_backend": "htcondorcern"}],
        # The canonical REANA hint is not necessarily the last one.
        [
            {"class": "reana", "compute_backend": "htcondorcern"},
            {"class": "ResourceRequirement", "ramMin": 4096},
        ],
    ],
)
def test_cwl_supported_backends_validate(hints):
    """Supported CWL compute backends pass validation wherever declared."""
    _validate(_cwl_yaml(hints))


@pytest.mark.parametrize(
    "hints",
    [
        [{"class": "reana", "compute_backend": "unsupported"}],
        # reana-workflow-engine-cwl resolves hints by scanning them all and
        # taking the first one carrying the key, regardless of its class, so a
        # backend declared outside the ``class: reana`` hint would still run.
        [
            {"class": "ResourceRequirement", "compute_backend": "unsupported"},
            {"class": "reana", "compute_backend": "htcondorcern"},
        ],
    ],
)
def test_cwl_unsupported_backends_are_rejected(hints):
    """Every CWL hint declaring a compute backend is validated."""
    with pytest.raises(REANAValidationError, match="unsupported"):
        _validate(_cwl_yaml(hints))


def test_cwl_packed_workflow_is_validated():
    """Steps nested under ``$graph`` are validated too."""
    _validate(
        _cwl_yaml([{"class": "reana", "compute_backend": "htcondorcern"}], packed=True)
    )
    with pytest.raises(REANAValidationError, match="unsupported"):
        _validate(
            _cwl_yaml(
                [{"class": "reana", "compute_backend": "unsupported"}], packed=True
            )
        )


def test_yadage_supported_backends_validate():
    """Supported Yadage compute backends pass validation."""
    _validate(_yadage_yaml([{"compute_backend": "htcondorcern"}]))
    _validate(_yadage_yaml([{"kerberos": True}]))


@pytest.mark.parametrize(
    "resources",
    [
        [{"compute_backend": "unsupported"}],
        # reana-workflow-engine-yadage iterates all resources with overwrite, so
        # a duplicate declaration later in the list is the one that runs.
        [{"compute_backend": "htcondorcern"}, {"compute_backend": "unsupported"}],
        [{"compute_backend": "unsupported"}, {"compute_backend": "htcondorcern"}],
    ],
)
def test_yadage_unsupported_backends_are_rejected(resources):
    """Every Yadage compute backend declaration is validated."""
    with pytest.raises(REANAValidationError, match="unsupported"):
        _validate(_yadage_yaml(resources))
