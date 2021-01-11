# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      core
# Author:    liangbaikai
# Date:      2020/12/22
# Desc:      there is a python file description
# ------------------------------------------------------------------
import asyncio
import importlib
import inspect
import time
import traceback
import uuid
from asyncio import Lock
from collections import deque
from contextlib import suppress
from typing import Dict

from smart.log import log
from smart.downloader import Downloader
from smart.item import Item
from smart.pipline import Piplines
from smart.request import Request
from smart.scheduler import Scheduler
from smart.setting import gloable_setting_dict


class Engine:
    def __init__(self, spider, middlewire=None, pipline: Piplines = None):
        self.lock = None
        self.task_dict: Dict[str, asyncio.Task] = {}
        self.pip_task_dict: Dict[str, asyncio.Task] = {}
        self.spider = spider
        self.middlewire = middlewire
        self.piplines = pipline
        duplicate_filter_class = self._get_dynamic_class_setting("duplicate_filter_class")
        scheduler_container_class = self._get_dynamic_class_setting("scheduler_container_class")
        net_download_class = self._get_dynamic_class_setting("net_download_class")
        self.scheduler = Scheduler(duplicate_filter_class(), scheduler_container_class())
        req_per_concurrent = self.spider.cutome_setting_dict.get("req_per_concurrent") or gloable_setting_dict.get(
            "req_per_concurrent")
        self.downloader = Downloader(self.scheduler, self.middlewire, seq=req_per_concurrent,
                                     downer=net_download_class())
        self.request_generator_queue = deque()
        self.stop = False
        self.log = log

    def _get_dynamic_class_setting(self, key):
        class_str = self.spider.cutome_setting_dict.get(
            key) or gloable_setting_dict.get(
            key)
        _module = importlib.import_module(".".join(class_str.split(".")[:-1]))
        _class = getattr(_module, class_str.split(".")[-1])
        return _class

    def iter_request(self):
        while True:
            if not self.request_generator_queue:
                yield None
                continue
            request_generator = self.request_generator_queue[0]
            spider, real_request_generator = request_generator[0], request_generator[1]
            try:
                # execute and get a request from cutomer code
                # request=real_request_generator.send(None)
                request_or_item = next(real_request_generator)
                if isinstance(request_or_item, Request):
                    request_or_item.__spider__ = spider
            except StopIteration:
                self.request_generator_queue.popleft()
                continue
            except Exception as e:
                # 可以处理异常
                self.request_generator_queue.popleft()
                self._handle_exception(spider, e)
                continue
            yield request_or_item

    def _check_complete_pip(self, task):
        if task.cancelled():
            self.log.debug(f" a task canceld ")
            return
        if task and task.done() and task._key:
            if task.exception():
                self.log.error(f"a task  occurer error in pipline {task.exception()}  ")
            else:
                self.log.debug(f"a task done  ")
                result = task.result()
                if result and isinstance(result, Item):
                    if hasattr(task, '_index'):
                        self._hand_piplines(task._spider, result, task._index + 1)
            self.pip_task_dict.pop(task._key)

    def _check_complete_callback(self, task):
        if task.cancelled():
            self.log.debug(f" a task canceld ")
            return
        if task and task.done() and task._key:
            self.log.debug(f"a task done  ")
            self.task_dict.pop(task._key)

    async def start(self):
        self.spider.on_start()
        # self.spider
        self.request_generator_queue.append((self.spider, iter(self.spider)))
        # self.request_generator_queue.append( iter(self.spider))
        # core  implenment
        while not self.stop:
            # paused
            if self.lock and self.lock.locked():
                await asyncio.sleep(1)
                continue

            request_or_item = next(self.iter_request())
            if isinstance(request_or_item, Request):
                self.scheduler.schedlue(request_or_item)

            if isinstance(request_or_item, Item):
                self._hand_piplines(self.spider, request_or_item)

            request = self.scheduler.get()
            can_stop = self._check_can_stop(request)
            # if request is None and not self.task_dict:
            if can_stop:
                # there is no request and the task has been completed.so ended
                self.log.debug(
                    f" here is no request and the task has been completed.so  engine will stop ..")
                self.stop = True
                break
            if isinstance(request, Request):
                self._ensure_future(request)

            resp = self.downloader.get()

            if resp is None:
                # let the_downloader can be scheduled, test 0.001-0.0006 is better
                await asyncio.sleep(0.0005)
                continue

            custome_callback = resp.request.callback
            if custome_callback:
                request_generator = custome_callback(resp)
                if request_generator:
                    self.request_generator_queue.append((custome_callback.__self__, request_generator))
                    # self.request_generator_queue.append( request_generator)
            if self.spider.state != "runing":
                self.spider.state = "runing"

        self.spider.state = "closed"
        self.spider.on_close()
        self.log.debug(f" engine stoped..")
        await asyncio.sleep(0.15)

    def pause(self):
        self.log.info(f" out called pause.. so engine will pause.. ")
        asyncio.create_task(self._lock())
        self.spider.state = "pause"

    def recover(self):
        if self.lock and self.lock.locked():
            self.log.info(f" out called recover.. so engine will recover.. ")
            self.lock.release()

    def close(self):
        # can make external active end engine
        self.stop = True
        tasks = asyncio.all_tasks()
        for it in tasks:
            it.cancel()
        asyncio.gather(*tasks, return_exceptions=True)
        self.log.debug(f" out called stop.. so engine close.. ")

    async def _lock(self):
        if self.lock is None:
            self.lock = Lock()
        await self.lock.acquire()

    def _ensure_future(self, request: Request):
        # compatible py_3.6
        task = asyncio.ensure_future(self.downloader.download(request))
        key = str(uuid.uuid4())
        task._key = key
        self.task_dict[key] = task
        task.add_done_callback(self._check_complete_callback)

    def _handle_exception(self, spider, e):
        if spider:
            try:
                self.log.error(f"  occured exceptyion e {e} ", exc_info=True)
                spider.on_exception_occured(e)
            except BaseException:
                pass

    def _check_can_stop(self, request):
        if request:
            return False
        if len(self.task_dict) > 0:
            return False
        if len(self.request_generator_queue) > 0:
            return False
        if self.downloader.response_queue.qsize() > 0:
            return False
        if len(self.pip_task_dict) > 0:
            return False
        return True

    def _hand_piplines(self, spider_ins, item, index=0):
        if self.piplines is None or len(self.piplines.piplines) <= 0:
            self.log.info("get a item but can not  find a piplinse to handle it so ignore it ")
            return

        if len(self.piplines.piplines) < index + 1:
            return

        pip = self.piplines.piplines[index][1]

        if not callable(pip):
            return

        if not inspect.iscoroutinefunction(pip):
            task = asyncio.get_running_loop().run_in_executor(None, pip, spider_ins, item)
        else:
            task = asyncio.ensure_future(pip(spider_ins, item))
        key = str(uuid.uuid4())
        task._key = key
        task._index = index
        task._spider = spider_ins
        self.pip_task_dict[key] = task
        task.add_done_callback(self._check_complete_pip)
