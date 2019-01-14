# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2018 CERN.
#
# REANA is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# REANA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with REANA; if not, see <http://www.gnu.org/licenses>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization or
# submit itself to any jurisdiction.

"""REANA-Commons Task tests."""

from mock import patch

from reana_commons.tasks import reana_ready


def test_reana_ready():
    """Test that reana_ready task checks all conditions."""
    with patch('reana_commons.config.REANA_READY_CONDITIONS',
               {'pytest_reana.fixtures':
                ['sample_condition_for_starting_queued_workflows',
                 'sample_condition_for_starting_queued_workflows',
                 'sample_condition_for_requeueing_workflows']}):
        assert not reana_ready()

    with patch('reana_commons.config.REANA_READY_CONDITIONS',
               {'pytest_reana.fixtures':
                ['sample_condition_for_starting_queued_workflows']}):
        assert reana_ready()
