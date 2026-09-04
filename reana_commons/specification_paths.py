# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Select filesystem members declared by a raw REANA specification.

The functions in this module define the authoritative boundary between workflow
definition sources (which are loaded during validation) and input datasets
(which are seeded only after validation).  Callers receive regular files rooted
at the directory containing the selected REANA specification; no declaration is
allowed to escape that directory or traverse a symbolic link.
"""

import errno
import os
import posixpath
import stat
from typing import Dict, Optional, Set, Tuple

import yaml

from reana_commons.errors import (
    REANASpecificationPathError,
    REANASpecificationScopeError,
    REANAValidationError,
)

CANONICAL_REANA_SPECIFICATION = "reana.yaml"
PARAMETER_FILE_WORKFLOW_TYPES = frozenset(("cwl", "snakemake"))
SPECIFICATION_BUNDLE_MAX_FILES = int(os.getenv("REANA_SPEC_BUNDLE_MAX_FILES", "1000"))
SPECIFICATION_BUNDLE_MAX_BYTES = int(
    os.getenv("REANA_SPEC_BUNDLE_MAX_BYTES", str(100 * 1024 * 1024))
)
SPECIFICATION_BUNDLE_MAX_PATH_BYTES = int(
    os.getenv("REANA_SPEC_BUNDLE_MAX_PATH_BYTES", "4096")
)
SPECIFICATION_BUNDLE_MAX_DIRECTORIES = 2000
SPECIFICATION_BUNDLE_MAX_DEPTH = 64


class _ScopeBudget:
    """Track unique files and directory prefixes in one selected scope."""

    def __init__(
        self,
        max_files: Optional[int] = None,
        max_directories: Optional[int] = None,
        max_depth: Optional[int] = None,
    ):
        """Create an empty scope budget with explicit resource limits."""
        self.max_files = (
            SPECIFICATION_BUNDLE_MAX_FILES if max_files is None else max_files
        )
        self.max_directories = (
            SPECIFICATION_BUNDLE_MAX_DIRECTORIES
            if max_directories is None
            else max_directories
        )
        self.max_depth = (
            SPECIFICATION_BUNDLE_MAX_DEPTH if max_depth is None else max_depth
        )
        self.files: Set[str] = set()
        self.directories: Set[str] = set()
        self.traversed_directory_roots: Set[str] = set()

    def _check_depth(self, relative_path: str, field: str) -> None:
        """Reject relative paths exceeding the component-depth contract."""
        depth = len(relative_path.split("/"))
        if depth > self.max_depth:
            raise REANASpecificationPathError(
                "Path exceeds the maximum depth of {} components: {}".format(
                    self.max_depth, relative_path
                ),
                field,
                relative_path,
                "max_depth",
            )

    def add_directory(self, relative_directory: str, field: str) -> None:
        """Account for a directory and each of its relative parent prefixes."""
        self._check_depth(relative_directory, field)
        components = relative_directory.split("/")
        for index in range(1, len(components) + 1):
            directory = "/".join(components[:index])
            if directory in self.directories:
                continue
            if len(self.directories) >= self.max_directories:
                raise REANAValidationError(
                    "Specification scope has too many directories "
                    "(maximum is {}).".format(self.max_directories)
                )
            self.directories.add(directory)

    def add_file(self, relative_path: str, field: str) -> None:
        """Account for a unique file and all of its parent directories."""
        self._check_depth(relative_path, field)
        parent = posixpath.dirname(relative_path)
        if parent:
            self.add_directory(parent, field)
        if relative_path in self.files:
            return
        if len(self.files) >= self.max_files:
            raise REANAValidationError(
                "Specification scope has too many files (maximum is {}).".format(
                    self.max_files
                )
            )
        self.files.add(relative_path)


def _directory_open_flags() -> int:
    """Return flags for opening a pinned directory without following links."""
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def _regular_file_open_flags() -> int:
    """Return flags for opening a regular file without following links."""
    return (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def open_regular_file_beneath(
    base_directory: str, relative_path: str, field: str
) -> int:
    """Open a contained regular file through pinned directory descriptors.

    The trusted base directory is pinned in one open and every untrusted
    component beneath it is opened with ``O_NOFOLLOW``. The returned descriptor
    therefore remains bound to the checked inode even if another writer renames
    or replaces an ancestor while the caller reads it.

    :param base_directory: Trusted lexical root for ``relative_path``.
    :param relative_path: Normalized POSIX path relative to ``base_directory``.
    :param field: User-facing declaration name for errors.
    :returns: Owned read-only descriptor for a regular file.
    :raises REANAValidationError: If any component is unsafe or changes type.
    """
    relative_path = _normalise_relative_path(relative_path, field)
    base_directory = os.path.realpath(base_directory)
    if os.open not in os.supports_dir_fd or not hasattr(os, "O_NOFOLLOW"):
        candidate = os.path.join(base_directory, *relative_path.split("/"))
        _contained_regular_file(base_directory, relative_path, field)
        descriptor = os.open(candidate, os.O_RDONLY)
        try:
            opened = os.fstat(descriptor)
            current = os.stat(candidate, follow_symlinks=False)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != current.st_dev
                or opened.st_ino != current.st_ino
            ):
                raise REANASpecificationPathError(
                    "Declared path changed while opening in {}: {}".format(
                        field, relative_path
                    ),
                    field,
                    relative_path,
                    "changed",
                )
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    relative_components = relative_path.split("/")
    directory_flags = _directory_open_flags()
    file_flags = _regular_file_open_flags()

    descriptor = None
    try:
        # The caller-provided root is trusted and may itself be reached through
        # a trusted symlink (for example /var on macOS). Pin it in one open,
        # then refuse links in every untrusted component beneath that root.
        descriptor = os.open(
            base_directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
        )
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise REANAValidationError(
                "The trusted source root is not a directory: {}".format(base_directory)
            )
        for component in relative_components[:-1]:
            next_descriptor = os.open(
                component,
                directory_flags,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        file_descriptor = os.open(
            relative_components[-1],
            file_flags,
            dir_fd=descriptor,
        )
        mode = os.fstat(file_descriptor).st_mode
        if not stat.S_ISREG(mode):
            os.close(file_descriptor)
            raise REANASpecificationPathError(
                "Declared path is not a regular file in {}: {}".format(
                    field, relative_path
                ),
                field,
                relative_path,
                "wrong_type",
            )
        return file_descriptor
    except REANAValidationError:
        raise
    except (OSError, TypeError, NotImplementedError) as exc:
        reason = "unreadable"
        if isinstance(exc, OSError):
            if exc.errno == errno.ENOENT:
                reason = "missing"
            elif exc.errno == errno.ELOOP:
                reason = "symlink"
            elif exc.errno == errno.ENOTDIR:
                reason = "wrong_type"
        raise REANASpecificationPathError(
            "Could not securely open declared path in {}: {} ({})".format(
                field, relative_path, exc
            ),
            field,
            relative_path,
            reason,
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def load_raw_reana_spec(specification_path: str) -> Dict:
    """Load a raw REANA specification and require a non-empty mapping."""
    try:
        specification_path = os.path.abspath(specification_path)
        descriptor = open_regular_file_beneath(
            os.path.dirname(specification_path),
            os.path.basename(specification_path),
            "REANA specification",
        )
        with os.fdopen(descriptor, "rb") as specification:
            if (
                os.fstat(specification.fileno()).st_size
                > SPECIFICATION_BUNDLE_MAX_BYTES
            ):
                raise REANAValidationError(
                    "The REANA specification is too large (maximum is {} bytes).".format(
                        SPECIFICATION_BUNDLE_MAX_BYTES
                    )
                )
            contents = specification.read(SPECIFICATION_BUNDLE_MAX_BYTES + 1)
        if len(contents) > SPECIFICATION_BUNDLE_MAX_BYTES:
            raise REANAValidationError(
                "The REANA specification is too large (maximum is {} bytes).".format(
                    SPECIFICATION_BUNDLE_MAX_BYTES
                )
            )
        value = yaml.safe_load(contents)
    except (OSError, REANAValidationError) as exc:
        raise REANAValidationError(
            "Could not load the REANA specification: {}".format(exc)
        )
    except yaml.YAMLError as exc:
        raise REANASpecificationScopeError(
            "Could not load the REANA specification: {}".format(exc)
        )
    if not isinstance(value, dict) or not value:
        raise REANASpecificationScopeError(
            "The REANA specification must be a non-empty YAML mapping."
        )
    return value


def workflow_parameter_file(reana_specification: Dict) -> Tuple[Optional[str], bool]:
    """Return ``(path, legacy)`` for an external workflow parameter file.

    ``inputs.parameters.input`` is interpreted as a file reference only for CWL
    and Snakemake.  For other workflow types it remains an ordinary runtime
    parameter named ``input``.
    """
    workflow = reana_specification.get("workflow") or {}
    inputs = reana_specification.get("inputs") or {}
    if not isinstance(workflow, dict) or not isinstance(inputs, dict):
        raise REANASpecificationScopeError("workflow and inputs must be mappings.")

    workflow_type = workflow.get("type")
    parameters = workflow.get("parameters") or {}
    if not isinstance(parameters, dict):
        raise REANASpecificationScopeError("workflow.parameters must be a mapping.")
    new_path = parameters.get("file")

    input_parameters = inputs.get("parameters") or {}
    if not isinstance(input_parameters, dict):
        raise REANASpecificationScopeError("inputs.parameters must be a mapping.")
    legacy_path = (
        input_parameters.get("input")
        if workflow_type in PARAMETER_FILE_WORKFLOW_TYPES
        else None
    )

    if new_path is not None and workflow_type not in PARAMETER_FILE_WORKFLOW_TYPES:
        raise REANAValidationError(
            "workflow.parameters.file is supported only for CWL and Snakemake "
            "workflows."
        )
    if new_path is not None and legacy_path is not None:
        raise REANAValidationError(
            "Use either workflow.parameters.file or inputs.parameters.input, "
            "not both."
        )
    if new_path is not None and not isinstance(new_path, str):
        raise REANASpecificationScopeError("workflow.parameters.file must be a string.")
    if legacy_path is not None and not isinstance(legacy_path, str):
        raise REANASpecificationScopeError("inputs.parameters.input must be a string.")
    return (
        (new_path, False)
        if new_path is not None
        else (legacy_path, legacy_path is not None)
    )


def _normalise_relative_path(path: str, field: str) -> str:
    """Validate a declared path and return its normalized POSIX spelling."""
    if not isinstance(path, str) or not path:
        raise REANASpecificationPathError(
            "{} must contain non-empty paths.".format(field),
            field,
            path,
            "wrong_type",
        )
    if len(path.encode("utf-8")) > SPECIFICATION_BUNDLE_MAX_PATH_BYTES:
        raise REANASpecificationPathError(
            "Path in {} exceeds {} encoded bytes.".format(
                field, SPECIFICATION_BUNDLE_MAX_PATH_BYTES
            ),
            field,
            path,
            "max_length",
        )
    if (
        "\x00" in path
        or "\\" in path
        or path.startswith("/")
        or (len(path) >= 2 and path[1] == ":")
    ):
        raise REANASpecificationPathError(
            "Unsafe path in {}: {}".format(field, path), field, path, "unsafe"
        )
    normalized = posixpath.normpath(path)
    parts = normalized.split("/")
    if (
        normalized in ("", ".", "..")
        or normalized != path.rstrip("/")
        or any(part in ("", ".", "..") for part in parts)
    ):
        raise REANASpecificationPathError(
            "Unsafe path in {}: {}".format(field, path), field, path, "unsafe"
        )
    if len(parts) > SPECIFICATION_BUNDLE_MAX_DEPTH:
        raise REANASpecificationPathError(
            "Path in {} exceeds the maximum depth of {} components: {}".format(
                field, SPECIFICATION_BUNDLE_MAX_DEPTH, path
            ),
            field,
            path,
            "max_depth",
        )
    return normalized


def _contained_regular_file(base_directory: str, relative_path: str, field: str) -> str:
    """Return an absolute regular-file path without following symbolic links."""
    current = base_directory
    parts = relative_path.split("/")
    for index, part in enumerate(parts):
        current = os.path.join(current, part)
        try:
            mode = os.lstat(current).st_mode
        except OSError:
            raise REANASpecificationPathError(
                "Declared path does not exist in {}: {}".format(field, relative_path),
                field,
                relative_path,
                "missing",
            )
        if stat.S_ISLNK(mode):
            raise REANASpecificationPathError(
                "Symbolic links are not allowed in {}: {}".format(field, relative_path),
                field,
                relative_path,
                "symlink",
            )
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            raise REANASpecificationPathError(
                "Declared path is not a directory in {}: {}".format(
                    field, relative_path
                ),
                field,
                relative_path,
                "wrong_type",
            )
    if not stat.S_ISREG(mode):
        raise REANASpecificationPathError(
            "Declared path is not a regular file in {}: {}".format(
                field, relative_path
            ),
            field,
            relative_path,
            "wrong_type",
        )
    return current


def _add_file(
    members: Dict[str, str],
    base_directory: str,
    declaration: str,
    field: str,
    budget: _ScopeBudget,
    allow_canonical_input: bool = False,
) -> None:
    relative_path = _normalise_relative_path(declaration, field)
    if relative_path == CANONICAL_REANA_SPECIFICATION:
        if allow_canonical_input and field == "inputs.files":
            return
        raise REANASpecificationPathError(
            "{} cannot declare the reserved path {}.".format(
                field, CANONICAL_REANA_SPECIFICATION
            ),
            field,
            relative_path,
            "conflict",
        )
    absolute_path = _contained_regular_file(base_directory, relative_path, field)
    previous = members.get(relative_path)
    if previous is not None and os.path.normcase(previous) != os.path.normcase(
        absolute_path
    ):
        raise REANASpecificationPathError(
            "Conflicting declarations resolve to {}.".format(relative_path),
            field,
            relative_path,
            "conflict",
        )
    budget.add_file(relative_path, field)
    members[relative_path] = absolute_path


def _add_directory(  # noqa: C901
    members: Dict[str, str],
    base_directory: str,
    declaration: str,
    field: str,
    budget: _ScopeBudget,
) -> None:
    relative_directory = _normalise_relative_path(declaration, field)
    if relative_directory in budget.traversed_directory_roots:
        return
    absolute_directory = os.path.join(base_directory, *relative_directory.split("/"))
    try:
        mode = os.lstat(absolute_directory).st_mode
    except OSError:
        raise REANASpecificationPathError(
            "Declared directory does not exist in {}: {}".format(
                field, relative_directory
            ),
            field,
            relative_directory,
            "missing",
        )
    if stat.S_ISLNK(mode):
        raise REANASpecificationPathError(
            "Declared path is not a regular directory in {}: {}".format(
                field, relative_directory
            ),
            field,
            relative_directory,
            "symlink",
        )
    if not stat.S_ISDIR(mode):
        raise REANASpecificationPathError(
            "Declared path is not a regular directory in {}: {}".format(
                field, relative_directory
            ),
            field,
            relative_directory,
            "wrong_type",
        )

    budget.add_directory(relative_directory, field)
    has_regular_file = False

    def _raise_walk_error(error):
        raise REANAValidationError(
            "Could not read declared directory in {}: {} ({})".format(
                field, relative_directory, error
            )
        )

    pending = [(absolute_directory, relative_directory)]
    while pending:
        root, relative_root = pending.pop()
        directories = []
        files = []
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    relative_entry = posixpath.join(relative_root, entry.name)
                    try:
                        if entry.is_symlink():
                            raise REANASpecificationPathError(
                                "Symbolic links are not allowed in {}: {}".format(
                                    field, relative_entry
                                ),
                                field,
                                relative_entry,
                                "symlink",
                            )
                        if entry.is_dir(follow_symlinks=False):
                            budget.add_directory(relative_entry, field)
                            directories.append((entry.path, relative_entry))
                        elif entry.is_file(follow_symlinks=False):
                            has_regular_file = True
                            budget.add_file(relative_entry, field)
                            files.append(relative_entry)
                        else:
                            raise REANASpecificationPathError(
                                "Only regular files and directories are allowed "
                                "in {}: {}".format(field, relative_entry),
                                field,
                                relative_entry,
                                "wrong_type",
                            )
                    except OSError as exc:
                        _raise_walk_error(exc)
        except REANAValidationError:
            raise
        except OSError as exc:
            _raise_walk_error(exc)
        for file_relative in sorted(files):
            _add_file(members, base_directory, file_relative, field, budget)
        pending.extend(reversed(sorted(directories, key=lambda item: item[1])))
    if not has_regular_file:
        raise REANAValidationError(
            "Declared directory contains no regular files in {}: {}".format(
                field, relative_directory
            )
        )
    budget.traversed_directory_roots.add(relative_directory)


def _add_declared_paths(
    members: Dict[str, str],
    base_directory: str,
    section: Dict,
    files_key: str,
    directories_key: Optional[str],
    field_prefix: str,
    budget: _ScopeBudget,
    allow_canonical_input: bool = False,
) -> None:
    files = section.get(files_key) or []
    if not isinstance(files, list):
        raise REANASpecificationScopeError(
            "{}.{} must be a list.".format(field_prefix, files_key)
        )
    directories = []
    if directories_key is not None:
        directories = section.get(directories_key) or []
        if not isinstance(directories, list):
            raise REANASpecificationScopeError(
                "{}.{} must be a list.".format(field_prefix, directories_key)
            )
    if len(files) + len(directories) > budget.max_files:
        raise REANAValidationError(
            "Specification scope has too many declared paths in {} "
            "(maximum is {}).".format(field_prefix, budget.max_files)
        )

    for path in files:
        if not isinstance(path, str):
            raise REANASpecificationScopeError(
                "{}.{} must contain paths expressed as strings.".format(
                    field_prefix, files_key
                )
            )
        _add_file(
            members,
            base_directory,
            path,
            "{}.{}".format(field_prefix, files_key),
            budget,
            allow_canonical_input=allow_canonical_input,
        )

    if directories_key is None:
        return
    for path in directories:
        if not isinstance(path, str):
            raise REANASpecificationScopeError(
                "{}.{} must contain paths expressed as strings.".format(
                    field_prefix, directories_key
                )
            )
        _add_directory(
            members,
            base_directory,
            path,
            "{}.{}".format(field_prefix, directories_key),
            budget,
        )


def uses_legacy_validation_scope(reana_specification: Dict) -> bool:
    """Return whether an external workflow needs the legacy input scope."""
    workflow = reana_specification.get("workflow") or {}
    inputs = reana_specification.get("inputs") or {}
    return (
        isinstance(workflow, dict)
        and isinstance(inputs, dict)
        and workflow.get("file") is not None
        and "files" not in workflow
        and "directories" not in workflow
        and bool(inputs.get("files") or inputs.get("directories"))
    )


def _gather_validation_members(
    specification_path: str,
    source_base_directory: Optional[str] = None,
    selected_specification_name: Optional[str] = None,
) -> Tuple[Dict[str, str], Dict, bool, _ScopeBudget]:
    """Gather validation members and return their shared resource budget."""
    specification_path = os.path.abspath(specification_path)
    base_directory = os.path.abspath(
        source_base_directory or os.path.dirname(specification_path)
    )
    selected_specification_name = selected_specification_name or os.path.basename(
        specification_path
    )
    allow_canonical_input = selected_specification_name == CANONICAL_REANA_SPECIFICATION
    specification_mode = os.lstat(specification_path).st_mode
    if stat.S_ISLNK(specification_mode) or not stat.S_ISREG(specification_mode):
        raise REANAValidationError(
            "The selected REANA specification must be a regular file."
        )

    reana_specification = load_raw_reana_spec(specification_path)
    workflow = reana_specification.get("workflow") or {}
    if not isinstance(workflow, dict):
        raise REANASpecificationScopeError("workflow must be a mapping.")

    budget = _ScopeBudget()
    budget.add_file(CANONICAL_REANA_SPECIFICATION, "REANA specification")
    members = {CANONICAL_REANA_SPECIFICATION: specification_path}
    workflow_file = workflow.get("file")
    if workflow_file is not None:
        if not isinstance(workflow_file, str):
            raise REANASpecificationScopeError("workflow.file must be a string.")
        workflow_file_path = workflow_file
        if workflow.get("type") == "cwl":
            workflow_file_path = workflow_file.partition("#")[0]
            if not workflow_file_path:
                raise REANAValidationError(
                    "workflow.file must identify a local CWL document before its "
                    "fragment."
                )
        _add_file(
            members,
            base_directory,
            workflow_file_path,
            "workflow.file",
            budget,
        )
    _add_declared_paths(
        members,
        base_directory,
        workflow,
        "files",
        "directories",
        "workflow",
        budget,
    )

    if uses_legacy_validation_scope(reana_specification):
        inputs = reana_specification.get("inputs") or {}
        _add_declared_paths(
            members,
            base_directory,
            inputs,
            "files",
            "directories",
            "inputs",
            budget,
            allow_canonical_input=allow_canonical_input,
        )

    parameter_file, legacy = workflow_parameter_file(reana_specification)
    if parameter_file is not None:
        _add_file(
            members,
            base_directory,
            parameter_file,
            ("inputs.parameters.input" if legacy else "workflow.parameters.file"),
            budget,
        )
    return members, reana_specification, legacy, budget


def gather_validation_members(
    specification_path: str,
    source_base_directory: Optional[str] = None,
    selected_specification_name: Optional[str] = None,
) -> Tuple[Dict[str, str], Dict, bool]:
    """Return validation members, the raw specification, and legacy-field use.

    ``source_base_directory`` lets a caller parse an immutable copied
    specification while resolving its declared sources against the directory
    from which that copy was made.

    ``selected_specification_name`` preserves the original selected filename
    when ``specification_path`` points to such an immutable canonical copy.
    """
    members, reana_specification, legacy, _budget = _gather_validation_members(
        specification_path, source_base_directory, selected_specification_name
    )
    return members, reana_specification, legacy


def gather_workspace_seed_members(
    specification_path: str,
) -> Tuple[Dict[str, str], Dict, bool]:
    """Return definition, input, and test files declared for a workspace seed."""
    members, reana_specification, legacy, budget = _gather_validation_members(
        specification_path
    )
    base_directory = os.path.dirname(os.path.abspath(specification_path))
    allow_canonical_input = (
        os.path.basename(os.path.abspath(specification_path))
        == CANONICAL_REANA_SPECIFICATION
    )

    inputs = reana_specification.get("inputs") or {}
    if not isinstance(inputs, dict):
        raise REANAValidationError("inputs must be a mapping.")
    _add_declared_paths(
        members,
        base_directory,
        inputs,
        "files",
        "directories",
        "inputs",
        budget,
        allow_canonical_input=allow_canonical_input,
    )

    tests = reana_specification.get("tests") or {}
    if not isinstance(tests, dict):
        raise REANAValidationError("tests must be a mapping.")
    _add_declared_paths(members, base_directory, tests, "files", None, "tests", budget)
    return members, reana_specification, legacy
