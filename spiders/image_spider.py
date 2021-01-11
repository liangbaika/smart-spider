# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      ImageSpider
# Author:    liangbaikai
# Date:      2021/1/11
# Desc:      there is a python file description
# ------------------------------------------------------------------
# https://sme-1256044673.cos.ap-chengdu.myqcloud.com/suining/SUININGAE5BFB4AA624404F83491CAF53BE270E.JPG
from smart.item import Item
from smart.pipline import Piplines
from smart.response import Response
from smart.spider import Spider


class ImageItem(Item):
    img = None


pip = Piplines()


@pip.pipline(2)
def imgpip(spider_ins, item):
    print(f"imgpip {item.results}")
    with open("1222223.jpg", 'wb') as fd:
        fd.write(item.results.get('img'))
    return item


class ImageSpider(Spider):
    start_urls = [
        "https://sme-1256044673.cos.ap-chengdu.myqcloud.com/suining/SUININGAE5BFB4AA624404F83491CAF53BE270E.JPG"
    ]
    cutome_setting_dict = {**Spider.cutome_setting_dict, **{"piplines_instance": pip}}

    def parse(self, response: Response):
        print(response.content)
        item = ImageItem.get_item()
        item.img = response.content
        item.img = response.content
        item.img = response.content

        yield item
