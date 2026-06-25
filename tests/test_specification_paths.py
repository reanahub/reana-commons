# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.

"""Tests for the authoritative workflow-source path contract."""

import os
import pathlib

import pytest

from reana_commons import specification_paths
from reana_commons.errors import (
    REANASpecificationPathError,
    REANASpecificationScopeError,
    REANAValidationError,
)
from reana_commons.specification_paths import (
    gather_validation_members,
    gather_workspace_seed_members,
    open_regular_file_beneath,
    workflow_parameter_file,
)


def _project(tmp_path: pathlib.Path):
    (tmp_path / "workflow").mkdir()
    (tmp_path / "workflow" / "Snakefile").write_text("")
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "common.smk").write_text("")
    (tmp_path / "params.yaml").write_text("answer: 42")
    (tmp_path / "input.csv").write_text("dataset")
    (tmp_path / "tests.feature").write_text("Feature: test")
    specification = tmp_path / "selected.yaml"
    specification.write_text("""
workflow:
  type: snakemake
  file: workflow/Snakefile
  directories: [rules]
  parameters:
    file: params.yaml
inputs:
  files: [input.csv]
tests:
  files: [tests.feature]
""")
    return specification


def test_validation_and_workspace_seed_scopes(tmp_path):
    """Datasets/tests enter only the post-validation workspace seed."""
    specification = _project(tmp_path)
    validation, _raw, legacy = gather_validation_members(str(specification))
    seed, _raw, _legacy = gather_workspace_seed_members(str(specification))
    assert not legacy
    assert set(validation) == {
        "reana.yaml",
        "workflow/Snakefile",
        "rules/common.smk",
        "params.yaml",
    }
    assert set(seed) == set(validation) | {"input.csv", "tests.feature"}


def test_external_workflow_uses_legacy_input_scope_when_explicit_scope_absent(
    tmp_path,
):
    """External workflows remain compatible with legacy input declarations."""
    (tmp_path / "workflow").mkdir()
    (tmp_path / "workflow" / "main.cwl").write_text("class: Workflow")
    (tmp_path / "workflow" / "step.cwl").write_text("class: CommandLineTool")
    (tmp_path / "data.txt").write_text("data")
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "inputs:\n"
        "  files: [data.txt]\n"
        "  directories: [workflow]\n"
        "workflow:\n"
        "  type: cwl\n"
        "  file: workflow/main.cwl\n"
    )

    members, _raw, _legacy = gather_validation_members(str(specification))

    assert set(members) == {
        "reana.yaml",
        "data.txt",
        "workflow/main.cwl",
        "workflow/step.cwl",
    }


def test_legacy_input_can_repeat_selected_canonical_specification(tmp_path):
    """A legacy input declaration may repeat the already selected reana.yaml."""
    (tmp_path / "main.cwl").write_text("class: Workflow")
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "inputs:\n"
        "  files: [reana.yaml]\n"
        "workflow:\n"
        "  type: cwl\n"
        "  file: main.cwl\n"
    )

    validation, _raw, _legacy = gather_validation_members(str(specification))
    seed, _raw, _legacy = gather_workspace_seed_members(str(specification))

    assert validation == {
        "reana.yaml": str(specification),
        "main.cwl": str(tmp_path / "main.cwl"),
    }
    assert seed == validation


def test_different_selected_specification_cannot_claim_canonical_path(tmp_path):
    """A sibling reana.yaml cannot replace a differently selected specification."""
    (tmp_path / "main.cwl").write_text("class: Workflow")
    (tmp_path / "reana.yaml").write_text("workflow: {type: serial}\n")
    specification = tmp_path / "selected.yaml"
    specification.write_text(
        "inputs:\n"
        "  files: [reana.yaml]\n"
        "workflow:\n"
        "  type: cwl\n"
        "  file: main.cwl\n"
    )

    with pytest.raises(REANASpecificationPathError) as error:
        gather_validation_members(str(specification))

    assert error.value.reason == "conflict"
    assert error.value.field == "inputs.files"
    assert error.value.path == "reana.yaml"


def test_workflow_source_cannot_claim_selected_canonical_path(tmp_path):
    """The compatibility exception remains limited to legacy input files."""
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "workflow:\n"
        "  type: serial\n"
        "  files: [reana.yaml]\n"
        "  specification: {steps: []}\n"
    )

    with pytest.raises(REANASpecificationPathError) as error:
        gather_validation_members(str(specification))

    assert error.value.reason == "conflict"
    assert error.value.field == "workflow.files"


def test_copied_specification_preserves_selected_canonical_identity(tmp_path):
    """An immutable canonical copy keeps the selected source filename identity."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.cwl").write_text("class: Workflow")
    specification = source / "reana.yaml"
    specification.write_text(
        "inputs:\n"
        "  files: [reana.yaml]\n"
        "workflow:\n"
        "  type: cwl\n"
        "  file: main.cwl\n"
    )
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    copied_specification = snapshot / "reana.yaml"
    copied_specification.write_bytes(specification.read_bytes())

    members, _raw, _legacy = gather_validation_members(
        str(copied_specification),
        source_base_directory=str(source),
        selected_specification_name=specification.name,
    )

    assert members == {
        "reana.yaml": str(copied_specification),
        "main.cwl": str(source / "main.cwl"),
    }


@pytest.mark.parametrize("explicit_key", ["files", "directories"])
def test_explicit_empty_workflow_scope_disables_legacy_fallback(tmp_path, explicit_key):
    """Key presence selects the narrow scope even when its list is empty."""
    (tmp_path / "workflow").mkdir()
    (tmp_path / "workflow" / "main.cwl").write_text("class: Workflow")
    (tmp_path / "workflow" / "step.cwl").write_text("class: CommandLineTool")
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "inputs:\n"
        "  directories: [workflow]\n"
        "workflow:\n"
        "  type: cwl\n"
        "  file: workflow/main.cwl\n"
        "  {}: []\n".format(explicit_key)
    )

    members, _raw, _legacy = gather_validation_members(str(specification))

    assert set(members) == {"reana.yaml", "workflow/main.cwl"}


def test_inline_serial_workflow_does_not_use_legacy_input_scope(tmp_path):
    """Serial runtime inputs are not copied into validation snapshots."""
    (tmp_path / "large.dat").write_text("runtime input")
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "inputs:\n"
        "  files: [large.dat]\n"
        "workflow:\n"
        "  type: serial\n"
        "  specification: {steps: []}\n"
    )

    members, _raw, _legacy = gather_validation_members(str(specification))

    assert set(members) == {"reana.yaml"}


def test_overlapping_directories_are_not_misreported_as_empty(tmp_path):
    """A directory is non-empty even when its files were already selected."""
    (tmp_path / "workflow" / "steps").mkdir(parents=True)
    (tmp_path / "workflow" / "main.cwl").write_text("class: Workflow")
    (tmp_path / "workflow" / "steps" / "step.cwl").write_text("class: CommandLineTool")
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "workflow:\n"
        "  type: cwl\n"
        "  file: workflow/main.cwl\n"
        "  directories: [workflow, workflow/steps]\n"
    )

    members, _raw, _legacy = gather_validation_members(str(specification))

    assert set(members) == {
        "reana.yaml",
        "workflow/main.cwl",
        "workflow/steps/step.cwl",
    }


def test_declared_path_count_is_bounded_before_processing(tmp_path, monkeypatch):
    """Duplicate declarations cannot multiply work beyond the scope budget."""
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "workflow:\n"
        "  type: serial\n"
        "  specification: {steps: []}\n"
        "  files: [missing, missing]\n"
        "  directories: [missing]\n"
    )
    monkeypatch.setattr(specification_paths, "SPECIFICATION_BUNDLE_MAX_FILES", 2)

    def unexpected_path_processing(*args, **kwargs):
        pytest.fail("oversized declarations reached filesystem processing")

    monkeypatch.setattr(specification_paths, "_add_file", unexpected_path_processing)
    monkeypatch.setattr(
        specification_paths, "_add_directory", unexpected_path_processing
    )

    with pytest.raises(REANAValidationError, match="too many declared paths"):
        gather_validation_members(str(specification))


def test_repeated_directory_root_is_traversed_once_across_scopes(tmp_path, monkeypatch):
    """The shared budget memoizes successful roots through workspace seeding."""
    declared = tmp_path / "workflow"
    declared.mkdir()
    (declared / "step.cwl").write_text("class: CommandLineTool")
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "inputs:\n"
        "  directories: [workflow]\n"
        "workflow:\n"
        "  type: serial\n"
        "  specification: {steps: []}\n"
        "  directories: [workflow, workflow]\n"
    )
    real_scandir = os.scandir
    traversals = 0

    def counting_scandir(path):
        nonlocal traversals
        if os.path.normcase(str(path)) == os.path.normcase(str(declared)):
            traversals += 1
        return real_scandir(path)

    monkeypatch.setattr(specification_paths.os, "scandir", counting_scandir)

    members, _raw, _legacy = gather_workspace_seed_members(str(specification))

    assert set(members) == {"reana.yaml", "workflow/step.cwl"}
    assert traversals == 1


def test_empty_repeated_directory_is_still_rejected(tmp_path):
    """A root is memoized only after a successful non-empty traversal."""
    (tmp_path / "empty").mkdir()
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "workflow:\n"
        "  type: serial\n"
        "  specification: {steps: []}\n"
        "  directories: [empty, empty]\n"
    )

    with pytest.raises(REANAValidationError, match="contains no regular files"):
        gather_validation_members(str(specification))


def test_raw_specification_is_bounded_before_yaml_parsing(tmp_path, monkeypatch):
    """An oversized canonical specification is rejected before PyYAML sees it."""
    specification = tmp_path / "reana.yaml"
    specification.write_text("workflow: {type: serial}\n")
    monkeypatch.setattr(specification_paths, "SPECIFICATION_BUNDLE_MAX_BYTES", 8)

    def unexpected_yaml_load(contents):
        pytest.fail("oversized YAML reached the parser")

    monkeypatch.setattr(specification_paths.yaml, "safe_load", unexpected_yaml_load)

    with pytest.raises(REANAValidationError, match="too large"):
        specification_paths.load_raw_reana_spec(str(specification))


def test_validation_scope_can_resolve_from_an_immutable_spec_copy(tmp_path):
    """A copied canonical spec can select sources from its original directory."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "Snakefile").write_text("rule all: input: []")
    specification = source / "reana.yaml"
    specification.write_text("workflow:\n  type: snakemake\n  file: Snakefile\n")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    copied_specification = snapshot / "reana.yaml"
    copied_specification.write_bytes(specification.read_bytes())

    members, _raw, _legacy = gather_validation_members(
        str(copied_specification), source_base_directory=str(source)
    )

    assert members["reana.yaml"] == str(copied_specification)
    assert members["Snakefile"] == str(source / "Snakefile")


def test_parameter_file_forms_conflict():
    """New and legacy parameter-file references are mutually exclusive."""
    specification = {
        "workflow": {
            "type": "snakemake",
            "parameters": {"file": "new.yaml"},
        },
        "inputs": {"parameters": {"input": "old.yaml"}},
    }
    with pytest.raises(REANAValidationError, match="either"):
        workflow_parameter_file(specification)


def test_input_is_ordinary_parameter_for_serial():
    """Serial input parameters named input are not interpreted as paths."""
    assert workflow_parameter_file(
        {
            "workflow": {"type": "serial"},
            "inputs": {"parameters": {"input": "ordinary value"}},
        }
    ) == (None, False)


def test_workflow_parameters_restricted_to_file_based_engines():
    """The new external parameter-file source is CWL/Snakemake-only."""
    with pytest.raises(REANAValidationError, match="only for CWL"):
        workflow_parameter_file(
            {
                "workflow": {
                    "type": "yadage",
                    "parameters": {"file": "params.yaml"},
                }
            }
        )


def test_declared_directory_rejects_symlink(tmp_path):
    """Directory traversal never follows an in-tree symbolic link."""
    specification = _project(tmp_path)
    (tmp_path / "rules" / "link.smk").symlink_to(tmp_path / "params.yaml")
    with pytest.raises(REANAValidationError, match="Only regular|Symbolic"):
        gather_validation_members(str(specification))


def test_declared_directory_must_contain_a_regular_file(tmp_path):
    """Empty directories cannot be represented by the regular-file ZIP contract."""
    (tmp_path / "empty").mkdir()
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "workflow:\n"
        "  type: serial\n"
        "  directories: [empty]\n"
        "  specification: {steps: []}\n"
    )
    with pytest.raises(REANAValidationError, match="contains no regular files"):
        gather_validation_members(str(specification))


def test_declared_directory_surfaces_walk_error(tmp_path, monkeypatch):
    """An unreadable declared subtree cannot be silently omitted."""
    specification = _project(tmp_path)
    original_scandir = os.scandir

    def _failing_scandir(path):
        if os.fspath(path).endswith("rules"):
            raise PermissionError("permission denied")
        return original_scandir(path)

    monkeypatch.setattr(specification_paths.os, "scandir", _failing_scandir)

    with pytest.raises(
        REANAValidationError,
        match="Could not read declared directory.*permission denied",
    ):
        gather_validation_members(str(specification))


def test_cwl_workflow_fragment_selects_base_document(tmp_path):
    """CWL URI fragments do not become part of the bundle filesystem path."""
    (tmp_path / "tools.cwl").write_text("$graph: []")
    specification = tmp_path / "reana.yaml"
    specification.write_text(
        "workflow:\n  type: cwl\n  file: tools.cwl#selected-tool\n"
    )
    members, _raw, _legacy = gather_validation_members(str(specification))
    assert set(members) == {"reana.yaml", "tools.cwl"}


@pytest.mark.parametrize(
    "body",
    [
        "workflow: [serial]\n",
        "workflow: serial\n",
        "workflow:\n  type: snakemake\n  parameters: [params.yaml]\n",
        "inputs: [input.csv]\nworkflow: {type: serial}\n",
        "inputs:\n  parameters: [params.yaml]\nworkflow: {type: snakemake}\n",
        "workflow:\n  type: serial\n  files: Snakefile\n",
        "workflow:\n  type: serial\n  directories: rules\n",
        "workflow:\n  type: serial\n  file: [Snakefile]\n",
        "workflow: [\n",
        "- workflow\n- inputs\n",
    ],
)
def test_untrustworthy_shapes_have_a_distinct_scope_error(tmp_path, body):
    """Clients may forward only shape/load failures for server-side reporting."""
    specification = tmp_path / "reana.yaml"
    specification.write_text(body)
    with pytest.raises(REANASpecificationScopeError):
        gather_validation_members(str(specification))


def test_unsafe_path_is_not_a_scope_discovery_error(tmp_path):
    """Containment failures must never be downgraded to canonical-only uploads."""
    specification = tmp_path / "reana.yaml"
    specification.write_text("workflow:\n  type: serial\n  files: [../secret]\n")
    with pytest.raises(REANAValidationError) as exc_info:
        gather_validation_members(str(specification))
    assert not isinstance(exc_info.value, REANASpecificationScopeError)


def test_descriptor_open_rejects_swapped_ancestor(tmp_path):
    """A directory replaced after discovery cannot redirect the later open."""
    workspace = tmp_path / "workspace"
    (workspace / "defs").mkdir(parents=True)
    (workspace / "defs" / "Snakefile").write_text("ORIGINAL")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Snakefile").write_text("OUTSIDE")

    (workspace / "defs").rename(workspace / "defs-original")
    (workspace / "defs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(REANAValidationError, match="securely open"):
        open_regular_file_beneath(
            str(workspace), "defs/Snakefile", "validation snapshot"
        )


def test_descriptor_open_remains_anchored_during_ancestor_swap(tmp_path):
    """An already opened file descriptor remains bound to the checked inode."""
    workspace = tmp_path / "workspace"
    (workspace / "defs").mkdir(parents=True)
    (workspace / "defs" / "Snakefile").write_text("ORIGINAL")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Snakefile").write_text("OUTSIDE")

    descriptor = open_regular_file_beneath(
        str(workspace), "defs/Snakefile", "validation snapshot"
    )
    (workspace / "defs").rename(workspace / "defs-original")
    (workspace / "defs").symlink_to(outside, target_is_directory=True)
    with os.fdopen(descriptor, encoding="utf-8") as source:
        assert source.read() == "ORIGINAL"


def test_descriptor_open_accepts_symlinked_trusted_base(tmp_path):
    """Trusted root symlinks are resolved before descendants are constrained."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "Snakefile").write_text("ORIGINAL")
    trusted_alias = tmp_path / "trusted-alias"
    trusted_alias.symlink_to(workspace, target_is_directory=True)

    descriptor = open_regular_file_beneath(
        str(trusted_alias), "Snakefile", "validation snapshot"
    )

    with os.fdopen(descriptor, encoding="utf-8") as source:
        assert source.read() == "ORIGINAL"


def test_compatibility_open_reports_changed_inode(tmp_path, monkeypatch):
    """The compatibility opener distinguishes replacement from declarations."""
    source = tmp_path / "Snakefile"
    source.write_text("ORIGINAL")
    real_stat = os.stat

    def changed_stat(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        values = list(result)
        values[1] += 1
        return os.stat_result(values)

    monkeypatch.setattr(os, "supports_dir_fd", set())
    monkeypatch.setattr(os, "stat", changed_stat)

    with pytest.raises(REANASpecificationPathError) as exc_info:
        open_regular_file_beneath(str(tmp_path), "Snakefile", "workflow.file")

    assert exc_info.value.reason == "changed"


def test_declared_directory_has_a_bounded_breadth(tmp_path, monkeypatch):
    """A broad directory stops discovery even when it contains few files."""
    declared = tmp_path / "declared"
    declared.mkdir()
    for index in range(3):
        (declared / str(index)).mkdir()
    (declared / "0" / "Snakefile").write_text("")
    specification = tmp_path / "reana.yaml"
    specification.write_text("workflow:\n  type: serial\n  directories: [declared]\n")
    monkeypatch.setattr(specification_paths, "SPECIFICATION_BUNDLE_MAX_DIRECTORIES", 2)

    with pytest.raises(REANAValidationError, match="too many directories"):
        gather_validation_members(str(specification))


def test_scope_depth_is_bounded(tmp_path, monkeypatch):
    """Declared paths over the fixed component limit are rejected early."""
    monkeypatch.setattr(specification_paths, "SPECIFICATION_BUNDLE_MAX_DEPTH", 2)
    with pytest.raises(REANAValidationError, match="maximum depth"):
        specification_paths._normalise_relative_path("one/two/three", "workflow.files")


def test_declared_path_has_a_bounded_encoded_length(tmp_path, monkeypatch):
    """Archive metadata cannot grow without a corresponding path-length bound."""
    monkeypatch.setattr(specification_paths, "SPECIFICATION_BUNDLE_MAX_PATH_BYTES", 8)
    with pytest.raises(REANAValidationError, match="encoded bytes"):
        open_regular_file_beneath(str(tmp_path), "long-name", "workflow.files")


def test_missing_declared_path_exposes_structured_identity(tmp_path):
    """Callers never need to recover a declared filename from exception text."""
    path = "missing: source/Snakefile"

    with pytest.raises(REANASpecificationPathError) as exc_info:
        specification_paths._contained_regular_file(
            str(tmp_path), path, "workflow.file"
        )

    assert str(exc_info.value) == (
        "Declared path does not exist in workflow.file: " "missing: source/Snakefile"
    )
    assert exc_info.value.field == "workflow.file"
    assert exc_info.value.path == path
    assert exc_info.value.reason == "missing"


@pytest.mark.parametrize(
    "path,reason,max_depth,max_bytes",
    [
        ("../outside", "unsafe", 64, 4096),
        ("one/two/three", "max_depth", 2, 4096),
        ("long-name", "max_length", 64, 8),
    ],
)
def test_declared_path_validation_exposes_stable_reason(
    tmp_path, monkeypatch, path, reason, max_depth, max_bytes
):
    """Containment limits expose stable reason codes and declaration fields."""
    monkeypatch.setattr(
        specification_paths, "SPECIFICATION_BUNDLE_MAX_DEPTH", max_depth
    )
    monkeypatch.setattr(
        specification_paths, "SPECIFICATION_BUNDLE_MAX_PATH_BYTES", max_bytes
    )

    with pytest.raises(REANASpecificationPathError) as exc_info:
        specification_paths._normalise_relative_path(path, "workflow.files")

    assert exc_info.value.field == "workflow.files"
    assert exc_info.value.path == path
    assert exc_info.value.reason == reason


def test_declared_path_type_and_symlink_expose_stable_reasons(tmp_path):
    """Filesystem object failures distinguish links from wrong object types."""
    directory = tmp_path / "directory"
    directory.mkdir()
    link = tmp_path / "link"
    link.symlink_to(directory, target_is_directory=True)

    with pytest.raises(REANASpecificationPathError) as directory_error:
        specification_paths._contained_regular_file(
            str(tmp_path), "directory", "workflow.file"
        )
    with pytest.raises(REANASpecificationPathError) as link_error:
        specification_paths._contained_regular_file(
            str(tmp_path), "link", "workflow.file"
        )

    assert directory_error.value.reason == "wrong_type"
    assert link_error.value.reason == "symlink"
