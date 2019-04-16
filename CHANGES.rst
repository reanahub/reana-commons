Changes
=======

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
