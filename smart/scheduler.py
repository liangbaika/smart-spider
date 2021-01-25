# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      scheduler
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      request scheduler, request filter
# ------------------------------------------------------------------
import asyncio
import inspect
import time
from collections import deque
from typing import Optional, Any

from smart.log import log
from smart.request import Request

from abc import ABC, abstractmethod

from smart.tool import mutations_bkdr_hash


class BaseSchedulerContainer(ABC):
    """
    request  保存的容器
    可以是一个队列 数据库 或者 redis
    """

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
    """
    请求去重过滤器
    目前内置的是一个基于set的去重 你可以扩展成布隆过滤器
    """

    @abstractmethod
    def add(self, url) -> Any:
        pass

    @abstractmethod
    def contains(self, url) -> bool:
        pass

    @abstractmethod
    def length(self) -> int:
        pass


class SampleDuplicateFilter(BaseDuplicateFilter):
    """
    基于set的请求去重器
    """

    def __init__(self):
        self.set_container = set()

    def add(self, url):
        if url:
            self.set_container.add(mutations_bkdr_hash(url))

    def contains(self, url):
        if not url:
            return False
        if mutations_bkdr_hash(url) in self.set_container:
            return True
        return False

    def length(self):
        return len(self.set_container)


class DequeSchedulerContainer(BaseSchedulerContainer):
    """
    deque 保存request
    """

    def __init__(self):
        self.url_queue = deque()

    def push(self, request: Request):
        self.url_queue.append(request)

    def pop(self) -> Optional[Request]:
        if self.url_queue:
            return self.url_queue.popleft()
        return None

    def size(self) -> int:
        return len(self.url_queue)


class AsyncQequeSchedulerContainer(BaseSchedulerContainer):
    """
    deque 保存request
    """

    def __init__(self):
        self.url_queue = asyncio.Queue()

    async def push(self, request: Request):
        await self.url_queue.put(request)

    async def pop(self) -> Optional[Request]:
        res = await self.url_queue.get()
        self.url_queue.task_done()
        return res

    def size(self) -> int:
        return self.url_queue.qsize()


class BaseScheduler(ABC):
    """
    请求调度器基类
    """

    @abstractmethod
    def schedlue(self, request: Request) -> bool:
        pass

    @abstractmethod
    def get(self) -> Optional[Request]:
        pass


class Scheduler(BaseScheduler):
    """
    请求调度器
    """

    def __init__(self, duplicate_filter: BaseDuplicateFilter = None,
                 scheduler_container: BaseSchedulerContainer = None):
        """
        初始方法
        :param duplicate_filter: 去重器对象
        :param scheduler_container: 调度容器对象
        """
        self.duplicate_filter = duplicate_filter or SampleDuplicateFilter()
        self.scheduler_container = scheduler_container or DequeSchedulerContainer()
        self.log = log

    def schedlue(self, request: Request) -> bool:
        """
        将请求放入 scheduler_container容器
        :param request: 请求
        :return: None
        """
        self.log.debug(f"get a request {request} wating toschedlue ")
        # dont_filter=true的请求不过滤
        if not request.dont_filter:
            # retry 失败的 重试实现延迟调度
            _url = request.url + ":" + str(request.retry)
            if self.duplicate_filter.contains(_url):
                self.log.debug(f"duplicate_filter filted ... url {_url} ")
                return False
            self.duplicate_filter.add(_url)
        push = self.scheduler_container.push(request)
        if inspect.isawaitable(push):
            asyncio.create_task(push)
        return True

    def get(self) -> Optional[Request]:
        """
        从scheduler_container容器获取一个请求对象
        可能为空
        :return: Optional[Request]
        """
        self.log.debug(f"get a request to download task ")
        pop = self.scheduler_container.pop()
        if pop is None:
            return None

        if inspect.isawaitable(pop):
            task = asyncio.create_task(pop)
            return task
        else:
            return pop


class AsyncScheduler(BaseScheduler):
    """
    请求调度器
    """

    def __init__(self, duplicate_filter: BaseDuplicateFilter = None,
                 scheduler_container: BaseSchedulerContainer = None):
        """
        初始方法
        :param duplicate_filter: 去重器对象
        :param scheduler_container: 调度容器对象
        """
        self.duplicate_filter = duplicate_filter or SampleDuplicateFilter()
        self.scheduler_container = scheduler_container or AsyncQequeSchedulerContainer()
        self.log = log

    async def schedlue(self, request: Request) -> bool:
        """
        将请求放入 scheduler_container容器
        :param request: 请求
        :return: None
        """
        self.log.debug(f"get a request {request} wating toschedlue ")
        # dont_filter=true的请求不过滤
        if not request.dont_filter:
            # retry 失败的 重试实现延迟调度
            _url = request.url + ":" + str(request.retry)
            contains = self.duplicate_filter.contains(_url)
            if inspect.isawaitable(contains):
                contains = await contains
            if contains:
                self.log.debug(f"duplicate_filter filted ... url{_url} ")
                return False
            filter_add = self.duplicate_filter.add(_url)
            if inspect.isawaitable(filter_add):
                await filter_add

        push = self.scheduler_container.push(request)
        if inspect.isawaitable(push):
            await push
        return True

    async def get(self) -> Optional[Request]:
        """
        从scheduler_container容器获取一个请求对象
        可能为空
        :return: Optional[Request]
        """
        self.log.debug(f"get a request to download task ")
        req = self.scheduler_container.pop()
        if inspect.isawaitable(req):
            req = await req
        return req
