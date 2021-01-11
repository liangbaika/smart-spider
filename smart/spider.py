# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      spider
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      there is a  abstract spider
# ------------------------------------------------------------------
from abc import ABC, abstractmethod
import uuid
from typing import List

from smart.request import Request
from smart.response import Response


class SpiderHook(ABC):

    def on_start(self):
        pass

    def on_close(self):
        pass

    def on_exception_occured(self, e: Exception):
        pass


class Spider(SpiderHook):
    name: str = f'smart-spider-{uuid.uuid4()}'

    # spider leaf state:  init | runing | paused | closed
    state: str = "init"

    start_urls: List[str] = []

    cutome_setting_dict = {
        # 请求延迟
        "req_delay": None,
        # 每个爬虫的请求并发数
        "req_per_concurrent": None,
        # 每个请求的最大重试次数
        "req_max_try": None,
        # 默认请求头
        "default_headers": None,
        # 根据响应的状态码 忽略以下响应
        "ignore_response_codes": None,
        "middleware_instance": None,
        "piplines_instance": None,
        # 请求url 去重处理器
        # 自己实现需要继承 BaseDuplicateFilter 实现相关抽象方法 系统默认SampleDuplicateFilter
        "duplicate_filter_class": "smart.scheduler.SampleDuplicateFilter",
        # 请求url调度器容器
        # 自己实现需要继承 BaseSchedulerContainer 实现相关抽象方法  系统默认DequeSchedulerContainer
        "scheduler_container_class": "smart.scheduler.DequeSchedulerContainer",
        # 请求网络的方法  输入 request  输出 response
        # 自己实现需要继承 BaseDown 实现相关抽象方法  系统默认AioHttpDown
        "net_download_class": "smart.downloader.AioHttpDown",
    }

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    @abstractmethod
    def parse(self, response: Response):
        ...

    def __iter__(self):
        yield from self.start_requests()
