# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for reana_commons.validation.images."""

from reana_commons.config import REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE
from reana_commons.snakemake import SNAKEMAKE_DYNAMIC_CONTAINER_IMAGE
from reana_commons.validation.images import (
    extract_cwl_images,
    extract_image_environments,
    extract_images,
    is_dynamic_image,
    iter_image_environments,
    validate_images,
)

import pytest

from reana_commons.errors import REANAValidationError

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

IMAGE = "docker.io/library/python:3.12"
IMAGE2 = "docker.io/library/ubuntu:24.04"
RUNTIME_UID = 1000
RUNTIME_GID = 0


def test_snakemake_empty_environment_uses_default_image():
    """Snakemake rules without containers resolve to the configured default."""
    specification = {
        "workflow": {
            "type": "snakemake",
            "specification": {"steps": [{"environment": ""}]},
        }
    }

    assert extract_images(specification) == [REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE]


@pytest.mark.parametrize(
    "image",
    [
        "python:{version}",
        SNAKEMAKE_DYNAMIC_CONTAINER_IMAGE,
        lambda wildcards: "python:3.12",
        None,
    ],
)
def test_dynamic_images_are_recognised(image):
    """Templates and non-strings cannot be resolved before a job runs."""
    assert is_dynamic_image(image) is True


@pytest.mark.parametrize("image", [IMAGE, "python:3.12", ""])
def test_resolvable_images_are_not_dynamic(image):
    """A concrete reference, empty or not, is usable as-is."""
    assert is_dynamic_image(image) is False


def test_snakemake_dynamic_container_is_not_reported_as_environment():
    """A per-job container is neither pullable nor meaningfully tag-checked."""
    specification = {
        "workflow": {
            "type": "snakemake",
            "specification": {
                "steps": [
                    {"environment": "python:{version}"},
                    {"environment": SNAKEMAKE_DYNAMIC_CONTAINER_IMAGE},
                    {"environment": IMAGE},
                ]
            },
        }
    }

    assert extract_image_environments(specification, RUNTIME_UID, RUNTIME_GID) == [
        {"image": IMAGE, "runtime_uid": RUNTIME_UID, "runtime_gid": RUNTIME_GID}
    ]


def test_snakemake_dynamic_container_does_not_become_the_default_image():
    """A skipped container must not be mistaken for "no container declared"."""
    specification = {
        "workflow": {
            "type": "snakemake",
            "specification": {"steps": [{"environment": "python:{version}"}]},
        }
    }

    assert list(iter_image_environments(specification, RUNTIME_UID, RUNTIME_GID)) == []


def test_snakemake_dynamic_container_is_still_vetted():
    """Image vetting must stay fail-closed on a container it cannot resolve."""
    specification = {
        "workflow": {
            "type": "snakemake",
            "specification": {"steps": [{"environment": "python:{version}"}]},
        }
    }

    assert extract_images(specification) == ["python:{version}"]
    with pytest.raises(REANAValidationError):
        validate_images(specification, enabled=True, allowlist=[IMAGE])


def test_serial_empty_environment_is_preserved():
    """Default substitution must not affect other workflow engines."""
    specification = {
        "workflow": {
            "type": "serial",
            "specification": {"steps": [{"environment": ""}]},
        }
    }

    assert extract_images(specification) == [""]


def test_null_workflow_specification_has_no_extractable_images():
    """Unexpanded workflow metadata must not crash server-side validation."""
    specification = {
        "workflow": {
            "type": "yadage",
            "specification": None,
        }
    }

    assert extract_images(specification) == []


def test_image_environments_preserve_per_step_kubernetes_uid():
    """The same image used under different UIDs produces distinct records."""
    specification = {
        "workflow": {
            "type": "serial",
            "specification": {
                "steps": [
                    {"environment": IMAGE},
                    {"environment": IMAGE, "kubernetes_uid": 2000},
                    {"environment": IMAGE, "kubernetes_uid": 2000},
                    {"environment": IMAGE2},
                ]
            },
        }
    }

    assert extract_image_environments(specification, RUNTIME_UID, RUNTIME_GID) == [
        {
            "image": IMAGE,
            "runtime_uid": RUNTIME_UID,
            "runtime_gid": RUNTIME_GID,
        },
        {
            "image": IMAGE,
            "runtime_uid": 2000,
            "runtime_gid": RUNTIME_GID,
        },
        {
            "image": IMAGE2,
            "runtime_uid": RUNTIME_UID,
            "runtime_gid": RUNTIME_GID,
        },
    ]


def test_yadage_image_environment_uses_resource_kubernetes_uid():
    """Yadage stores its per-step UID override in environment resources."""
    specification = {
        "workflow": {
            "type": "yadage",
            "specification": {
                "stages": [
                    {
                        "scheduler": {
                            "step": {
                                "environment": {
                                    "environment_type": "docker-encapsulated",
                                    "image": "docker.io/library/python",
                                    "imagetag": "3.12",
                                    "resources": [{"kubernetes_uid": 2000}],
                                }
                            }
                        }
                    }
                ]
            },
        }
    }

    assert extract_image_environments(specification, RUNTIME_UID, RUNTIME_GID) == [
        {
            "image": IMAGE,
            "runtime_uid": 2000,
            "runtime_gid": RUNTIME_GID,
        }
    ]


def test_snakemake_image_environment_uses_step_kubernetes_uid():
    """Snakemake's loaded step metadata carries its effective UID override."""
    specification = {
        "workflow": {
            "type": "snakemake",
            "specification": {
                "steps": [{"environment": IMAGE, "kubernetes_uid": 2000}]
            },
        }
    }

    assert extract_image_environments(specification, RUNTIME_UID, RUNTIME_GID) == [
        {
            "image": IMAGE,
            "runtime_uid": 2000,
            "runtime_gid": RUNTIME_GID,
        }
    ]


def test_cwl_image_environment_uses_default_runtime_identity():
    """CWL images use the cluster runtime identity because no override exists."""
    specification = {
        "workflow": {
            "type": "cwl",
            "specification": {
                "requirements": [{"class": "DockerRequirement", "dockerPull": IMAGE}]
            },
        }
    }

    assert extract_image_environments(specification, RUNTIME_UID, RUNTIME_GID) == [
        {
            "image": IMAGE,
            "runtime_uid": RUNTIME_UID,
            "runtime_gid": RUNTIME_GID,
        }
    ]


def test_image_environment_iterator_is_lazy_and_first_use_ordered():
    """A bounded consumer does not traverse or retain the complete workflow."""

    class Steps:
        def __iter__(self):
            yield {"environment": IMAGE2}
            yield {"environment": IMAGE}
            raise AssertionError("bounded consumer traversed beyond its budget")

    specification = {
        "workflow": {
            "type": "serial",
            "specification": {"steps": Steps()},
        }
    }

    environments = iter_image_environments(specification, RUNTIME_UID, RUNTIME_GID)
    assert next(environments)["image"] == IMAGE2
    assert next(environments)["image"] == IMAGE


def test_image_environment_iterator_deduplicates_as_it_streams():
    """Duplicate identities do not consume a bounded caller's response slots."""
    specification = {
        "workflow": {
            "type": "serial",
            "specification": {
                "steps": [
                    {"environment": IMAGE},
                    {"environment": IMAGE},
                    {"environment": IMAGE, "kubernetes_uid": 2000},
                ]
            },
        }
    }

    assert list(iter_image_environments(specification, RUNTIME_UID, RUNTIME_GID)) == [
        {
            "image": IMAGE,
            "runtime_uid": RUNTIME_UID,
            "runtime_gid": RUNTIME_GID,
        },
        {"image": IMAGE, "runtime_uid": 2000, "runtime_gid": RUNTIME_GID},
    ]


def _wf(requirements=None, hints=None):
    """Build a minimal CWL workflow dict."""
    wf = {}
    if requirements is not None:
        wf["requirements"] = requirements
    if hints is not None:
        wf["hints"] = hints
    return wf


# ---------------------------------------------------------------------------
# requirements – list form (original behaviour, must keep working)
# ---------------------------------------------------------------------------


def test_requirements_list_form():
    wf = _wf(requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}])
    assert extract_cwl_images(wf) == [IMAGE]


def test_requirements_list_form_no_docker():
    wf = _wf(requirements=[{"class": "ResourceRequirement", "coresMin": 1}])
    assert extract_cwl_images(wf) == []


# ---------------------------------------------------------------------------
# hints – list form (previously bypassed vetting)
# ---------------------------------------------------------------------------


def test_hints_list_form():
    wf = _wf(hints=[{"class": "DockerRequirement", "dockerPull": IMAGE}])
    assert extract_cwl_images(wf) == [IMAGE]


def test_hints_list_form_no_docker():
    wf = _wf(hints=[{"class": "ResourceRequirement", "coresMin": 1}])
    assert extract_cwl_images(wf) == []


# ---------------------------------------------------------------------------
# requirements – mapping form (previously bypassed vetting)
# ---------------------------------------------------------------------------


def test_requirements_mapping_form():
    wf = _wf(requirements={"DockerRequirement": {"dockerPull": IMAGE}})
    assert extract_cwl_images(wf) == [IMAGE]


def test_requirements_mapping_form_no_docker():
    wf = _wf(requirements={"ResourceRequirement": {"coresMin": 1}})
    assert extract_cwl_images(wf) == []


# ---------------------------------------------------------------------------
# hints – mapping form (previously bypassed vetting)
# ---------------------------------------------------------------------------


def test_hints_mapping_form():
    wf = _wf(hints={"DockerRequirement": {"dockerPull": IMAGE}})
    assert extract_cwl_images(wf) == [IMAGE]


# ---------------------------------------------------------------------------
# both requirements and hints present
# ---------------------------------------------------------------------------


def test_requirements_and_hints_both_collected():
    wf = _wf(
        requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}],
        hints=[{"class": "DockerRequirement", "dockerPull": IMAGE2}],
    )
    assert extract_cwl_images(wf) == [IMAGE, IMAGE2]


# ---------------------------------------------------------------------------
# multi-node $graph
# ---------------------------------------------------------------------------


def test_graph_list_multiple_nodes():
    graph = [
        _wf(requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}]),
        _wf(hints=[{"class": "DockerRequirement", "dockerPull": IMAGE2}]),
    ]
    assert extract_cwl_images(graph) == [IMAGE, IMAGE2]


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


def test_empty_workflow():
    assert extract_cwl_images({}) == []


def test_empty_graph_list():
    assert extract_cwl_images([]) == []


def test_single_dict_wrapped_automatically():
    wf = _wf(requirements=[{"class": "DockerRequirement", "dockerPull": IMAGE}])
    # passing a plain dict (not a list) must still work
    assert extract_cwl_images(wf) == [IMAGE]


def test_none_requirements_treated_as_empty():
    # node.get("requirements") returns None when value is explicitly null
    wf = {"requirements": None, "hints": None}
    assert extract_cwl_images(wf) == []
