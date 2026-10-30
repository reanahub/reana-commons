# This file is part of REANA.
# Copyright (C) 2023, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons volume utilities testing."""

import pytest

from reana_commons.k8s.volumes import extract_cvmfs_repository, get_k8s_cvmfs_volumes


def test_cvmfs_volumes():
    """Test volumes and volume mounts for CVMFS."""
    repos = ["x.y.z", "abc.foo"]
    volume_mounts, volumes = get_k8s_cvmfs_volumes(repos)

    assert len(volume_mounts) == len(repos)
    for mount in volume_mounts:
        assert any(mount["name"] == volume["name"] for volume in volumes)
        assert mount["mountPath"].endswith(tuple(repos))


@pytest.mark.parametrize(
    "path,expected",
    [
        (
            "/cvmfs/unpacked.cern.ch/registry.hub.docker.com/library/python:3.9",
            "unpacked.cern.ch",
        ),
        ("/cvmfs/sft.cern.ch/some/path", "sft.cern.ch"),
        ("/cvmfs/atlas.cern.ch", "atlas.cern.ch"),
    ],
)
def test_extract_cvmfs_repository(path, expected):
    """Test extraction of CVMFS repository name from path."""
    assert extract_cvmfs_repository(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "/not/cvmfs/path",
        "cvmfs/missing/leading/slash",
        "/cvmfs/",
        "/cvmfs",
    ],
)
def test_extract_cvmfs_repository_invalid(path):
    """Test that invalid paths raise ValueError."""
    with pytest.raises(ValueError):
        extract_cvmfs_repository(path)
