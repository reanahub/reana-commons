# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2026 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Wire contract between the sandboxed specification loader and its callers.

The reana-workflow-validator sandbox (which produces the report), the
reana-workflow-controller (which extracts it from the pod log), and reana-server
(which interprets it) must agree on how the loader's result crosses the process
boundary. Centralising the sentinels, exit codes, and error codes here keeps
that contract in one place so it cannot silently drift between the repositories.
"""

#: Accepted top-level REANA specification file names, in priority order.
REANA_SPEC_FILENAMES = ("reana.yaml", "reana.yml")

#: Sentinels wrapping the single-line JSON report the loader writes to stdout,
#: so the controller can extract it even if a library leaks other output. The
#: report is emitted on one line, and the *last* block is authoritative.
REPORT_START = "===REANA-VALIDATION-REPORT-START==="
REPORT_END = "===REANA-VALIDATION-REPORT-END==="

# Loader exit codes. The sandbox is a pure loader, so these describe the
# *loading* outcome only; the valid/invalid (cluster policy) decision is made by
# reana-server on the emitted specification.
EXIT_LOADED = 0  #: The specification loaded; the report carries it.
EXIT_LOAD_ERROR = 1  #: The specification could not be loaded (a user error).
EXIT_INTERNAL_ERROR = 2  #: Internal/infrastructure error (not a bad spec).

# ``error.code`` values carried by the report's ``error`` object.
ERROR_CODE_LOAD = "load"  #: The specification failed to load (user-facing).
ERROR_CODE_INTERNAL = "internal"  #: An infrastructure failure, not a bad spec.
