import asyncio
import atexit
import multiprocessing
import threading
import time
from datetime import datetime
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
async def pip2(spider_ins, item):
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


@reminder.spider_start.connect
def rr(sender, **kwargs):
    print("spider_start1")
    return 1222222


@reminder.spider_start.connect
def gfgfgf(sender, **kwargs):
    print("spider_start2")
    return 33333333


@reminder.spider_execption.connect
def asa(sender, **kwargs):
    print("spider_execption")


@reminder.spider_close.connect
def dfd(sender, **kwargs):
    print("spider_close")


@reminder.engin_start.connect
def hhh(sender, **kwargs):
    print("engin_start")


@reminder.engin_idle.connect
def ggg(sender, **kwargs):
    print("engin_idle")


@reminder.engin_close.connect
def gggggg(sender, **kwargs):
    print("engin_close")


@reminder.request_dropped.connect
def rrr(sender, **kwargs):
    print("spider_start")


@reminder.request_scheduled.connect
def dsdsds(sender, **kwargs):
    print("request_scheduled")


@reminder.response_received.connect
def sasa(sender, **kwargs):
    print("response_received")


@reminder.response_downloaded.connect
def yyy(sender, **kwargs):
    print("response_downloaded")


@reminder.item_dropped.connect
def xxx(sender, **kwargs):
    print("spider_start")


def main():
    starter = CrawStater()
    spider1 = GovsSpider()
    spider2 = JsonSpider()
    js_spider = JsSpider()
    gloable_setting_dict.update(
        duplicate_filter_class="spiders.distributed.AioRedisBaseDuplicateFilter",
        scheduler_container_class="spiders.distributed.AioRedisSchuler",
        is_single=0,
    )
    spider = IpSpider()
    starter.run_many([spider], middlewire=middleware2, pipline=piplinestest)


if __name__ == '__main__':
    start = time.time()
    pool = multiprocessing.Pool(4)
    for i in range(4):
        pool.apply_async(main)
    # main()
    pool.close()
    pool.join()
    print(f'结束 花费{time.time() - start}s')

    # starter.run_many([spider])
