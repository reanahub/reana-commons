# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons compute backend validation."""

from typing import Dict, List, Optional

from reana_commons.errors import REANAValidationError


def build_compute_backends_validator(
    reana_yaml: Dict, supported_backends: Optional[List[str]]
):
    """Validate compute backends in REANA specification file.

    :param reana_yaml: dictionary which represents REANA specification file.
    :param supported_backends: a list of the supported compute backends.
    """
    workflow = reana_yaml["workflow"]
    workflow_type = workflow["type"]
    if workflow_type == "serial":
        workflow_steps = workflow["specification"]["steps"]
        return ComputeBackendValidatorSerial(
            workflow_steps=workflow_steps, supported_backends=supported_backends
        )
    if workflow_type == "yadage":
        workflow_steps = workflow["specification"]["stages"]
        return ComputeBackendValidatorYadage(
            workflow_steps=workflow_steps, supported_backends=supported_backends
        )
    if workflow_type == "cwl":
        # An unpacked CWL workflow carries its steps directly in the
        # specification; a packed one nests them under ``$graph``. The
        # complexity estimator resolves the two shapes the same way.
        specification = workflow.get("specification", {})
        workflow_steps = specification.get("$graph", specification)
        return ComputeBackendValidatorCWL(
            workflow_steps=workflow_steps, supported_backends=supported_backends
        )
    if workflow_type == "snakemake":
        workflow_steps = workflow["specification"]["steps"]
        return ComputeBackendValidatorSnakemake(
            workflow_steps=workflow_steps, supported_backends=supported_backends
        )


class ComputeBackendValidatorBase:
    """REANA workflow compute backend validation base class."""

    def __init__(
        self,
        workflow_steps: Optional[List[Dict]] = None,
        supported_backends: Optional[List[str]] = [],
    ):
        """Validate compute backends in REANA workflow steps.

        :param workflow_steps: list of dictionaries which represents different steps involved in workflow.
        :param supported_backends: a list of the supported compute backends.
        """
        self.workflow_steps = workflow_steps
        self.supported_backends = supported_backends

    def validate(self) -> None:
        """Validate compute backends in REANA workflow."""
        raise NotImplementedError

    def raise_error(self, compute_backend: str, step_name: str) -> None:
        """Raise validation error."""
        raise REANAValidationError(
            f'Compute backend "{compute_backend}" found in step "{step_name}" is not supported. '
            f'List of supported compute backends: "{", ".join(self.supported_backends)}"'
        )


class ComputeBackendValidatorSerial(ComputeBackendValidatorBase):
    """REANA serial workflow compute backend validation."""

    def validate(self) -> None:
        """Validate compute backends in REANA serial workflow."""
        for step in self.workflow_steps:
            backend = step.get("compute_backend")
            if backend and backend not in self.supported_backends:
                self.raise_error(backend, step.get("name"))


class ComputeBackendValidatorYadage(ComputeBackendValidatorBase):
    """REANA Yadage workflow compute backend validation."""

    def validate(self) -> None:
        """Validate compute backends in REANA Yadage workflow."""

        def parse_stages(stages: Optional[List[Dict]]) -> None:
            """Extract compute backends in Yadage workflow steps."""
            for stage in stages:
                if "workflow" in stage["scheduler"]:
                    nested_stages = stage["scheduler"]["workflow"].get("stages", {})
                    parse_stages(nested_stages)
                else:
                    environment = stage["scheduler"]["step"]["environment"]
                    # Every declaration is validated, not just the first one:
                    # reana-workflow-engine-yadage resolves the effective backend
                    # by iterating all resources with overwrite, so the *last*
                    # declaration is the one that actually runs.
                    backends = [
                        resource["compute_backend"]
                        for resource in environment.get("resources", [])
                        if isinstance(resource, dict) and "compute_backend" in resource
                    ]
                    for backend in backends:
                        if backend and backend not in self.supported_backends:
                            self.raise_error(backend, stage["name"])

        return parse_stages(self.workflow_steps)


class ComputeBackendValidatorCWL(ComputeBackendValidatorBase):
    """REANA CWL workflow compute backend validation."""

    def validate(self) -> None:
        """Validate compute backends in REANA CWL workflow."""

        def _get_declared_backends(hints: List[Dict]) -> List[str]:
            """Return every compute backend declared in a step's hints.

            The canonical REANA representation is a ``class: reana`` hint, but
            reana-workflow-engine-cwl resolves hints by scanning them all and
            taking the first one carrying the key, regardless of its class. All
            declarations are therefore validated, so that no hint can smuggle an
            unsupported backend past validation and into execution.
            """
            return [
                hint["compute_backend"]
                for hint in hints or []
                if isinstance(hint, dict) and "compute_backend" in hint
            ]

        def _validate_compute_backends(workflow: Dict) -> None:
            """Validate compute backends in REANA CWL workflow steps."""
            steps = workflow.get("steps", [])
            for step in steps:
                for backend in _get_declared_backends(step.get("hints", [])):
                    if backend and backend not in self.supported_backends:
                        self.raise_error(backend, step.get("id"))

        workflow = self.workflow_steps
        if isinstance(workflow, dict):
            _validate_compute_backends(workflow)
        elif isinstance(workflow, list):
            for wf in workflow:
                _validate_compute_backends(wf)


class ComputeBackendValidatorSnakemake(ComputeBackendValidatorBase):
    """REANA Snakemake workflow compute backend validation."""

    def validate(self) -> None:
        """Validate compute backends in REANA Snakemake workflow."""
        for idx, step in enumerate(self.workflow_steps):
            backend = step.get("compute_backend")
            if backend and backend not in self.supported_backends:
                step_name = step.get("name", str(idx))
                self.raise_error(backend, step_name)
