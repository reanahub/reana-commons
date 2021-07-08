Changes
=======

Version master (UNRELEASED)
---------------------------

- Adds ``get_disk_usage`` utility function to calculate disk usage for a directory.
- Centralises ``fs`` package dependency
- Changes ``workflow-submission`` queue as a priority queue and allows to set the priority number on workflow submission.
- Adds Yadage workflow specification loading utilities.
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
