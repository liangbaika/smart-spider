# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      __init__.py
# Author:    liangbaikai
# Date:      2021/1/14
# Desc:      there is a python file description
# ------------------------------------------------------------------
import asyncio
import base64
import hashlib
import json
import pickle
import random
import threading
import time
from collections import deque
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Optional

import aioredis

from smart.log import log
from smart.request import Request
from smart.scheduler import BaseDuplicateFilter, BaseSchedulerContainer
import redis  # 导入redis 模块

from smart.signal import reminder
from smart.tool import mutations_bkdr_hash
from test.redis_lock import acquire_lock, release_lock


class RedisSchuler(BaseSchedulerContainer):
    # pool = redis.ConnectionPool(host='121.4.157.53', port=6399, password="Admin123@@@", decode_responses=True)

    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
    tp = ThreadPoolExecutor(100)

    _stop = False

    def __init__(self):
        self.redis = redis.Redis(connection_pool=self.pool)
        self.task_queue_name = "smart_spider_redis_task_queue"
        # 需要保持session 的放在本地 或者序列化报错的request 的容器
        self.faults = deque()
        self.caches = deque()
        self.ecodeing = "latin1"
        self.tp.submit(self.buffer)

    def _do_push(self, request: Request):
        try:
            req_byte = pickle.dumps(request)
            self.redis.rpush(self.task_queue_name, req_byte.decode(self.ecodeing))
        except Exception:
            self.faults.append(request)

    def push(self, request: Request):
        self.tp.submit(self._do_push, request)

    def buffer(self):
        cons = []
        while not self._stop:
            # if len(cons) > 0 and (max(cons) - min(cons) > 3 and len(cons) > 90):
            #     time.sleep(random.uniform(0.2, 2))
            #     cons = []

            res = self._do_pop()
            if res:
                self.caches.append(res)
                cons.append(time.time())
            else:
                time.sleep(random.uniform(0.1, 0.5))
            time.sleep(0.001)

    def _do_pop(self) -> Optional[Request]:
        if len(self.faults) > 0:
            req = self.faults.popleft()
            if req:
                return req
        else:
            try:
                # identifier = acquire_lock('resource')
                code = self.redis.lpop(self.task_queue_name)
                if code:
                    req_byte = code.encode(self.ecodeing)
                    req = pickle.loads(req_byte)
                    return req
            except Exception as e:
                print(e)
        return None

    def pop(self) -> Optional[Request]:
        if self.caches:
            return self.caches.popleft()
        return None

    def size(self) -> int:
        return self.redis.llen(self.task_queue_name)

    @staticmethod
    @reminder.engin_close.connect
    def engin_close(sender, **kwargs):
        RedisSchuler._stop = True
        RedisSchuler.tp.shutdown()


class RedisBaseDuplicateFilter(BaseDuplicateFilter):
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)

    # pool = redis.ConnectionPool(host='121.4.157.53', port=6399, password="Admin123@@@", decode_responses=True)

    def __init__(self):
        self.redis = redis.Redis(connection_pool=self.pool)
        self.filterset_name = "smart_spider_redis_repeat_set"

    def add(self, url):
        if url:
            self.redis.sadd(self.filterset_name, mutations_bkdr_hash(url))

    def contains(self, url):
        res = self.redis.sismember(self.filterset_name, mutations_bkdr_hash(url))
        return res

    def length(self):
        return self.redis.scard(self.filterset_name)


class AioRedisBaseDuplicateFilter(BaseDuplicateFilter):
    # pool = redis.ConnectionPool(host='121.4.157.53', port=6399, password="Admin123@@@", decode_responses=True)
    def __init__(self):
        self.redis = None
        self.lock = asyncio.Lock()
        self.filterset_name = "aio_smart_spider_redis_repeat_set"

    async def add(self, url):
        await self.creat_redi()
        if url:
            await self.redis.sadd(self.filterset_name, mutations_bkdr_hash(url))

    async def contains(self, url):
        await self.creat_redi()
        res =await self.redis.sismember(self.filterset_name, mutations_bkdr_hash(url))
        return res

    async def length(self):
        await self.creat_redi()
        return await self.redis.scard(self.filterset_name)

    async def creat_redi(self):
        if not self.redis:
            async with self.lock:
                if not self.redis:
                    self.redis = await aioredis.create_redis_pool(('127.0.0.1', 6379), db=0, encoding='utf-8')
                    print("#############")

class AioRedisSchuler(BaseSchedulerContainer):
    def __init__(self):
        self.redis = None
        self.task_queue_name = "aio_smart_spider_redis_task_queue"
        self.ecodeing = "latin1"
        self.lock = asyncio.Lock()

    async def push(self, request: Request):
        await self.creat_redi()
        req_byte = pickle.dumps(request)
        await self.redis.rpush(self.task_queue_name, req_byte.decode(self.ecodeing))

    async def creat_redi(self):
        if not self.redis:
            async with self.lock:
                if not self.redis:
                    self.redis = await aioredis.create_redis_pool(('127.0.0.1', 6379), db=0, encoding='utf-8')
                    print("#############")

    async def pop(self) -> Optional[Request]:
        try:
            await self.creat_redi()
            code = await self.redis.lpop(self.task_queue_name)
            if code:
                req_byte = code.encode(self.ecodeing)
                req = pickle.loads(req_byte)
                return req
        except Exception as e:
            print(e)
        return None

    async def size(self) -> int:
        await self.creat_redi()
        return await self.redis.llen(self.task_queue_name)
