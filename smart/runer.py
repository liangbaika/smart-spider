# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      run
# Author:    liangbaikai
# Date:      2020/12/22
# Desc:      there is a python file description
# ------------------------------------------------------------------
import asyncio
import importlib
import inspect
import sys
import time
from asyncio import CancelledError
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List
from urllib.request import urlopen

from smart.log import log
from smart.core import Engine
from smart.middlewire import Middleware
from smart.pipline import Piplines
from smart.setting import gloable_setting_dict
from smart.spider import Spider
from smart.tool import is_valid_url

try:
    # uvloop  performance is better on  linux..
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


class CrawStater:
    __version = "0.1.0"

    def __init__(self, loop=None):
        if sys.platform == "win32":
            # avoid a certain extent: too many files error
            loop = loop or asyncio.ProactorEventLoop()
        else:
            self.loop = loop or asyncio.new_event_loop()
        thread_pool_max_size = gloable_setting_dict.get(
            "thread_pool_max_size", 30)
        loop.set_default_executor(ThreadPoolExecutor(thread_pool_max_size))
        asyncio.set_event_loop(loop)
        self.loop = loop
        self.cores = []
        self.log = log
        self.spider_names = []

    def run_many(self, spiders: List[Spider], middlewire: Middleware = None, pipline: Piplines = None):
        if not spiders or len(spiders) <= 0:
            raise ValueError("need spiders")
        for spider in spiders:
            if not isinstance(spider, Spider):
                raise ValueError("need a  Spider sub instance")
            _middle = spider.cutome_setting_dict.get("middleware_instance") or middlewire
            _pip = spider.cutome_setting_dict.get("piplines_instance") or pipline
            core = Engine(spider, _middle, _pip)
            self.cores.append(core)
            self.spider_names.append(spider.name)
        self._check_internet_state()
        self._run()

    def run_single(self, spider: Spider, middlewire: Middleware = None, pipline: Piplines = None):
        if not spider:
            raise ValueError("need a  Spider class or Spider sub instance")
        if not isinstance(spider, Spider):
            raise ValueError("need a   Spider sub instance")
        _middle = spider.cutome_setting_dict.get("middleware_instance") or middlewire
        _pip = spider.cutome_setting_dict.get("piplines_instance") or pipline
        core = Engine(spider, _middle, _pip)
        self.cores.append(core)
        self.spider_names.append(spider.name)
        self._run()

    def run(self, spider_module: str, spider_names: List[str] = [], middlewire: Middleware = None,
            pipline: Piplines = None):

        spider_module = importlib.import_module(f'{spider_module}')
        spider = [x for x in inspect.getmembers(spider_module,
                                                predicate=lambda x: inspect.isclass(x)) if
                  issubclass(x[1], Spider) and x[1] != Spider]
        if spider and len(spider) > 0:
            for tuple_item in spider:
                if (not spider_names or len(spider_names) <= 0) \
                        or tuple_item[1].name in spider_names:
                    _middle = tuple_item[1].cutome_setting_dict.get("middleware_instance") or middlewire
                    _pip = tuple_item[1].cutome_setting_dict.get("piplines_instance") or pipline
                    _spider = tuple_item[1]()
                    if not isinstance(_spider, Spider):
                        raise ValueError("need a   Spider sub instance")
                    core = Engine(_spider, _middle, _pip)
                    self.cores.append(core)
                    self.spider_names.append(_spider.name)
            self._run()

    def stop(self):
        self.log.info(f'warning stop be called,  {",".join(self.spider_names)} will stop ')
        for core in self.cores:
            self.loop.call_soon_threadsafe(core.close)

    def pause(self):
        self.log.info(f'warning pause be called,  {",".join(self.spider_names)} will pause ')
        for core in self.cores:
            self.loop.call_soon_threadsafe(core.pause)

    def recover(self):
        self.log.info(f'warning recover be called,  {",".join(self.spider_names)} will recover ')
        for core in self.cores:
            self.loop.call_soon_threadsafe(core.recover)

    def _run(self):
        start = time.time()
        tasks = []
        for core in self.cores:
            self.log.info(f'{core.spider.name} start run..')
            future = asyncio.ensure_future(core.start(), loop=self.loop)
            tasks.append(future)
        if len(tasks) <= 0:
            raise ValueError("can not finded spider tasks to start so ended...")
        self._print_info()
        try:
            group_tasks = asyncio.gather(*tasks, loop=self.loop)
            self.loop.run_until_complete(group_tasks)
        except CancelledError as e:
            self.log.debug(f" in loop, occured CancelledError e {e} ", exc_info=True)
        except KeyboardInterrupt as e2:
            self.log.debug(f" in loop, occured KeyboardInterrupt e {e2} ")
            self.stop()
        except BaseException as e3:
            self.log.error(f" in loop, occured BaseException e {e3} ", exc_info=True)

        self.log.info(f'craw succeed {",".join(self.spider_names)} ended.. it cost {round(time.time() - start, 3)} s')

    def _print_info(self):
        self.log.info("good luck!")
        self.log.info(
            """
                           _____                      _          _____       _     _           
              / ____|                    | |        / ____|     (_)   | |          
             | (___  _ __ ___   __ _ _ __| |_ _____| (___  _ __  _  __| | ___ _ __ 
              \___ \| '_ ` _ \ / _` | '__| __|______\___ \| '_ \| |/ _` |/ _ \ '__|
              ____) | | | | | | (_| | |  | |_       ____) | |_) | | (_| |  __/ |   
             |_____/|_| |_| |_|\__,_|_|   \__|     |_____/| .__/|_|\__,_|\___|_|   
                                                          | |                      
                                                          |_|                      
            
            """
        )
        self.log.info(" \r\n smart-spider-framework"
                      f"\r\n os: {sys.platform}"
                      " \r\n author: liangbaikai<1144388620@qq.com>"
                      f" \r\n version: {self.__version}"
                      " \r\n proverbs: whatever is worth doing is worth doing well."
                      )

    @classmethod
    def _check_internet_state(cls):
        error_msg = "internet may not be available please check net, run ended"
        net_healthy_check_url = gloable_setting_dict.get("net_healthy_check_url", None)
        if net_healthy_check_url is None:
            return
        if not is_valid_url(net_healthy_check_url):
            return
        try:
            resp = urlopen(url=net_healthy_check_url, timeout=10)
            if not 200 <= resp.status <= 299:
                raise RuntimeError(error_msg)
        except Exception:
            raise RuntimeError(error_msg)
