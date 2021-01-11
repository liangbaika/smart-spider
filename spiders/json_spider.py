# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      JsonSpider
# Author:    liangbaikai
# Date:      2021/1/7
# Desc:      there is a python file description
# ------------------------------------------------------------------
import re
import traceback

from smart.field import JsonPathField, RegexField
from smart.item import Item
from smart.response import Response
from smart.spider import Spider


class BidItem(Item):
    target_item = JsonPathField(json_path="$.data.records.*")

    cate = JsonPathField(json_path="$..cate")
    city = JsonPathField(json_path="$..city")
    pub_time = JsonPathField(json_path="$..pub_time")
    title = RegexField(re_select='"title":.?"(.*?)",')

    def clean_city(self, value):
        return value + "省"


class JsonSpider(Spider):
    name = "JsonSpider"
    start_urls = [
        "http://139.155.14.219:8529/suining/bid/pageTop?current=1&size=50&sort=id,desc"
    ]

    def parse(self, response: Response):
        yield from BidItem.get_items(response.text)
