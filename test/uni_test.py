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


class TestItem(Item):
    # target_item = RegexField("\d+")
    age = RegexField("\d+", default="23222")

    age2 = 33

    def clean_age(self, value):
        return value


class TestClassOne(object):
    def test_response(self):
        request = Request("http://www.ocpe.com.cn/nengyuanjingji/zf/2020-08-29/3785.html")
        request.encoding = "utf-8"
        with open("test.html", "rb") as f:
            data = f.read()
            # data='{"code":200,"msg":"success","data":{"SYS_NAME":"职业院校综合管理与内部质量诊断与改进平台","LOGO":"/dfs/2020/11/05/20201105143318-47f7d6e3ca5637b23468330cab0ec0f3.jpg","BACKGROUND":"/dfs/2020/10/19/20201019194723-cdec006aef30e1e8313ac25eb2b71e38.png"}}'
            response = Response(data, 200, request)
            res = response.xpath("//div[@class='xwt_a']//a/text()").getall()
            print(res)
            print(response.links())

    def test_2(self):
        item = TestItem.get_item(html="sa11123s11s23sasasa01")
        print(item.results)
        # for _item in item:
        #     print(_item)

        pass

    def test3(self):
        x = """
        ss
        """
        title = RegexField(re_select='"title": "(.*?)",', re_flags=re.DOTALL).extract(x)
        print(title)
        print('\033[1;31;40m 1111111是1111111')


if __name__ == '__main__':
    pass
    print(isinstance(None,bool))
