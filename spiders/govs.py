# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      govs
# Author:    liangbaikai
# Date:      2021/1/6
# Desc:      there is a python file description
# ------------------------------------------------------------------
import asyncio
import traceback

import aiohttp

from smart.field import HtmlField
from smart.item import Item
from smart.request import Request
from smart.response import Response
from smart.spider import Spider


class ArticelItem(Item):
    title = HtmlField(xpath_select="//*[@class='titles']/text()")
    pub_time = HtmlField(xpath_select="//*[@class='times']/text()")
    author = HtmlField(xpath_select="//*[@class='author']/text()")
    content = HtmlField(xpath_select="//div[@class='article-content']")


class GovsSpider(Spider):
    name = "GovsSpider"
    start_urls = [
        "http://www.nea.gov.cn/policy/jd.htm"
    ]
    cutome_setting_dict = {**Spider.cutome_setting_dict,
                           # **{
                           #     "req_delay": 3,
                           #     "req_per_concurrent": 3,
                           # }
                           }

    def parse(self, response: Response):
        selects_detail_urls = response.xpath(
            '//*[@class="list"]//li//a/@href').getall()
        if len(selects_detail_urls) > 0:
            for detail_url in selects_detail_urls:
                yield Request(url=detail_url,
                              callback=self.parse_detail)
        next = response.xpath('//*[@id="div_currpage"]//a[text()="下一页"]')
        if next:
            next_url = response.xpath(
                '//*[@id="div_currpage"]//a[text()="下一页"]/@href').get()
            yield Request(url=next_url, callback=self.parse)

    def parse_detail(self, response):
        yield ArticelItem.get_item(html=response.text)

    def on_exception_occured(self, e: Exception):
        print(e)


