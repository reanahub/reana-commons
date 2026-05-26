# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2022, 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons compute backend validation."""

from typing import Dict, List, Optional

from reana_commons.errors import REANAValidationError


def workflow_uses_kubernetes(reana_yaml: Dict) -> bool:
    """Check if any step in the workflow runs on Kubernetes.

    Steps that do not declare a compute backend default to Kubernetes.
    Hybrid workflows (some steps on Kubernetes, some on HTCondor/Slurm) also
    return True.
    """
    workflow = reana_yaml.get("workflow", {})
    workflow_type = workflow.get("type")
    spec = workflow.get("specification", {})

    if workflow_type == "serial":
        return _serial_uses_kubernetes(spec)
    if workflow_type == "snakemake":
        return _snakemake_uses_kubernetes(spec)
    if workflow_type == "yadage":
        return _yadage_uses_kubernetes(spec.get("stages", []))
    if workflow_type == "cwl":
        graph = spec.get("$graph", spec)
        return _cwl_uses_kubernetes(graph)
    return True  # unknown type: conservative default


def _serial_uses_kubernetes(spec: Dict) -> bool:
    steps = spec.get("steps", [])
    return any(
        step.get("compute_backend", "kubernetes") == "kubernetes" for step in steps
    )


def _snakemake_uses_kubernetes(spec: Dict) -> bool:
    return _serial_uses_kubernetes(spec)


def _yadage_uses_kubernetes(stages: List[Dict]) -> bool:
    for stage in stages:
        scheduler = stage.get("scheduler", {})
        if "workflow" in scheduler:
            if _yadage_uses_kubernetes(scheduler["workflow"].get("stages", [])):
                return True
        else:
            resources = (
                scheduler.get("step", {}).get("environment", {}).get("resources", [])
            )
            backend = next(
                (r["compute_backend"] for r in resources if "compute_backend" in r),
                "kubernetes",
            )
            if backend == "kubernetes":
                return True
    return False


def _cwl_uses_kubernetes(workflow) -> bool:
    def _check(wf: Dict) -> bool:
        for step in wf.get("steps", []):
            hints = step.get("hints", [])
            reana_hints = next((h for h in hints if h.get("class") == "reana"), {})
            if reana_hints.get("compute_backend", "kubernetes") == "kubernetes":
                return True
        return False

    if isinstance(workflow, dict):
        return _check(workflow)
    if isinstance(workflow, list):
        return any(_check(wf) for wf in workflow)
    return True


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
        workflow_steps = workflow.get("specification", {}).get("$graph", workflow)
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
                    backend = next(
                        (
                            resource["compute_backend"]
                            for resource in environment.get("resources", [])
                            if "compute_backend" in resource
                        ),
                        None,
                    )
                    if backend and backend not in self.supported_backends:
                        self.raise_error(backend, stage["name"])

        return parse_stages(self.workflow_steps)


class ComputeBackendValidatorCWL(ComputeBackendValidatorBase):
    """REANA CWL workflow compute backend validation."""

    def validate(self) -> None:
        """Validate compute backends in REANA CWL workflow."""

        def _get_reana_hints(hints: List[Dict]) -> Dict:
            for hint in hints:
                if hint.get("class") == "reana":
                    return hint
            return {}

        def _validate_compute_backends(workflow: Dict) -> None:
            """Validate compute backends in REANA CWL workflow steps."""
            steps = workflow.get("steps", [])
            for step in steps:
                hints = step.get("hints", [])
                reana_hints = _get_reana_hints(hints)
                backend = reana_hints.get("compute_backend")
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
