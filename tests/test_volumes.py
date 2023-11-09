# This file is part of REANA.
# Copyright (C) 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""REANA-Commons volume utilities testing."""
from reana_commons.k8s.volumes import get_k8s_cvmfs_volumes


def test_cvmfs_volumes():
    """Test volumes and volume mounts for CVMFS."""
    repos = ["x.y.z", "abc.foo"]
    volume_mounts, volumes = get_k8s_cvmfs_volumes(repos)

    assert len(volume_mounts) == len(repos)
    for mount in volume_mounts:
        assert any(mount["name"] == volume["name"] for volume in volumes)
        assert mount["mountPath"].endswith(tuple(repos))
