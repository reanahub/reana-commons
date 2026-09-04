# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for extracting container images from REANA workflow specifications."""

from typing import Dict, Iterable, Iterator, List

from reana_commons.config import REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE
from reana_commons.errors import REANAValidationError


def extract_images(reana_yaml: Dict) -> List[str]:
    """Extract container images from a REANA workflow specification.

    Returns the full image string (``image`` or ``image:tag``) for every step.
    Empty strings are included as-is; callers decide whether to treat them as
    an admin-controlled default (e.g. Snakemake rules without a container
    directive produce ``""`` from the workflow loader).

    :param reana_yaml: Parsed REANA specification dictionary.
    :returns: List of image strings, one per step/requirement.
    """
    workflow_type = reana_yaml["workflow"]["type"]
    specification = reana_yaml["workflow"].get("specification") or {}

    if workflow_type == "snakemake":
        return [
            step.get("environment") or REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE
            for step in specification.get("steps", [])
        ]
    elif workflow_type == "serial":
        return [step.get("environment", "") for step in specification.get("steps", [])]
    elif workflow_type == "yadage":
        return [
            _yadage_env_to_image(env)
            for env in iter_yadage_environments(specification.get("stages", []))
        ]
    elif workflow_type == "cwl":
        return extract_cwl_images(specification.get("$graph", specification))
    return []


def iter_image_environments(
    reana_yaml: Dict, runtime_uid: int, runtime_gid: int
) -> Iterator[Dict]:
    """Yield distinct image and effective runtime-identity combinations.

    A workflow may use the same image in several steps with different
    ``kubernetes_uid`` overrides. Keeping the image and identity together lets
    clients check every effective execution context instead of incorrectly
    caching compatibility by image name alone. Records are yielded in first-use
    order, allowing bounded consumers to stop without materialising the whole
    workflow. At most one deduplication key is retained per yielded record.

    :param reana_yaml: Parsed REANA specification dictionary.
    :param runtime_uid: Default workflow runtime UID.
    :param runtime_gid: Workflow runtime GID.
    :yields: ``{image, runtime_uid, runtime_gid}`` records, deduplicated by the
        complete tuple.
    """
    workflow_type = reana_yaml["workflow"]["type"]
    specification = reana_yaml["workflow"].get("specification") or {}
    default_uid = int(runtime_uid)
    default_gid = int(runtime_gid)
    seen = set()

    def raw_environments():
        """Yield image and optional UID pairs without deduplicating them."""
        if workflow_type in ("serial", "snakemake"):
            for step in specification.get("steps", []):
                image = step.get("environment", "")
                if workflow_type == "snakemake":
                    image = image or REANA_DEFAULT_SNAKEMAKE_ENV_IMAGE
                yield image, step.get("kubernetes_uid")
        elif workflow_type == "yadage":
            for environment in iter_yadage_environments(
                specification.get("stages", [])
            ):
                kubernetes_uid = next(
                    (
                        resource["kubernetes_uid"]
                        for resource in environment.get("resources", [])
                        if "kubernetes_uid" in resource
                    ),
                    None,
                )
                yield _yadage_env_to_image(environment), kubernetes_uid
        elif workflow_type == "cwl":
            for image in iter_cwl_images(specification.get("$graph", specification)):
                yield image, None

    for image, kubernetes_uid in raw_environments():
        if not image:
            continue
        effective_uid = int(default_uid if kubernetes_uid is None else kubernetes_uid)
        key = (image, effective_uid, default_gid)
        if key in seen:
            continue
        seen.add(key)
        yield {
            "image": image,
            "runtime_uid": effective_uid,
            "runtime_gid": default_gid,
        }


def extract_image_environments(
    reana_yaml: Dict, runtime_uid: int, runtime_gid: int
) -> List[Dict]:
    """Return sorted distinct image/runtime-identity records.

    This compatibility wrapper preserves the ordering of the original list API.
    Bounded consumers should use :func:`iter_image_environments` directly.
    """
    return [
        {
            "image": image,
            "runtime_uid": effective_uid,
            "runtime_gid": effective_gid,
        }
        for image, effective_uid, effective_gid in sorted(
            {
                (
                    environment["image"],
                    environment["runtime_uid"],
                    environment["runtime_gid"],
                )
                for environment in iter_image_environments(
                    reana_yaml, runtime_uid, runtime_gid
                )
            }
        )
    ]


def iter_yadage_environments(stages: List) -> Iterator[Dict]:
    """Recursively yield environment dicts from nested Yadage stages.

    Each yielded dict is the raw ``scheduler.step.environment`` object, which
    contains at minimum ``image``, optionally ``imagetag``, and optionally a
    ``resources`` list.  Callers that only need image strings should use
    :func:`extract_images` instead.

    :param stages: The ``stages`` list from a Yadage workflow specification.
    """
    for stage in stages:
        if "workflow" in stage["scheduler"]:
            nested = stage["scheduler"]["workflow"].get("stages", [])
            yield from iter_yadage_environments(nested)
        else:
            yield stage["scheduler"]["step"]["environment"]


def _iter_cwl_reqs(node: Dict) -> Iterator[Dict]:
    """Yield {class, ...} dicts from CWL requirements/hints, list or mapping form."""
    for key in ("requirements", "hints"):
        block = node.get(key) or []
        if isinstance(block, dict):
            for class_name, body in block.items():
                entry = {"class": class_name}
                if isinstance(body, dict):
                    entry.update(body)
                yield entry
        else:
            for item in block:
                if isinstance(item, dict):
                    yield item


def iter_cwl_images(cwl_graph) -> Iterator[str]:
    """Yield ``dockerPull`` images from a CWL workflow or ``$graph`` value."""
    if isinstance(cwl_graph, dict):
        cwl_graph = [cwl_graph]
    for workflow in cwl_graph:
        for requirement in _iter_cwl_reqs(workflow):
            if "dockerPull" in requirement:
                yield requirement["dockerPull"]


def extract_cwl_images(cwl_graph) -> List[str]:
    """Extract ``dockerPull`` images from a CWL ``$graph`` value.

    :param cwl_graph: Either a single CWL workflow dict or a list of them
        (the value of the ``$graph`` key, or the specification dict itself when
        no ``$graph`` key is present).
    :returns: List of image strings from ``DockerRequirement.dockerPull`` entries.
    """
    return list(iter_cwl_images(cwl_graph))


def _yadage_env_to_image(env: Dict) -> str:
    """Build a full image string from a Yadage environment dict."""
    tag = env.get("imagetag", "")
    return "{}{}".format(env["image"], ":{}".format(tag) if tag else "")


def validate_images(reana_yaml: Dict, enabled: bool, allowlist: Iterable[str]) -> None:
    """Validate workflow container images against the vetted images allowlist.

    :param reana_yaml: REANA specification.
    :param enabled: Whether container image vetting is enabled in the cluster.
    :param allowlist: Iterable of allowed image strings.
    :raises REANAValidationError: If an image is not in the allowlist.
    """
    if not enabled:
        return

    allowed_images = set(allowlist)
    for image in extract_images(reana_yaml):
        if image and image not in allowed_images:
            raise REANAValidationError(f"Image not allowed: {image}")
