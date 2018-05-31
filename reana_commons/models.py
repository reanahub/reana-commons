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
import uuid

from sqlalchemy import (Column, Enum, ForeignKey, Integer, String,
                        UniqueConstraint, Boolean)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy_utils import JSONType, UUIDType
from sqlalchemy_utils.models import Timestamp

Base = declarative_base()


class User(Base, Timestamp):
    """User table"""

    __tablename__ = 'user_'

    id_ = Column(UUIDType, primary_key=True)
    api_key = Column(String(length=120))
    email = Column(String(length=255))
    workflows = relationship("Workflow", backref="user")

    def __repr__(self):
        """User string represetantion."""
        return '<User %r>' % self.id_


class UserOrganization(Base):
    """Relationship between Users and Organizations."""
    __tablename__ = 'user_organizations'

    user_id = Column(UUIDType, ForeignKey('user_.id_'), primary_key=True)
    name = Column(String(255), ForeignKey('organization.name'),
                  primary_key=True,)


class Organization(Base, Timestamp):
    __tablename__ = 'organization'

    id_ = Column(UUIDType, primary_key=True, default=str(uuid.uuid4()))
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
    workspace_path = Column(String(255))
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.created)
    owner_id = Column(UUIDType, ForeignKey('user_.id_'))
    specification = Column(JSONType)
    parameters = Column(JSONType)
    type_ = Column(String(30))
    logs = Column(String)
    __table_args__ = UniqueConstraint('name', 'owner_id', 'run_number',
                                      name='_user_workflow_run_uc'),

    def __init__(self, id_, name, workspace_path,
                 owner_id, specification, parameters, type_,
                 logs, status=WorkflowStatus.created):
        """Initialize workflow model."""
        self.id_ = id_
        self.name = name
        self.workspace_path = workspace_path
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

    @staticmethod
    def update_workflow_status(db_session, workflow_uuid, status,
                               log, message=None):
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

            workflow.status = status
            db_session.commit()
        except Exception as e:
            log.info(
                'An error occurred while updating workflow: {0}'.
                format(str(e)))
            raise e

    @staticmethod
    def append_workflow_logs(db_session, workflow_uuid,
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

            workflow.logs = (workflow.logs or "") + new_logs
            db_session.commit()
        except Exception as e:
            # log.info(
            #     'An error occurred while updating workflow: {0}'.
            #     format(str(e)))
            raise e


class Job(Base, Timestamp):
    """Job table."""

    __tablename__ = 'job'

    id_ = Column(UUIDType, primary_key=True)
    workflow_uuid = Column(UUIDType, primary_key=True)
    status = Column(String(30))
    job_type = Column(String(30))
    cvmfs_mounts = Column(String(256))
    shared_file_system = Column(Boolean)
    docker_img = Column(String(256))
    experiment = Column(String(256))
    cmd = Column(String(1024))
    env_vars = Column(String(1024))
    restart_count = Column(Integer)
    max_restart_count = Column(Integer)
    deleted = Column(Boolean)
    logs = Column(String)

    def __init__(self, id_, workflow_uuid, status, job_type, cvmfs_mounts,
                 shared_file_system, docker_img, experiment, cmd, env_vars,
                 restart_count, max_restart_count, deleted, logs=None):
        """Initialize job table."""
        self.id_ = id_
        self.workflow_uuid = workflow_uuid
        self.status = status
        self.job_type = job_type
        self.cvmfs_mounts = cvmfs_mounts
        self.shared_file_system = shared_file_system
        self.docker_img = docker_img
        self.experiment = experiment
        self.cmd = cmd
        self.env_vars = env_vars
        self.restart_count = restart_count
        self.max_restart_count = max_restart_count
        self.deleted = deleted
        self.logs = logs
