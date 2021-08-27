# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2021 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-Commons workflow engine common utils."""

import os
import base64
import json
import logging
import signal

import click

from reana_commons.api_client import JobControllerAPIClient
from reana_commons.publisher import WorkflowStatusPublisher
from reana_commons.utils import check_connection_to_job_controller


def load_json(ctx, param, value):
    """Load json callback function."""
    json_value = ""
    if value:
        value = str.encode(value[1:])
        json_value = json.loads(base64.standard_b64decode(value).decode())
    return json_value


def load_yadage_operational_options(ctx, param, operational_options):
    """Decode and prepare operational options."""
    operational_options = load_json(ctx, param, operational_options)
    workflow_workspace = ctx.params.get("workflow_workspace")
    toplevel = operational_options.get("toplevel", "")
    if not toplevel.startswith("github:"):
        toplevel = os.path.join(workflow_workspace, toplevel)
    operational_options["toplevel"] = toplevel

    operational_options["initdir"] = os.path.join(
        workflow_workspace, operational_options.get("initdir", "")
    )

    operational_options["initfiles"] = [
        os.path.join(workflow_workspace, initfile)
        for initfile in operational_options.get("initfiles", [])
    ]

    return operational_options


def load_cwl_operational_options(ctx, param, value):
    """Load json and prepare operational options for CWL engine."""
    operational_options = load_json(ctx, param, value)
    res = []
    for option, val in operational_options.items():
        res.extend([option, val])
    return res


workflow_engines = dict(
    cwl=dict(load_operational_options_callback=load_cwl_operational_options),
    serial=dict(load_operational_options_callback=load_json),
    yadage=dict(load_operational_options_callback=load_yadage_operational_options),
    snakemake=dict(load_operational_options_callback=load_json),
)


def create_workflow_engine_command(
    workflow_engine_run_adapter, engine_type, exit_handler=None
):
    """Create Click command to execute REANA workflow engines resiliently.

    :param workflow_engine_run_adapter: A function that executes a workflow by
        implementing and adapter to concrete workflow engines. This function
        will receive as arguments: a publisher instance
        (``reana_commons.publisher.WorkflowStatusPublisher``) to publish workflow
        status and a REANA Job Controller client
        (``reana_commons.api_client.JobControllerAPIClient``) and the rest of parameters
        as keyword arguments coming from the click command.
    :param exit_handler: A Python signal handler to invoke in the event of a
        termination signal. The handler receives as parameters ``singnum``
        (signal number) and ``frame`` (current stack)

    :type workflow_engine_run_adapter: func
    :type exit_handler: func


    Example:
    .. code-block:: python
        def custom_exit_handler(signum, frame):
            close_open_resources()
            notify_component_about_failure()

        def dummy_workflow_engine_run_adapter(
            publisher,
            rjc_api_client,
            workflow_uuid=None,
            **kwargs
        ):
            logging("Running %s ...", workflow_uuid)
            publisher.publish_workflow_status(workflow_uuid, 1)
            rjc_api_client.submit(**job_spec)
            publisher.publish_workflow_status(workflow_uuid, 2)
            logging("Workflow %s finished.", workflow_uuid)

        run_dummy_workflow_engine_command = create_workflow_engine_command(
            dummy_workflow_engine_run_adapter, engine_type="dummy"
        )

    """
    if engine_type not in workflow_engines.keys():
        raise Exception(
            "Unknown workflow engine type {}. "
            "Must be one of {}".format(engine_type, workflow_engines.keys())
        )

    @click.command()
    @click.option("--workflow-uuid", required=True, help="UUID of workflow to be run.")
    @click.option(
        "--workflow-workspace",
        required=True,
        help="Name of workspace in which workflow should run.",
    )
    @click.option(
        "--workflow-json",
        help="JSON representation of workflow object to be run.",
        callback=load_json,
    )
    @click.option(
        "--workflow-file",
        help="Path to the workflow file. This field is used when"
        " no workflow JSON has been passed.",
    )
    @click.option(
        "--workflow-parameters",
        help="JSON representation of parameters received by the workflow.",
        callback=load_json,
    )
    @click.option(
        "--operational-options",
        help="Options to be passed to the workflow engine (i.e. caching).",
        callback=workflow_engines[engine_type]["load_operational_options_callback"],
    )
    def run_workflow_engine_run_command(**kwargs):
        """Click command used to invoke concrete workflow engine adapters."""
        workflow_uuid = kwargs.get("workflow_uuid")
        workflow_workspace = kwargs.get("workflow_workspace")

        def _default_exit_handler(signum, frame):
            """Handle executable exit gracefully."""
            if not publisher:
                raise Exception(
                    "Workflow engine graceful exit requires an instance"
                    "of reana_commons.publisher.WorkflowStatusPublisher"
                )
            try:
                logging.warning(
                    "Termination signal {} received. Workflow interrupted ...".format(
                        signum
                    )
                )
                publisher.publish_workflow_status(
                    workflow_uuid, 3, logs="Workflow exited unexpectedly."
                )
            except Exception:
                logging.error(
                    "Workflow {} could not be stopped gracefully".format(workflow_uuid),
                )

        try:
            signal.signal(signal.SIGTERM, exit_handler or _default_exit_handler)
            publisher = WorkflowStatusPublisher()
            rjc_api_client = JobControllerAPIClient("reana-job-controller")
            check_connection_to_job_controller()
            workflow_engine_run_adapter(publisher, rjc_api_client, **kwargs)
            logging.info(
                "Workflow {} finished. Files available at {}.".format(
                    workflow_uuid, workflow_workspace
                ),
            )
            publisher.close()
        except Exception as e:
            logging.debug(str(e))
            if publisher:
                publisher.publish_workflow_status(
                    workflow_uuid,
                    3,
                    logs="Workflow exited unexpectedly.\n{e}".format(e=e),
                )
            else:
                logging.error(
                    "Workflow {} failed but status "
                    "could not be published causing the workflow to be "
                    "stuck in running status.".format(workflow_uuid),
                )

        finally:
            if publisher:
                publisher.close()

    return run_workflow_engine_run_command
