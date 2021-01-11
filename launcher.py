import asyncio
import atexit
import threading
import time
from multiprocessing.pool import Pool

from smart.log import log
from smart.pipline import Piplines
from smart.runer import CrawStater
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
    return item


@piplinestest.pipline(2)
def pip2(spider_ins, item):
    print(f"我是item2 {item.results}")
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


if __name__ == '__main__':
    starter = CrawStater()
    spider1 = GovsSpider()
    spider2 = JsonSpider()
    js_spider = JsSpider()
    starter.run_many([spider1], middlewire=middleware2, pipline=piplinestest)
