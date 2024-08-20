# -*- coding: utf-8 -*-
#
# This file is part of REANA.
# Copyright (C) 2024 CERN.
#
# REANA is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""REANA-commons Redis cache."""

from redis import StrictRedis
from redis_cache import RedisCache

from reana_commons.config import (
    REANA_INFRASTRUCTURE_COMPONENTS_HOSTNAMES,
    REDIS_CACHE_PORT,
)

redis_cache = RedisCache(
    redis_client=StrictRedis(
        host=REANA_INFRASTRUCTURE_COMPONENTS_HOSTNAMES["cache"],
        port=REDIS_CACHE_PORT,
        decode_responses=True,
    )
)
