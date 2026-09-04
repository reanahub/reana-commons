# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Offline runtime-environment checks.

The server reports environment identities and reproducibility warnings without
contacting registries. Image availability and filesystem-dependent properties
are checked explicitly by the client-side ``--pull`` operation, using the
user's container runtime and registry credentials.
"""

from typing import Dict, Iterable, Iterator, List, Optional, Tuple


def _finding(image: str, code: str, message: str) -> Dict:
    """Build a single advisory finding for an image."""
    return {"image": image, "code": code, "message": message}


def parse_image_reference(
    image: str,
) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Split an image reference into ``(registry, repository, tag, digest)``."""
    reference = image
    digest = None
    if "@" in reference:
        reference, digest = reference.split("@", 1)

    first, slash, remainder = reference.partition("/")
    if slash and ("." in first or ":" in first or first == "localhost"):
        registry = first
    else:
        registry, remainder = "docker.io", reference

    tag = None
    last_segment = remainder.rsplit("/", 1)[-1]
    if ":" in last_segment:
        remainder, tag = remainder.rsplit(":", 1)
    repository = remainder

    if registry == "docker.io" and "/" not in repository:
        repository = "library/" + repository
    if not tag and not digest:
        tag = "latest"
    return registry, repository, tag, digest


def iter_environment_tag_warnings(images: Iterable[str]) -> Iterator[Dict]:
    """Yield tag warnings for distinct images in first-use order."""
    seen = set()
    for image in images:
        if not image or image in seen:
            continue
        seen.add(image)
        _registry, _repository, tag, digest = parse_image_reference(image)
        if not digest and (tag is None or tag == "latest"):
            yield _finding(
                image,
                "image_tag",
                'Using "{}" without a fixed tag harms reproducibility; pin an '
                "explicit version.".format(image),
            )


def check_environment_tags(images: List[str]) -> List[Dict]:
    """Return offline reproducibility warnings for distinct image references."""
    return list(iter_environment_tag_warnings(images))
