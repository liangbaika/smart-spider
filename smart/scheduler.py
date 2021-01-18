# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      scheduler
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      there is a python file description
# ------------------------------------------------------------------
import asyncio
from collections import deque
from typing import Optional

from smart.log import log
from smart.request import Request

from abc import ABC, abstractmethod


class BaseSchedulerContainer(ABC):

    @abstractmethod
    def push(self, request: Request):
        pass

    @abstractmethod
    def pop(self) -> Optional[Request]:
        pass

    @abstractmethod
    def size(self) -> int:
        pass


class BaseDuplicateFilter(ABC):

    @abstractmethod
    def add(self, url):
        pass

    @abstractmethod
    def contains(self, url):
        pass

    @abstractmethod
    def length(self):
        pass


class SampleDuplicateFilter(BaseDuplicateFilter):

    def __init__(self):
        self.set_container = set()

    def add(self, url):
        if url:
            self.set_container.add(url)

    def contains(self, url):
        if not url:
            return False
        if url in self.set_container:
            return True
        return False

    def length(self):
        return len(self.set_container)


class DequeSchedulerContainer(BaseSchedulerContainer):

    def __init__(self):
        self.url_queue = asyncio.Queue()

    def push(self, request: Request):
        self.url_queue.put_nowait(request)
        # self.url_queue.append(request)

    def pop(self) -> Optional[Request]:
        if self.url_queue:
            return self.url_queue.get_nowait()
            # return self.url_queue.popleft()
        return None

    async def async_pop(self) -> Optional[Request]:
        req = await self.url_queue.get()
        return req

    def size(self) -> int:
        return self.url_queue.qsize()


class Scheduler:
    def __init__(self, duplicate_filter: BaseDuplicateFilter = None,
                 scheduler_container: BaseSchedulerContainer = None):
        if duplicate_filter is None:
            duplicate_filter = SampleDuplicateFilter()
        if scheduler_container is None:
            scheduler_container = DequeSchedulerContainer()
        self.scheduler_container = scheduler_container
        self.duplicate_filter = duplicate_filter
        self.log = log

    def schedlue(self, request: Request):
        self.log.debug(f"get a request {request} wating toschedlue ")
        if not request.dont_filter:
            _url = request.url + ":" + str(request.retry)
            if self.duplicate_filter.contains(_url):
                self.log.debug(f"duplicate_filter filted ... url{_url} ")
                return
            self.duplicate_filter.add(_url)
        self.scheduler_container.push(request)

    def get(self) -> Optional[Request]:
        self.log.debug(f"get a request to download task ")
        return self.scheduler_container.pop()

    def size(self)->int:
        return self.scheduler_container.size()

    async def async_get(self) -> Optional[Request]:
        self.log.debug(f"get a request to download task ")
        res = await self.scheduler_container.async_pop()
        return res
