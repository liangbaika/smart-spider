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
import random
import time
import uuid
from asyncio import Lock, QueueEmpty
from collections import deque
from contextlib import suppress
from typing import Dict, Any

from smart.log import log
from smart.downloader import Downloader
from smart.item import Item
from smart.pipline import Piplines
from smart.request import Request
from smart.response import Response
from smart.scheduler import Scheduler, DequeSchedulerContainer, AsyncScheduler
from smart.setting import gloable_setting_dict
from smart.signal import reminder, Reminder


class Engine:
    def __init__(self, spider, middlewire=None, pipline: Piplines = None):
        self.reminder = reminder
        self.log = log
        self.lock = None
        self.task_dict: Dict[str, Any] = {}
        self.pip_task_dict: Dict[str, asyncio.Task] = {}
        self.spider = spider
        self.middlewire = middlewire
        self.piplines = pipline
        duplicate_filter_class = self._get_dynamic_class_setting("duplicate_filter_class")
        scheduler_container_class = self._get_dynamic_class_setting("scheduler_container_class")
        net_download_class = self._get_dynamic_class_setting("net_download_class")
        scheduler_class = self._get_dynamic_class_setting("scheduler_class")
        self.scheduler = scheduler_class(duplicate_filter_class(), scheduler_container_class())
        req_per_concurrent = self.spider.cutome_setting_dict.get("req_per_concurrent") or gloable_setting_dict.get(
            "req_per_concurrent")
        single = self.spider.cutome_setting_dict.get("is_single")
        self.is_single = gloable_setting_dict.get("is_single") if single is None else single
        self.downloader = Downloader(self.scheduler, self.middlewire, reminder=self.reminder,
                                     seq=req_per_concurrent,
                                     downer=net_download_class())
        self.request_generator_queue = deque()
        self.stop = False
        self.condition = asyncio.Condition()
        self.item_queue = asyncio.Queue()
        pipline_is_paralleled = self.spider.cutome_setting_dict.get("pipline_is_paralleled")
        pipline_is_paralleled = gloable_setting_dict.get(
            "pipline_is_paralleled") if pipline_is_paralleled is None else pipline_is_paralleled
        self.pipline_is_paralleled = pipline_is_paralleled

        self.lock1 = asyncio.Lock()
        self.lock2 = asyncio.Lock()

    def _get_dynamic_class_setting(self, key):
        class_str = self.spider.cutome_setting_dict.get(key) or gloable_setting_dict.get(key)
        _module = importlib.import_module(".".join(class_str.split(".")[:-1]))
        _class = getattr(_module, class_str.split(".")[-1])
        self.log.info(f"dynamic loaded  key【{key}】--> class【{class_str}】success")
        return _class

    def iter_request(self):
        while True:
            if not self.request_generator_queue:
                yield None
                continue
            request_generator = self.request_generator_queue[0]
            spider, real_request_generator = request_generator[0], request_generator[1]
            try:
                request_or_item = next(real_request_generator)
            except StopIteration:
                self.request_generator_queue.popleft()
                continue
            except Exception as e:
                # 可以处理异常
                self.request_generator_queue.popleft()
                self._handle_exception(spider, e)
                self.reminder.go(Reminder.spider_execption, spider, exception=e)
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
                        self._hand_piplines(task._spider, result, index=task._index + 1, paralleled=False)
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
        self.reminder.go(Reminder.spider_start, self.spider)
        self.reminder.go(Reminder.engin_start, self)

        self.request_generator_queue.append((self.spider, iter(self.spider)))
        handle_items = [asyncio.ensure_future(self.handle_item()) for _ in range(50)]
        works = [asyncio.ensure_future(self.work()) for _ in range(50)]
        while not self.stop:
            # 是否暂停了
            if self.lock and self.lock.locked():
                await asyncio.sleep(0.5)
                continue
            # 若是分布式爬虫 让内存里的任务不过堆积过多 尽量均分给其他机器
            if self.is_single:
                if len(self.task_dict) > 1500:
                    await asyncio.sleep(0.3)
            waited, wait = False, None
            user_func_res = next(self.iter_request())
            if isinstance(user_func_res, Request):
                wait = self.scheduler.schedlue(user_func_res)

            if isinstance(user_func_res, (dict, Item)):
                wait = self.item_queue.put(user_func_res)
            if wait is not None and inspect.isawaitable(wait):
                waited = True
                await wait

            await asyncio.sleep(0.001)
            if self._check_can_stop(None):
                # there is no request and the task has been completed.so ended
                self.log.debug(" here is no request and the task has been completed.so  engine will stop ..")
                self.stop = True
                break
            if self.spider.state != "runing":
                self.spider.state = "runing"

            # if not waited:
            #     await asyncio.sleep(0.001)
            # if user_func_res is None or not wait:
            #     await self.lock1.acquire()

        self.spider.state = "closed"
        self.reminder.go(Reminder.spider_close, self.spider)
        self.spider.on_close()
        for _t in works + handle_items:
            _t.cancel()
        self.reminder.go(Reminder.engin_close, self)
        self.log.debug(f" engine stoped..")

    async def work(self):
        seed = False
        while not self.stop:
            waited = False
            request = self.scheduler.get()
            if inspect.isawaitable(request):
                waited = True
                request = await request
            resp = None
            if isinstance(request, Request):
                setattr(request, "__spider__", self.spider)
                self.reminder.go(Reminder.request_scheduled, request)
                if waited:
                    resp = await self._ensure_future_special(request)
                else:
                    self._ensure_future(request)
            _resp = self.downloader.get()
            if not resp:
                resp = _resp

            if resp is None:
                if not waited:
                    await asyncio.sleep(0.004)
                # let the_downloader can be scheduled, test 0.001-0.0006 is better
                # uniform = random.uniform(0.0001, 0.006)
                if not seed:
                    await asyncio.sleep(0.03)
                seed = not seed
                continue
            custome_callback = resp.request.callback
            if custome_callback:
                request_generator = custome_callback(resp)
                if request_generator:
                    self.request_generator_queue.append((custome_callback.__self__, request_generator))


    @staticmethod
    async def cancel_all_tasks():
        tasks = []
        for task in asyncio.Task.all_tasks():
            if task is not asyncio.tasks.Task.current_task():
                tasks.append(task)
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def pause(self):
        # self.log.info(f" out called pause.. so engine will pause.. ")
        asyncio.create_task(self._lock())
        self.spider.state = "pause"

    def recover(self):
        if self.lock and self.lock.locked():
            # self.log.info(f" out called recover.. so engine will recover.. ")
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

    async def _ensure_future_special(self, request: Request):
        # compatible py_3.6
        key = str(uuid.uuid4())
        self.task_dict[key] = request
        resp = await self.downloader.download(request)
        self.task_dict.pop(key)
        return resp

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
        if len(self.pip_task_dict) > 0:
            return False
        if len(self.request_generator_queue) > 0:
            return False
        if self.item_queue.qsize() > 0:
            return False
        if self.downloader.response_queue.qsize() > 0:
            return False
        if len(self.request_generator_queue) > 0 and self.scheduler.scheduler_container.size() > 0:
            return False
        return  True
        # if self.scheduler.scheduler_container.size() > 0:
        #     return False
        start = time.time()
        self.reminder.go(Reminder.engin_idle, self)
        while not self.is_single:
            end = time.time()
            period = 5
            if (end - start) > period:
                self.log.info(f"empty loop {period}s second so stop")
                break
            if self.scheduler.scheduler_container.size() <= 0:
                time.sleep(0.1)
            else:
                return False
        self.log.info("craw end ,engin will stop")
        return True

    def _run_pip_async(self, pip, spider_ins, item, index, paralleled=False):
        if not inspect.iscoroutinefunction(pip):
            task = asyncio.get_running_loop().run_in_executor(None, pip, spider_ins, item)
        else:
            task = asyncio.ensure_future(pip(spider_ins, item))
        key = str(uuid.uuid4())
        task._key = key
        if not paralleled:
            task._index = index
        task._spider = spider_ins
        self.pip_task_dict[key] = task
        task.add_done_callback(self._check_complete_pip)

    def _hand_piplines(self, spider_ins, item, index=0, paralleled=False):
        if self.piplines is None or len(self.piplines.piplines) <= 0:
            self.log.debug("get a item but can not  find a piplinse to handle it so ignore it ")
            return
        if paralleled:
            for order, pip in self.piplines.piplines:
                if not callable(pip):
                    continue
                self._run_pip_async(pip, spider_ins, item, index, paralleled)
        else:
            if not paralleled and len(self.piplines.piplines) < index + 1:
                return
            pip = self.piplines.piplines[index][1]
            if not callable(pip):
                return
            self._run_pip_async(pip, spider_ins, item, index, paralleled)

    async def handle_item(self):
        while not self.stop:
            if self.item_queue.qsize() <= 0:
                await asyncio.sleep(0.2)

            item = await self.item_queue.get()

            self.item_queue.task_done()
            # item = self.item_queue.get_nowait()
            self._hand_piplines(self.spider, item, paralleled=self.pipline_is_paralleled)

