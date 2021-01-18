# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      request
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      request desc
# ------------------------------------------------------------------
from dataclasses import dataclass, InitVar
from typing import Callable, Any

from smart.tool import is_valid_url


@dataclass
class Request:
    """
    请求对象  分分布式条件下需要保证此对象能被序列化
    """

    # 请求地址
    url: InitVar[str]
    # 回调函数
    callback: Callable = None
    # session
    session: Any = None
    # 请求方法 都支持
    method: str = 'get'
    # 超时时间 默认10 s
    timeout: float = None
    # 编码 尽量不传  框架会自动探测
    encoding: str = None
    # 请求头
    header: dict = None
    # 请求cookies 字典
    cookies: dict = None
    # post data
    data: any = None
    # http requets kwargs..
    extras: dict = None
    # meta 可以传递值
    meta: dict = None
    # 是否过滤请求 默认过滤
    dont_filter: bool = False
    # 已经重试请求的次数 超过最大重试次数 将被丢弃 触发对应的信号机制
    _retry: int = 0

    def __post_init__(self, url):
        """
        初始化钩子 验证下 url是否合法
        没有schema的将自动添加 http:// 前缀
        :param url: 请求地址
        :return: none
        """
        if url is None or url == '':
            raise ValueError("request url can not be empty ")
        if url and not (url.startswith("http") or url.startswith("ftp")):
            url = "http://" + url
        if is_valid_url(url):
            self.url = url
        else:
            raise ValueError(
                f"request url [{url}] is not a valid url,does it hava a schemas, url is valid like http://www.baidu.com")

    @property
    def retry(self) -> int:
        """
        已经重试的次数
        :return: int
        """
        return self._retry

    @retry.setter
    def retry(self,value):
        self._retry=self._retry+value
