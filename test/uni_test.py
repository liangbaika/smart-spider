# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      uni_test
# Author:    liangbaikai
# Date:      2021/1/5
# Desc:      there is a python file description
# ------------------------------------------------------------------
import copy
import re
from dataclasses import asdict, fields

from smart.field import RegexField, BaseField, HtmlField
from smart.item import Item
from smart.request import Request
from smart.response import Response
from smart.tool import is_valid_url


class TestItem(Item):
    # target_item = RegexField("\d+")
    age = RegexField("\d+", default="23222")
    age2 = 33

    def clean_age(self, value):
        return value


class TestClassOne(object):
    def test_1(self):
        request = Request("http://www.ocpe.com.cn/nengyuanjingji/zf/2020-08-29/3785.html")
        request.encoding = "utf-8"
        with open("test.html", "rb") as f:
            data = f.read()
            # data='{"code":200,"msg":"success","data":{"SYS_NAME":"职业院校综合管理与内部质量诊断与改进平台","LOGO":"/dfs/2020/11/05/20201105143318-47f7d6e3ca5637b23468330cab0ec0f3.jpg","BACKGROUND":"/dfs/2020/10/19/20201019194723-cdec006aef30e1e8313ac25eb2b71e38.png"}}'
            response = Response(data, 200, request)
            res = response.xpath("//div[@class='xwt_a']//a/text()").getall()
            print(response.links())
            print(res)

    def test_2(self):
        item = TestItem.get_item(html="sa11123s11s23sasasa01")
        print(item.results)

    def test3(self):
        print(is_valid_url("http://www.baidu.com"))
