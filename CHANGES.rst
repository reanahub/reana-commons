Changes
=======

Version 0.9.4 (UNRELEASED)
--------------------------

- Changes the OpenAPI specification of the ``start_workflow`` endpoint's response to add missing ``run_number`` field.
- Changes validation of REANA specification to expose functions for loading workflow input parameters and workflow specifications.
- Changes CVMFS support to allow users to automatically mount any available repository.
- Fixes the mounting of CVMFS volumes for the REANA deployments that use non-default Kubernetes namespace.

Version 0.9.3 (2023-09-26)
--------------------------

- Adds support for Python 3.12.
- Adds the OpenAPI specification support for ``prune_workspace`` endpoint that allows to delete files that are neither inputs nor outputs from the workspace.
- Adds support for ``tests.files`` in ``reana.yaml`` allowing to specify Gherkin feature files for testing runnable examples.
- Changes the OpenAPI specification to include the ``run_stopped_at`` property in the workflow progress information returned by the workflow list and workflow status endpoints.
- Changes the OpenAPI specification to include the ``maximum_interactive_session_inactivity_period`` value to the ``info`` endpoint.
- Changes the email sending utility to allow configuring authentication and encryption options.
- Changes validation of REANA specification to emit warnings about unknown properties.
- Fixes the verbs used to describe changes to the status of a workflow in order to avoid incorrect grammatical phrases such as ``workflow has been failed``.
- Fixes the loading of Snakemake and CWL workflow specifications when no parameters are specified.
- Fixes the OpenAPI specification of GitLab OAuth endpoint return statuses.
- Fixes container image names to be Podman-compatible.
- Fixes the email sending utility to not send emails when notifications are disabled globally.

Version 0.9.2.1 (2023-07-19)
----------------------------

- Changes ``PyYAML`` dependency version bounds in order to fix installation on Python 3.10+.

Version 0.9.2 (2023-02-10)
--------------------------

- Fixes ``wcmatch`` dependency version specification.

Version 0.9.1 (2023-01-18)
--------------------------

- Changes Kerberos renew container's configuration to log each ticket renewal.

Version 0.9.0 (2022-12-13)
--------------------------

- Adds support for Python 3.11.
- Adds support for Rucio.
- Adds REANA specification validation and loading logic from ``reana-client``.
- Adds common utility functions for managing workspace files.
- Adds OpenAPI specification support for ``launch`` endpoint that allows running workflows from remote sources.
- Adds OpenAPI specification support for ``get_workflow_retention_rules`` endpoint that allows to retrieve the workspace file retention rules of a workflow.
- Adds generation of Kerberos init and renew container's configuration.
- Adds support for Unicode characters inside email body.
- Changes OpenAPI specification to include missing response schema elements and some other small enhancements.
- Changes the Kubernetes Python client to use the ``networking/v1`` API.
- Changes REANA specification loading functionality to allow specifying different working directories.
- Changes REANA specification to allow enabling Kerberos for the whole workflow.
- Changes REANA specification to allow specifying ``retention_days`` for the workflow.
- Changes REANA specification to allow specifying ``slurm_partition`` and ``slurm_time`` for Slurm compute backend jobs.
- Changes the loading of Snakemake specifications to preserve the current working directory.
- Fixes the submission of jobs by stripping potential leading and trailing whitespaces in Docker image names.

Version 0.8.5 (2022-02-23)
--------------------------

- Adds ``retry_count`` parameter to WorkflowSubmissionPublisher.

Version 0.8.4 (2022-02-08)
--------------------------

- Adds new configuration variable to toggle Kubernetes security context. (``K8S_USE_SECURITY_CONTEXT``)
- Changes installation to revert ``Yadage`` dependency versions.

Version 0.8.3 (2022-02-04)
--------------------------

- Changes installation to remove upper version pin on ``kombu``.

Version 0.8.2 (2022-02-01)
--------------------------

- Adds support for Python 3.10.
- Adds workflow name validation utility.
- Changes ``Snakemake`` loaded specification to include compute backends.
- Changes OpenAPI specification with respect to return supported compute backends in ``info`` endpoint.
- Fixes file system usage calculation on CephFS shares in ``get_disk_usage`` utility function.

Version 0.8.1 (2021-12-21)
---------------------------

- Adds OpenAPI specification support for ``kubernetes_job_timeout`` handling.
- Changes OpenAPI specification for cluster health status endpoint.
- Changes Yadage dependencies to allow 0.21.x patchlevel-version updates.
- Changes installation to require Python-3.6 or higher versions.

Version 0.8.0 (2021-11-22)
---------------------------

- Adds ``get_disk_usage`` utility function to calculate disk usage for a directory.
- Adds ``Yadage`` workflow specification loading utilities.
- Adds workspace validation utilities.
- Adds ``Snakemake`` workflow engine integration.
- Adds custom objects API instance to k8s client.
- Adds available worklow engines configuration.
- Adds environment variable to define time between job controller connection checks.
- Adds cluster health status endpoint.
- Adds OpenAPI specifications with respect to user quotas.
- Changes ``workflow-submission`` queue as a priority queue and allows to set the priority number on workflow submission.
- Changes OpenAPI specifications with respect to turning ``workspaces`` endpoint into ``info``.
- Changes publisher logging level on error callback.
- Removes support for Python 2.

Version 0.7.5 (2021-07-02)
--------------------------

- Adds support for glob patterns when listing workflow files.
- Adds support for specifying ``kubernetes_memory_limit`` for Kubernetes compute backend jobs.

Version 0.7.4 (2021-03-17)
--------------------------

- Adds new functions to serialise/deserialise job commands between REANA components.
- Changes ``reana_ready`` function location to REANA-Server.

Version 0.7.3 (2021-02-22)
--------------------------

- Adds new configuration variable to toggle runtime user jobs clean up depending on their statuses. (``REANA_RUNTIME_KUBERNETES_KEEP_ALIVE_JOBS_WITH_STATUSES``)
- Adds central class to instantiate workflow engines with more resilience. (``workflow_engine.create_workflow_engine_command``)

Version 0.7.2 (2021-02-02)
--------------------------

- Adds support for Python 3.9.
- Fixes minor code warnings.
- Fixes a helper function that calculates directory hashes.
- Changes OpenAPI specifications with respect to sign-up form.
- Changes OpenAPI specifications with respect to email confirmation.
- Changes CI system to include Python flake8 checker.

Version 0.7.1 (2020-11-09)
--------------------------

- Adds support for restarting yadage workflows (through ``accept_metadir`` operational option).
- Allows ``htcondor_max_runtime`` and ``htcondor_accounting_group`` to be specified for HTC jobs.
- Adds new field in REANA-Server OpenAPI spec to return server version.
- Changes CI system from Travis to GitHub Actions.

Version 0.7.0 (2020-10-20)
--------------------------

- Adds new utility to send emails.
- Adds centralised validation utility for workflow operational options.
- Adds new configuration variable to set the maximum number of running workflows. (``REANA_MAX_CONCURRENT_BATCH_WORKFLOWS``)
- Adds new configuration variable to set prefix of REANA cluster component names. (``REANA_COMPONENT_PREFIX``)
- Adds new configuration variable for the runtime pod node selector label. (``REANA_RUNTIME_KUBERNETES_NODE_LABEL``)
- Adds new configuration variable to define the Kubernetes namespace in which REANA infrastructure components run. (``REANA_INFRASTRUCTURE_KUBERNETES_NAMESPACE``)
- Adds new configuration variable to define the Kubernetes namespace in which REANA runtime components components run. (``REANA_RUNTIME_KUBERNETES_NAMESPACE``)
- Adds possibility to specify unpacked container images for running jobs.
- Adds support for ``initfiles`` operational option for the Yadage workflow engine.
- Fixes memory leak in Bravado client instantiation.
- Changes CephFS Persistent Volume Claim name. (``REANA_SHARED_PVC_NAME``)
- Changes default logging level to ``INFO``.
- Changes default CVMFS volume list to include LHCb Gaudi related workflows.
- Changes code formatting to respect ``black`` coding style.
- Changes underlying requirements to use Kubernetes Python library version 11.
- Changes underlying requirements to use latest CVMFS CSI driver version.
- Changes documentation to single-page layout.

Version 0.6.1 (2020-05-25)
--------------------------

- Upgrades Kubernetes Python client.

Version 0.6.0 (2019-12-19)
--------------------------

- Adds new API for Gitlab integration.
- Adds new Kubernetes client API for ingresses.
- Adds new APIs for management of user secrets.
- Adds EOS storage Kubernetes configuration.
- Adds HTCondor and Slurm compute backends.
- Adds support for streaming file uploads.
- Allows unpacked CVMFS and CMS open data volumes.
- Adds Serial workflow step name and compute backend.
- Adds support for Python 3.8.

Version 0.5.0 (2019-04-16)
--------------------------

- Centralises log level and log format configuration.
- Adds new utility to inspect the disk usage on a given workspace.
  (``get_workspace_disk_usage``)
- Introduces the module to share Celery tasks accross REANA
  components. (``tasks.py``)
- Introduces common Celery task to determine whether REANA can
  execute new workflows depending on a set of conditions
  such as running job count. (``reana_ready``, ``check_predefined_conditions``,
  ``check_running_job_count``)
- Allows the AMQP consumer to be configurable with multiple queues.
- Introduces new queue for workflow submission. (``workflow-submission``)
- Introduces new publisher for workflow submissions.
  (``WorkflowSubmissionPublisher``)
- Centralises Kubernetes API client configuration and initialisation.
- Adds Kubernetes specific configuration for CVMFS volumes as utils.
- Introduces a new method, ``copy_openapi_specs``, to automatically move
  validated OpenAPI specifications from components to REANA Commons
  ``openapi_specifications`` directory.
- Centralises interactive session types.
- Introduces central REANA errors through the ``errors.py`` module.
- Skips SSL verification for all HTTPS requests performed with the
  ``BaseAPIClient``.

Version 0.4.0 (2018-11-06)
--------------------------

- Aggregates OpenAPI specifications of REANA components.
- Improves AMQP re-connection handling. Switches from ``pika`` to ``kombu``.
- Enhances test suite and increases code coverage.
- Changes license to MIT.

Version 0.3.1 (2018-09-04)
--------------------------

- Adds parameter expansion and validation utilities for parametrised Serial
  workflows.

Version 0.3.0 (2018-08-10)
--------------------------

- Initial public release.
- Provides basic AMQP pub/sub methods for REANA components.
- Utilities for caching used in different REANA components.
- Click formatting helpers.

.. admonition:: Please beware

   Please note that REANA is in an early alpha stage of its development. The
   developer preview releases are meant for early adopters and testers. Please
   don't rely on released versions for any production purposes yet.
