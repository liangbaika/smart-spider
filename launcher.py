import asyncio
import atexit
import threading
import time
from multiprocessing.pool import Pool

from smart.log import log
from smart.pipline import Piplines
from smart.runer import CrawStater
from smart.setting import gloable_setting_dict
from smart.signal import reminder
from smart.spider import Spider
from spiders.db.sanicdb import SanicDB
from spiders.govs import GovsSpider, ArticelItem
from spiders.image_spider import ImageSpider
from spiders.ipspider2 import IpSpider3, GovSpider, IpSpider, ApiSpider
from spiders.js.js_spider import JsSpider, Broswer
from spiders.json_spider import JsonSpider
from test import middleware2

piplinestest = Piplines()


@piplinestest.pipline(1)
async def do_pip(spider_ins, item):
    print(f"我是item1111111 {item.results}")
    return item


@piplinestest.pipline(2)
def pip2(spider_ins, item):
    print(f"我是item2222222 {item.results}")
    return item


@piplinestest.pipline(3)
async def pip3(spider_ins, item):
    print(f"我是item33333 {item.results}")
    return item


db = SanicDB('localhost', 'testdb', 'root', 'root',
             minsize=5, maxsize=55,
             connect_timeout=10
             )


@atexit.register
def when_end():
    global db
    if db:
        db.close()


@piplinestest.pipline(3)
async def to_mysql_db(spider_ins, item):
    if item and isinstance(item, ArticelItem):
        print(f"我是item3 入库 {item.results}")
        global db
        last_id = await db.table_insert("art", item.results)
        print(f"last_id {last_id}")

    return item


def start1():
    starter = CrawStater()
    starter.run_single(IpSpider(), middlewire=middleware2, pipline=piplinestest)

#
# @reminder.spider_start.connect
# def test1(sender, **kwargs):
#     print("spider_start1")
#     return 1222222
#
#
# @reminder.spider_start.connect
# def test221(sender, **kwargs):
#     print("spider_start2")
#     return 33333333
#
#
# @reminder.spider_execption.connect
# def test2(sender, **kwargs):
#     print("spider_execption")
#
#
# @reminder.spider_close.connect
# def tes3t(sender, **kwargs):
#     print("spider_close")
#
#
# @reminder.engin_start.connect
# def test4(sender, **kwargs):
#     print("engin_start")
#
#
# @reminder.engin_idle.connect
# def test5(sender, **kwargs):
#     print("engin_idle")
#
#
# @reminder.engin_close.connect
# def test6(sender, **kwargs):
#     print("engin_close")
#
#
# @reminder.request_dropped.connect
# def test7(sender, **kwargs):
#     print("spider_start")
#
#
# @reminder.request_scheduled.connect
# def test8(sender, **kwargs):
#     print("request_scheduled")
#
#
# @reminder.response_received.connect
# def test9(sender, **kwargs):
#     print("response_received")
#
#
# @reminder.response_downloaded.connect
# def test10(sender, **kwargs):
#     print("response_downloaded")
#
#
# @reminder.item_dropped.connect
# def test11(sender, **kwargs):
#     print("spider_start")


if __name__ == '__main__':
    starter = CrawStater()
    spider1 = GovsSpider()
    spider2 = JsonSpider()
    js_spider = JsSpider()
    gloable_setting_dict.update(
        duplicate_filter_class="spiders.distributed.RedisBaseDuplicateFilter",
        scheduler_container_class="spiders.distributed.RedisSchuler",
        pipline_is_paralleled=1
    )

    spider = IpSpider()
    # starter.run_many([spider], middlewire=middleware2, pipline=piplinestest)
    starter.run_many([spider])

