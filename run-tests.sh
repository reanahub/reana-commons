#!/bin/sh
#
# This file is part of REANA.
# Copyright (C) 2018, 2020, 2021, 2023 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

# Quit on errors
set -o errexit

# Quit on unbound symbols
set -o nounset

check_script () {
    shellcheck run-tests.sh
}

check_black () {
    black --check .
}

check_flake8 () {
    flake8 .
}

check_pydocstyle () {
    pydocstyle reana_commons
}

check_manifest () {
    check-manifest
}

check_sphinx () {
    sphinx-build -qnNW docs docs/_build/html
}

check_pytest () {
    if [ -n "${PYTESTARG-}" ]; then
        pytest "$PYTESTARG"
    else
        python setup.py test
    fi
}

check_all () {
    check_script
    check_black
    check_flake8
    check_pydocstyle
    check_manifest
    check_sphinx
    check_pytest
}

if [ $# -eq 0 ]; then
    check_all
    exit 0
fi

for arg in "$@"
do
    case $arg in
        --check-shellscript) check_script;;
        --check-black) check_black;;
        --check-flake8) check_flake8;;
        --check-pydocstyle) check_pydocstyle;;
        --check-manifest) check_manifest;;
        --check-sphinx) check_sphinx;;
        --check-pytest) check_pytest;;
        *)
    esac
done
