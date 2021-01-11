# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      request
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      there is a python file description
# ------------------------------------------------------------------
from dataclasses import dataclass, field, InitVar
from typing import Callable

from smart.tool import is_valid_url


@dataclass
class Request:
    url: InitVar[str]
    callback: Callable = None
    method: str = 'get'
    timeout: float = None
    # if None will auto detect encoding
    encoding: str = None
    header: dict = None
    cookies: dict = None
    # post data
    data: any = None
    # http requets kwargs..
    extras: dict = None
    # different callback functions can be delivered
    meta: dict = None
    # do not filter repeat url
    dont_filter: bool = False
    # no more than  max retry times  and retry is delay retry
    _retry: int = 0

    def __post_init__(self, url):
        if is_valid_url(url):
            self.url = url
        else:
            raise ValueError(
                f"request url [{url}] is not a valid url,does it hava a schemas, url is valid like http://www.baidu.com")

    @property
    def retry(self):
        return self._retry

    @retry.setter
    def retry(self, value):
        if isinstance(value, int):
            self._retry = value
        else:
            raise ValueError("need a int value")
