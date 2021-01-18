# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      __init__.py
# Author:    liangbaikai
# Date:      2021/1/14
# Desc:      there is a python file description
# ------------------------------------------------------------------
import base64
import hashlib
import json
import pickle
import random
import threading
import time
from collections import deque
from typing import Optional
from smart.request import Request
from smart.scheduler import BaseDuplicateFilter, BaseSchedulerContainer
import redis  # 导入redis 模块


class RedisSchuler(BaseSchedulerContainer):
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)

    def __init__(self):
        self.redis = redis.Redis(connection_pool=self.pool)
        self.task_queue_name = "smart_spider_redis_task_queue"
        # 需要保持session 的放在本地 或者序列化报错的request 的容器
        self.faults = deque()
        self.ecodeing = "latin1"

    def push(self, request: Request):
        try:
            req_byte = pickle.dumps(request)
            self.redis.rpush(self.task_queue_name, req_byte.decode(self.ecodeing))
        except Exception:
            self.faults.append(request)

    def pop(self) -> Optional[Request]:
        if len(self.faults) > 0:
            req = self.faults.popleft()
            if req:
                return req
        else:
            code = self.redis.lpop(self.task_queue_name)
            if code:
                req_byte = code.encode(self.ecodeing)
                req = pickle.loads(req_byte)
                return req
        return None

    def size(self) -> int:
        return self.redis.llen(self.task_queue_name)


class RedisBaseDuplicateFilter(BaseDuplicateFilter):
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)


    def __init__(self):
        self.redis = redis.Redis(connection_pool=self.pool)
        self.filterset_name = "smart_spider_redis_repeat_set"

    def add(self, url):
        if url:
            self.redis.sadd(self.filterset_name, url)

    def contains(self, url):
        return self.redis.sismember(self.filterset_name, url)

    def length(self):
        return self.redis.scard(self.filterset_name)
