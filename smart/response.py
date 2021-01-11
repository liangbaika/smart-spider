# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      response
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      there is a python file description
# ------------------------------------------------------------------
import json
from dataclasses import dataclass
from typing import List, Dict, Union, Any, Optional

import cchardet
from jsonpath import jsonpath
from parsel import Selector, SelectorList

from smart.tool import get_index_url
from .request import Request


@dataclass
class Response:
    body: bytes
    status: int
    request: Request = None
    headers: dict = None
    cookies: dict = None
    _selector: Selector = None

    def xpath(self, xpath_str) -> Union[SelectorList]:
        """
        个别html可能不兼容 导致无法搜索到结果
        :param xpath_str: xpath str
        :return: SelectorList
        """
        return self.selector.xpath(xpath_str)

    def css(self, css_str) -> Union[SelectorList]:
        return self.selector.css(css_str)

    def re(self, partern, replace_entities=True) -> List:
        return self.selector.re(partern, replace_entities)

    def re_first(self, partern, default=None, replace_entities=True) -> Any:
        return self.selector.re_first(partern, default, replace_entities)

    def json(self) -> Dict:
        return json.loads(self.text)

    def jsonpath(self, jsonpath_str) -> List:
        res = jsonpath(self.json(), jsonpath_str)
        return [] if isinstance(res, bool) and not res else res

    def get_base_url(self) -> str:
        return get_index_url(self.url)

    def urljoin(self, url) -> str:
        if url is None or url == '':
            raise ValueError("urljoin called, the url can not be empty")
        schema_suffix = "http"
        if url.startswith("%s" % schema_suffix):
            return url
        else:
            basr_url = self.get_base_url()
            return basr_url + url if url.startswith("/") else basr_url + "/" + url

    def links(self) -> List[str]:
        xpath = self.selector.xpath("//@href")
        full_urls = []
        for _item in xpath:
            link = _item.get()
            if link and "javascript:" not in link and len(link) > 1:
                if self.request:
                    link = self.urljoin(link)
                full_urls.append(link)
        return full_urls

    @property
    def selector(self) -> Selector:
        if not self._selector:
            self._selector = Selector(self.text)
        return self._selector

    @property
    def content(self) -> bytes:
        return self.body

    @property
    def content_type(self) -> Optional[str]:
        if self.headers:
            for key in self.headers.keys():
                if "content_type" == key.lower():
                    return self.headers.get(key)
        return None

    @property
    def text(self) -> Optional[str]:
        if not self.body:
            return None
        # if request encoding is none and then  auto detect encoding
        self.request.encoding = self.encoding or cchardet.detect(self.body)["encoding"]
        if self.request.encoding is None:
            raise UnicodeDecodeError(
                "body can not detect an encoding,it may be a binary data or you can set request.encoding to try it  ")
        # minimum possible may be UnicodeDecodeError
        return self.body.decode(self.encoding)

    @property
    def url(self) -> str:
        return self.request.url

    @property
    def meta(self) -> Dict:
        return self.request.meta

    @property
    def encoding(self) -> str:
        return self.request.encoding

    @property
    def ok(self) -> bool:
        return self.status == 0 or 200 <= self.status <= 299
