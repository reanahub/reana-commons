# Changelog

## [0.95.0](https://github.com/reanahub/reana-commons/compare/0.9.8...0.95.0) (2024-11-12)


### ⚠ BREAKING CHANGES

* **python:** drop support for Python 3.6 and 3.7

### Build

* **python:** add minimal `pyproject.toml` ([#466](https://github.com/reanahub/reana-commons/issues/466)) ([9468850](https://github.com/reanahub/reana-commons/commit/94688500bf2d46fb61d165e649b127df6b827ab7))
* **python:** add support for Python 3.13 ([#472](https://github.com/reanahub/reana-commons/issues/472)) ([563f8c8](https://github.com/reanahub/reana-commons/commit/563f8c868c8c0f88bc78d781060ef6d75cdd8006))
* **python:** drop support for Python 3.6 and 3.7 ([#453](https://github.com/reanahub/reana-commons/issues/453)) ([85cca11](https://github.com/reanahub/reana-commons/commit/85cca11e6d110a99b8d4b05ee936d90731238f67))
* **python:** install snakemake compatible with Python 3.12 ([#465](https://github.com/reanahub/reana-commons/issues/465)) ([9c88f7c](https://github.com/reanahub/reana-commons/commit/9c88f7cd33ac87dff36c42ba07b0d6030c68af38))
* **python:** remove deprecated `pytest-runner` ([#466](https://github.com/reanahub/reana-commons/issues/466)) ([e406a59](https://github.com/reanahub/reana-commons/commit/e406a59f1be817d8c570238c58eecabaae01fc16))
* **python:** upgrade yadage dependencies ([#462](https://github.com/reanahub/reana-commons/issues/462)) ([2d2f631](https://github.com/reanahub/reana-commons/commit/2d2f6311e4821f11341d9d302ed8d74b035a15dd))
* **python:** use optional deps instead of `tests_require` ([#466](https://github.com/reanahub/reana-commons/issues/466)) ([6952b62](https://github.com/reanahub/reana-commons/commit/6952b62d7086518edd2befa98cd421a42bb8242a))


### Features

* **gherkin:** add gherkin parser for workflow testing ([#464](https://github.com/reanahub/reana-commons/issues/464)) ([cf38a92](https://github.com/reanahub/reana-commons/commit/cf38a92f28df3a28816adb5fade86e3c78051b11)), closes [#463](https://github.com/reanahub/reana-commons/issues/463)
* **openapi:** add `live_logs_enabled` property in logs output ([#473](https://github.com/reanahub/reana-commons/issues/473)) ([564c027](https://github.com/reanahub/reana-commons/commit/564c027e5a722c2da5e29e2c6203629bdc1c6482))
* **openapi:** add dask_autoscaler_enabled field ([#474](https://github.com/reanahub/reana-commons/issues/474)) ([fd90d74](https://github.com/reanahub/reana-commons/commit/fd90d74279d518cbd062ca0ad9c37ae15d0eb972))
* **openapi:** add dask_cluster_max_number_of_workers field ([#477](https://github.com/reanahub/reana-commons/issues/477)) ([bb6bad6](https://github.com/reanahub/reana-commons/commit/bb6bad65be225127c50842144e2e10d4742f0d92))
* **openapi:** add endpoint to fetch workflow share status ([#429](https://github.com/reanahub/reana-commons/issues/429)) ([6370815](https://github.com/reanahub/reana-commons/commit/637081531da4ba7993c402362b006f15688287e5))
* **openapi:** add endpoint to share workflows ([#429](https://github.com/reanahub/reana-commons/issues/429)) ([b7a3476](https://github.com/reanahub/reana-commons/commit/b7a3476ef51899c5e4f0524d3926960afca57bfa))
* **openapi:** add endpoint to unshare workflows ([#429](https://github.com/reanahub/reana-commons/issues/429)) ([2ec60cc](https://github.com/reanahub/reana-commons/commit/2ec60cc4c92006855db86173d749a65eb8d39e32))
* **openapi:** add endpoints to fetch sharing users ([#429](https://github.com/reanahub/reana-commons/issues/429)) ([761a898](https://github.com/reanahub/reana-commons/commit/761a8982e21b9836a726f76cca55dd98f881de27))
* **openapi:** add recommended images to info endpoint ([#459](https://github.com/reanahub/reana-commons/issues/459)) ([3d2420a](https://github.com/reanahub/reana-commons/commit/3d2420af5f20dba926c2650cb304a60072702a12))
* **openapi:** add share-related parameters to `get_workflows` ([#429](https://github.com/reanahub/reana-commons/issues/429)) ([d4c0358](https://github.com/reanahub/reana-commons/commit/d4c03586ce55e4b24b9325fe2b1c353bf3d71684))
* **openapi:** add workflow engine versions to info endpoint ([#475](https://github.com/reanahub/reana-commons/issues/475)) ([2caa2e2](https://github.com/reanahub/reana-commons/commit/2caa2e2b37d090876a68c2db6e8ec8b2c5e52cd7))
* **openapi:** update reana.yaml schema to include dask field ([#467](https://github.com/reanahub/reana-commons/issues/467)) ([d0becac](https://github.com/reanahub/reana-commons/commit/d0becac22cb04fcbbc0765d44153f171888fba63))
* **openapi:** update workflow sharing specs after changes ([#429](https://github.com/reanahub/reana-commons/issues/429)) ([3f08c0a](https://github.com/reanahub/reana-commons/commit/3f08c0ad4b403d51264f3973285c03209d04ea33))
* **snakemake:** add support for Snakemake 8 ([#471](https://github.com/reanahub/reana-commons/issues/471)) ([cac0dcc](https://github.com/reanahub/reana-commons/commit/cac0dcc10dacdb87a6bb16050c6c020577c2af11))


### Bug fixes

* **kerberos:** stop ticket renewal when pod is terminated ([#454](https://github.com/reanahub/reana-commons/issues/454)) ([a7bcf7a](https://github.com/reanahub/reana-commons/commit/a7bcf7a655dad59478f6fb0a332b9ce348539e63))


### Performance improvements

* **k8s:** avoid extraneous refetching of user secrets ([#456](https://github.com/reanahub/reana-commons/issues/456)) ([77d263e](https://github.com/reanahub/reana-commons/commit/77d263e4c5a86a74f93cd017794b85cb27d5921a)), closes [#455](https://github.com/reanahub/reana-commons/issues/455)
* **kerberos:** stop ticket renewal as soon as possible ([#454](https://github.com/reanahub/reana-commons/issues/454)) ([08cbfa1](https://github.com/reanahub/reana-commons/commit/08cbfa16f08a4e814350791b5de40a40d34841b1))


### Continuous integration

* **actions:** update GitHub actions due to Node 16 deprecation ([#452](https://github.com/reanahub/reana-commons/issues/452)) ([ac2a01b](https://github.com/reanahub/reana-commons/commit/ac2a01b4162f5889837b7328eefb5d7908929ad9))
* **actions:** upgrade to Ubuntu 24.04 and Python 3.12 ([#465](https://github.com/reanahub/reana-commons/issues/465)) ([6fa5566](https://github.com/reanahub/reana-commons/commit/6fa5566f0d778bca33acffe89d1c1af0d69a10e0))
* **commitlint:** improve checking of merge commits ([#465](https://github.com/reanahub/reana-commons/issues/465)) ([273b72d](https://github.com/reanahub/reana-commons/commit/273b72df4edeeaa759f3153ce453285597f4681b))
* **pytest:** invoke `pytest` directly instead of `setup.py test` ([#466](https://github.com/reanahub/reana-commons/issues/466)) ([ed6c468](https://github.com/reanahub/reana-commons/commit/ed6c4689c461c3831efbd60b83be807e16240392))
* **tox:** fix collecting code coverage information ([#470](https://github.com/reanahub/reana-commons/issues/470)) ([ebf3695](https://github.com/reanahub/reana-commons/commit/ebf3695f2c641070ecec517e4ae316dfc3e807be))


### Chores

* **master:** release 0.95.0a1 ([024776f](https://github.com/reanahub/reana-commons/commit/024776f707e8573a19daa4eaf5b239e7dc1257f0))

## [0.9.8](https://github.com/reanahub/reana-commons/compare/0.9.7...0.9.8) (2024-03-01)


### Build

* **python:** change extra names to comply with PEP 685 ([#446](https://github.com/reanahub/reana-commons/issues/446)) ([9dad6da](https://github.com/reanahub/reana-commons/commit/9dad6da7b80bc07423d45dab7b6799911740a082))
* **python:** require smart-open&lt;7 for Python 3.6 ([#446](https://github.com/reanahub/reana-commons/issues/446)) ([17fd581](https://github.com/reanahub/reana-commons/commit/17fd581d4928d5c377f67bcb77c4f245e661c395))
* **python:** restore snakemake `reports` extra ([#446](https://github.com/reanahub/reana-commons/issues/446)) ([904178f](https://github.com/reanahub/reana-commons/commit/904178fe454b9af39164a0c327f1ecd1663132af))


### Continuous integration

* **commitlint:** allow release commit style ([#447](https://github.com/reanahub/reana-commons/issues/447)) ([1208ccf](https://github.com/reanahub/reana-commons/commit/1208ccf2de844afe788d7bbccbd4f63b24af427e))

## [0.9.7](https://github.com/reanahub/reana-commons/compare/0.9.6...0.9.7) (2024-02-20)


### Build

* **snakemake:** require pulp&lt;2.8.0 ([#444](https://github.com/reanahub/reana-commons/issues/444)) ([5daa109](https://github.com/reanahub/reana-commons/commit/5daa109a58066126c2d8a35e7cd7da70d4137f62))


### Documentation

* **authors:** complete list of contributors ([#442](https://github.com/reanahub/reana-commons/issues/442)) ([4a74c10](https://github.com/reanahub/reana-commons/commit/4a74c10e7a248f580778ebc772bffe94e533e7ed))

## [0.9.6](https://github.com/reanahub/reana-commons/compare/0.9.5...0.9.6) (2024-02-13)


### Features

* **config:** allow customisation of runtime group name ([#440](https://github.com/reanahub/reana-commons/issues/440)) ([5cec305](https://github.com/reanahub/reana-commons/commit/5cec30561ba21e2ea695e20eaea8171226f06e52))
* **snakemake:** upgrade to Snakemake 7.32.4 ([#435](https://github.com/reanahub/reana-commons/issues/435)) ([20ae9ce](https://github.com/reanahub/reana-commons/commit/20ae9cebf19a1fdb77ad08956db04ef026521b5d))


### Bug fixes

* **cache:** handle deleted files when calculating access times ([#437](https://github.com/reanahub/reana-commons/issues/437)) ([698900f](https://github.com/reanahub/reana-commons/commit/698900fc63e20bd54dcc4a5faa6cac0be5d0d8de))


### Code refactoring

* **docs:** move from reST to Markdown ([#441](https://github.com/reanahub/reana-commons/issues/441)) ([36ce4e0](https://github.com/reanahub/reana-commons/commit/36ce4e0a86484e3a7006e20545a892424ce0f3a2))


### Continuous integration

* **commitlint:** addition of commit message linter ([#432](https://github.com/reanahub/reana-commons/issues/432)) ([a67906f](https://github.com/reanahub/reana-commons/commit/a67906fe8620e1f624e24e8a4511694a9b60378d))
* **commitlint:** check for the presence of concrete PR number ([#438](https://github.com/reanahub/reana-commons/issues/438)) ([d3035dc](https://github.com/reanahub/reana-commons/commit/d3035dc12cecf16edcbec462dfdb1386da16f6d6))
* **release-please:** initial configuration ([#432](https://github.com/reanahub/reana-commons/issues/432)) ([687f2f4](https://github.com/reanahub/reana-commons/commit/687f2f4ea8c5c49a70c6f121faf7e59a98dd3138))
* **shellcheck:** check all shell scripts recursively ([#436](https://github.com/reanahub/reana-commons/issues/436)) ([709a685](https://github.com/reanahub/reana-commons/commit/709a685b3a8586b069a98c0338283a6bd2721005))
* **shellcheck:** fix exit code propagation ([#438](https://github.com/reanahub/reana-commons/issues/438)) ([85d9a2a](https://github.com/reanahub/reana-commons/commit/85d9a2a68e3929f442e03d5422a37ffd6b7169c6))

## 0.9.5 (2023-12-15)

- Fixes installation by pinning `bravado-core` to versions lower than 6.1.1.

## 0.9.4 (2023-11-30)

- Changes the REANA specification schema to use the `draft-07` version of the JSON Schema specification.
- Changes validation of REANA specification to expose functions for loading workflow input parameters and workflow specifications.
- Changes validation of REANA specification to make the `environment` property mandatory for the steps of serial workflows.
- Changes validation of REANA specification to raise a warning for unexpected properties for the steps of serial workflows.
- Changes CVMFS support to allow users to automatically mount any available repository.
- Fixes the mounting of CVMFS volumes for the REANA deployments that use non-default Kubernetes namespace.

## 0.9.3 (2023-09-26)

- Adds support for Python 3.12.
- Adds the OpenAPI specification support for `prune_workspace` endpoint that allows to delete files that are neither inputs nor outputs from the workspace.
- Adds support for `tests.files` in `reana.yaml` allowing to specify Gherkin feature files for testing runnable examples.
- Changes the OpenAPI specification to include the `run_stopped_at` property in the workflow progress information returned by the workflow list and workflow status endpoints.
- Changes the OpenAPI specification to include the `maximum_interactive_session_inactivity_period` value to the `info` endpoint.
- Changes the email sending utility to allow configuring authentication and encryption options.
- Changes validation of REANA specification to emit warnings about unknown properties.
- Fixes the verbs used to describe changes to the status of a workflow in order to avoid incorrect grammatical phrases such as `workflow has been failed`.
- Fixes the loading of Snakemake and CWL workflow specifications when no parameters are specified.
- Fixes the OpenAPI specification of GitLab OAuth endpoint return statuses.
- Fixes container image names to be Podman-compatible.
- Fixes the email sending utility to not send emails when notifications are disabled globally.

## 0.9.2.1 (2023-07-19)

- Changes `PyYAML` dependency version bounds in order to fix installation on Python 3.10+.

## 0.9.2 (2023-02-10)

- Fixes `wcmatch` dependency version specification.

## 0.9.1 (2023-01-18)

- Changes Kerberos renew container's configuration to log each ticket renewal.

## 0.9.0 (2022-12-13)

- Adds support for Python 3.11.
- Adds support for Rucio.
- Adds REANA specification validation and loading logic from `reana-client`.
- Adds common utility functions for managing workspace files.
- Adds OpenAPI specification support for `launch` endpoint that allows running workflows from remote sources.
- Adds OpenAPI specification support for `get_workflow_retention_rules` endpoint that allows to retrieve the workspace file retention rules of a workflow.
- Adds generation of Kerberos init and renew container's configuration.
- Adds support for Unicode characters inside email body.
- Changes OpenAPI specification to include missing response schema elements and some other small enhancements.
- Changes the Kubernetes Python client to use the `networking/v1` API.
- Changes REANA specification loading functionality to allow specifying different working directories.
- Changes REANA specification to allow enabling Kerberos for the whole workflow.
- Changes REANA specification to allow specifying `retention_days` for the workflow.
- Changes REANA specification to allow specifying `slurm_partition` and `slurm_time` for Slurm compute backend jobs.
- Changes the loading of Snakemake specifications to preserve the current working directory.
- Fixes the submission of jobs by stripping potential leading and trailing whitespaces in Docker image names.

## 0.8.5 (2022-02-23)

- Adds `retry_count` parameter to WorkflowSubmissionPublisher.

## 0.8.4 (2022-02-08)

- Adds new configuration variable to toggle Kubernetes security context. (`K8S_USE_SECURITY_CONTEXT`)
- Changes installation to revert `Yadage` dependency versions.

## 0.8.3 (2022-02-04)

- Changes installation to remove upper version pin on `kombu`.

## 0.8.2 (2022-02-01)

- Adds support for Python 3.10.
- Adds workflow name validation utility.
- Changes `Snakemake` loaded specification to include compute backends.
- Changes OpenAPI specification with respect to return supported compute backends in `info` endpoint.
- Fixes file system usage calculation on CephFS shares in `get_disk_usage` utility function.

## 0.8.1 (2021-12-21)

- Adds OpenAPI specification support for `kubernetes_job_timeout` handling.
- Changes OpenAPI specification for cluster health status endpoint.
- Changes Yadage dependencies to allow 0.21.x patchlevel-version updates.
- Changes installation to require Python-3.6 or higher versions.

## 0.8.0 (2021-11-22)

- Adds `get_disk_usage` utility function to calculate disk usage for a directory.
- Adds `Yadage` workflow specification loading utilities.
- Adds workspace validation utilities.
- Adds `Snakemake` workflow engine integration.
- Adds custom objects API instance to k8s client.
- Adds available worklow engines configuration.
- Adds environment variable to define time between job controller connection checks.
- Adds cluster health status endpoint.
- Adds OpenAPI specifications with respect to user quotas.
- Changes `workflow-submission` queue as a priority queue and allows to set the priority number on workflow submission.
- Changes OpenAPI specifications with respect to turning `workspaces` endpoint into `info`.
- Changes publisher logging level on error callback.
- Removes support for Python 2.

## 0.7.5 (2021-07-02)

- Adds support for glob patterns when listing workflow files.
- Adds support for specifying `kubernetes_memory_limit` for Kubernetes compute backend jobs.

## 0.7.4 (2021-03-17)

- Adds new functions to serialise/deserialise job commands between REANA components.
- Changes `reana_ready` function location to REANA-Server.

## 0.7.3 (2021-02-22)

- Adds new configuration variable to toggle runtime user jobs clean up depending on their statuses. (`REANA_RUNTIME_KUBERNETES_KEEP_ALIVE_JOBS_WITH_STATUSES`)
- Adds central class to instantiate workflow engines with more resilience. (`workflow_engine.create_workflow_engine_command`)

## 0.7.2 (2021-02-02)

- Adds support for Python 3.9.
- Fixes minor code warnings.
- Fixes a helper function that calculates directory hashes.
- Changes OpenAPI specifications with respect to sign-up form.
- Changes OpenAPI specifications with respect to email confirmation.
- Changes CI system to include Python flake8 checker.

## 0.7.1 (2020-11-09)

- Adds support for restarting yadage workflows (through `accept_metadir` operational option).
- Allows `htcondor_max_runtime` and `htcondor_accounting_group` to be specified for HTC jobs.
- Adds new field in REANA-Server OpenAPI spec to return server version.
- Changes CI system from Travis to GitHub Actions.

## 0.7.0 (2020-10-20)

- Adds new utility to send emails.
- Adds centralised validation utility for workflow operational options.
- Adds new configuration variable to set the maximum number of running workflows. (`REANA_MAX_CONCURRENT_BATCH_WORKFLOWS`)
- Adds new configuration variable to set prefix of REANA cluster component names. (`REANA_COMPONENT_PREFIX`)
- Adds new configuration variable for the runtime pod node selector label. (`REANA_RUNTIME_KUBERNETES_NODE_LABEL`)
- Adds new configuration variable to define the Kubernetes namespace in which REANA infrastructure components run. (`REANA_INFRASTRUCTURE_KUBERNETES_NAMESPACE`)
- Adds new configuration variable to define the Kubernetes namespace in which REANA runtime components components run. (`REANA_RUNTIME_KUBERNETES_NAMESPACE`)
- Adds possibility to specify unpacked container images for running jobs.
- Adds support for `initfiles` operational option for the Yadage workflow engine.
- Fixes memory leak in Bravado client instantiation.
- Changes CephFS Persistent Volume Claim name. (`REANA_SHARED_PVC_NAME`)
- Changes default logging level to `INFO`.
- Changes default CVMFS volume list to include LHCb Gaudi related workflows.
- Changes code formatting to respect `black` coding style.
- Changes underlying requirements to use Kubernetes Python library version 11.
- Changes underlying requirements to use latest CVMFS CSI driver version.
- Changes documentation to single-page layout.

## 0.6.1 (2020-05-25)

- Upgrades Kubernetes Python client.

## 0.6.0 (2019-12-19)

- Adds new API for Gitlab integration.
- Adds new Kubernetes client API for ingresses.
- Adds new APIs for management of user secrets.
- Adds EOS storage Kubernetes configuration.
- Adds HTCondor and Slurm compute backends.
- Adds support for streaming file uploads.
- Allows unpacked CVMFS and CMS open data volumes.
- Adds Serial workflow step name and compute backend.
- Adds support for Python 3.8.

## 0.5.0 (2019-04-16)

- Centralises log level and log format configuration.
- Adds new utility to inspect the disk usage on a given workspace.
  (`get_workspace_disk_usage`)
- Introduces the module to share Celery tasks accross REANA
  components. (`tasks.py`)
- Introduces common Celery task to determine whether REANA can
  execute new workflows depending on a set of conditions
  such as running job count. (`reana_ready`, `check_predefined_conditions`,
  `check_running_job_count`)
- Allows the AMQP consumer to be configurable with multiple queues.
- Introduces new queue for workflow submission. (`workflow-submission`)
- Introduces new publisher for workflow submissions.
  (`WorkflowSubmissionPublisher`)
- Centralises Kubernetes API client configuration and initialisation.
- Adds Kubernetes specific configuration for CVMFS volumes as utils.
- Introduces a new method, `copy_openapi_specs`, to automatically move
  validated OpenAPI specifications from components to REANA Commons
  `openapi_specifications` directory.
- Centralises interactive session types.
- Introduces central REANA errors through the `errors.py` module.
- Skips SSL verification for all HTTPS requests performed with the
  `BaseAPIClient`.

## 0.4.0 (2018-11-06)

- Aggregates OpenAPI specifications of REANA components.
- Improves AMQP re-connection handling. Switches from `pika` to `kombu`.
- Enhances test suite and increases code coverage.
- Changes license to MIT.

## 0.3.1 (2018-09-04)

- Adds parameter expansion and validation utilities for parametrised Serial
  workflows.

## 0.3.0 (2018-08-10)

- Initial public release.
- Provides basic AMQP pub/sub methods for REANA components.
- Utilities for caching used in different REANA components.
- Click formatting helpers.
