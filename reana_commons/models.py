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
# You should have received a copy of the GNU General Public License along with
# REANA; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307, USA.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization or
# submit itself to any jurisdiction.

"""Models for REANA Components."""

from __future__ import absolute_import

import enum
import os
import uuid
from string import Template

from sqlalchemy import (Boolean, Column, Enum, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy_utils import JSONType, UUIDType
from sqlalchemy_utils.models import Timestamp

Base = declarative_base()

user_workspace_path_template = \
    Template('users/$user_id/workflow_runs/$workflow_run_id')

def generate_uuid():
    """Generate new uuid."""
    return str(uuid.uuid4())


class User(Base, Timestamp):
    """User table"""

    __tablename__ = 'user_'

    id_ = Column(UUIDType, primary_key=True, unique=True,
                 default=generate_uuid)
    api_key = Column(String(length=255))
    email = Column(String(length=255), unique=True, primary_key=True)
    workflows = relationship("Workflow", backref="user_")

    def __repr__(self):
        """User string represetantion."""
        return '<User %r>' % self.id_

    def get_user_workspace(self):
        """Build user's workspace directory path.

        :param user: Workspace owner.
        :return: Path to the user's workspace directory.
        """
        return user_workspace_path_template.substitute(
            dict(user_id=self.id_, workflow_run_id=''))


class UserOrganization(Base):
    """Relationship between Users and Organizations."""
    __tablename__ = 'user_organizations'

    user_id = Column(UUIDType, ForeignKey('user_.id_'), primary_key=True)
    name = Column(String(255), ForeignKey('organization.name'),
                  primary_key=True,)


class Organization(Base, Timestamp):
    __tablename__ = 'organization'

    id_ = Column(UUIDType, primary_key=True, default=generate_uuid)
    name = Column(String(255), primary_key=True, unique=True)
    # database_uri = Column(String(255))


class WorkflowStatus(enum.Enum):
    created = 0
    running = 1
    finished = 2
    failed = 3


class Workflow(Base, Timestamp):
    """Workflow table."""

    __tablename__ = 'workflow'

    id_ = Column(UUIDType, primary_key=True)
    name = Column(String(255))
    run_number = Column(Integer)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.created)
    owner_id = Column(UUIDType, ForeignKey('user_.id_'))
    specification = Column(JSONType)
    parameters = Column(JSONType)
    type_ = Column(String(30))
    logs = Column(String)
    __table_args__ = UniqueConstraint('name', 'owner_id', 'run_number',
                                      name='_user_workflow_run_uc'),

    def __init__(self, id_, name, owner_id, specification, parameters, type_,
                 logs, status=WorkflowStatus.created):
        """Initialize workflow model."""
        self.id_ = id_
        self.name = name
        self.status = status
        self.owner_id = owner_id
        self.specification = specification
        self.parameters = parameters
        self.type_ = type_
        self.logs = logs or ''
        from .database import Session
        last_workflow = Session.query(Workflow).filter_by(
            name=name,
            owner_id=owner_id).\
            order_by(Workflow.run_number.desc()).first()
        if not last_workflow:
            self.run_number = 1
        else:
            self.run_number = last_workflow.run_number + 1

    def __repr__(self):
        """Workflow string represetantion."""
        return '<Workflow %r>' % self.id_

    def get_workflow_run_dir(self):
        """Build workflow run directory path.

        :return: Path to the workflow run workspace directory.
        """
        return user_workspace_path_template.substitute(
            dict(user_id=self.owner_id, workflow_run_id=self.id_))

    @staticmethod
    def update_workflow_status(db_session, workflow_uuid, status,
                               new_logs, message=None):
        """Update database workflow status.

        :param workflow_uuid: UUID which represents the workflow.
        :param status: String that represents the analysis status.
        :param status_message: String that represents the message
           related with the
           status, if there is any.
        """
        try:
            workflow = \
                db_session.query(Workflow).filter_by(id_=workflow_uuid).first()

            if not workflow:
                raise Exception('Workflow {0} doesn\'t exist in database.'.
                                format(workflow_uuid))
            if status:
                workflow.status = status
            workflow.logs = (workflow.logs or "") + new_logs
            db_session.commit()
        except Exception as e:
            raise e


class Job(Base, Timestamp):
    """Job table."""

    __tablename__ = 'job'

    id_ = Column(UUIDType, unique=True, primary_key=True,
                 default=generate_uuid)
    workflow_uuid = Column(UUIDType)
    status = Column(String(30))
    job_type = Column(String(30))
    cvmfs_mounts = Column(String(256))
    shared_file_system = Column(Boolean)
    docker_img = Column(String(256))
    experiment = Column(String(256))
    cmd = Column(String(10000))
    env_vars = Column(String(10000))
    restart_count = Column(Integer)
    max_restart_count = Column(Integer)
    deleted = Column(Boolean)
    logs = Column(String, nullable=True)


class Run(Base, Timestamp):
    """Run table."""

    __tablename__ = 'run'

    id_ = Column(UUIDType, unique=True, primary_key=True,
                 default=generate_uuid)
    workflow_uuid = Column(UUIDType, primary_key=True)
    run_number = Column(Integer)
    planned = Column(Integer)
    submitted = Column(Integer)
    succeeded = Column(Integer)
    failed = Column(Integer)
    engine_specific = Column(JSONType)


class RunJobs(Base):
    """Run jobs table."""

    __tablename__ = 'run_jobs'

    id_ = Column(UUIDType, primary_key=True, default=generate_uuid)
    run_id = Column(UUIDType, ForeignKey('run.id_'))
    job_id = Column(UUIDType, ForeignKey('job.id_'))


class JobCache(Base, Timestamp):
    """Job Cache table."""

    __tablename__ = 'job_cache'

    id_ = Column(UUIDType, unique=True, primary_key=True,
                 default=generate_uuid)
    job_id = Column(UUIDType, ForeignKey('job.id_'), primary_key=True)
    parameters = Column(String(1024))
    result_path = Column(String(1024))
    workspace_hash = Column(String(1024))
