# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for extracting container images from REANA workflow specifications."""

from typing import Dict, Iterator, List


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
    specification = reana_yaml["workflow"].get("specification", {})

    if workflow_type in ("serial", "snakemake"):
        return [step.get("environment", "") for step in specification.get("steps", [])]
    elif workflow_type == "yadage":
        return [
            _yadage_env_to_image(env)
            for env in iter_yadage_environments(specification.get("stages", []))
        ]
    elif workflow_type == "cwl":
        return extract_cwl_images(specification.get("$graph", specification))
    return []


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


def extract_cwl_images(cwl_graph) -> List[str]:
    """Extract ``dockerPull`` images from a CWL ``$graph`` value.

    :param cwl_graph: Either a single CWL workflow dict or a list of them
        (the value of the ``$graph`` key, or the specification dict itself when
        no ``$graph`` key is present).
    :returns: List of image strings from ``DockerRequirement.dockerPull`` entries.
    """
    if isinstance(cwl_graph, dict):
        cwl_graph = [cwl_graph]
    return [
        req["dockerPull"]
        for wf in cwl_graph
        for req in _iter_cwl_reqs(wf)
        if "dockerPull" in req
    ]


def _yadage_env_to_image(env: Dict) -> str:
    """Build a full image string from a Yadage environment dict."""
    tag = env.get("imagetag", "")
    return "{}{}".format(env["image"], ":{}".format(tag) if tag else "")
