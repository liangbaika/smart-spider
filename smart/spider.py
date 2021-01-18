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
    # 名称
    name: str = f'smart-spider-{uuid.uuid4()}'

    # 生命周期状态:  init | runing | paused | closed
    state: str = "init"

    # 起始urls
    start_urls: List[str] = []

    # 自定义的设置  没有的话就取全局的设置默认值
    cutome_setting_dict = {
        # 请求延迟  默认10s
        "req_delay": None,
        # 每个爬虫的请求并发数 默认100
        "req_per_concurrent": None,
        # 每个请求的最大重试次数 默认 3
        "req_max_try": None,
        # 默认请求头
        "default_headers": None,
        # 根据响应的状态码 默认忽略以下响应 [401, 403, 404, 405, 500, 502, 504],
        "ignore_response_codes": None,
        # 默认无 此处配置对象
        "middleware_instance": None,
        # 默认无  此处配置对象
        "piplines_instance": None,
        # 请求url 去重处理器
        # 自己实现需要继承 BaseDuplicateFilter 实现相关抽象方法 系统默认 smart.scheduler.SampleDuplicateFilter
        "duplicate_filter_class": None,
        # 请求url调度器容器
        # 自己实现需要继承 BaseSchedulerContainer 实现相关抽象方法  系统默认smart.scheduler.DequeSchedulerContainer
        "scheduler_container_class": None,
        # 请求网络的方法  输入 request  输出 response
        # 自己实现需要继承 BaseDown 实现相关抽象方法  系统默认 smart.downloader.AioHttpDown
        "net_download_class": None,
    }

    def start_requests(self):
        """
        初始请求 用户可以重写此方法
        :return:
        """
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    @abstractmethod
    def parse(self, response: Response):
        """
        回调函数 用户实现
        :param response: 响应对象
        :return:
        """
        ...

    def __iter__(self):
        yield from self.start_requests()
