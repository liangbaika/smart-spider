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
from types import AsyncGeneratorType, GeneratorType
from typing import Dict, Any

import typing

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
        self.request_generator_queue = asyncio.Queue()

        self.stop = False
        self.condition = asyncio.Condition()
        self.item_queue = asyncio.Queue()
        pipline_is_paralleled = self.spider.cutome_setting_dict.get("pipline_is_paralleled")
        pipline_is_paralleled = gloable_setting_dict.get(
            "pipline_is_paralleled") if pipline_is_paralleled is None else pipline_is_paralleled
        self.pipline_is_paralleled = pipline_is_paralleled

        self.lock1 = asyncio.Lock()
        self.lock2 = asyncio.Lock()
        self.worker_tasks = []

    def _get_dynamic_class_setting(self, key):
        class_str = self.spider.cutome_setting_dict.get(key) or gloable_setting_dict.get(key)
        _module = importlib.import_module(".".join(class_str.split(".")[:-1]))
        _class = getattr(_module, class_str.split(".")[-1])
        self.log.info(f"dynamic loaded  key【{key}】--> class【{class_str}】success")
        return _class

    async def process_start_urls(self):
        """
        Process the start URLs
        :return: AN async iterator
        """
        for req in self.spider:
            yield req

    async def start(self):
        self.spider.on_start()
        self.reminder.go(Reminder.spider_start, self.spider)
        self.reminder.go(Reminder.engin_start, self)
        async for request_ins in self.process_start_urls():
            self.request_generator_queue.put_nowait(self.handle_request(request_ins))
        workers = [
            asyncio.ensure_future(self.start_worker())
            for _ in range(3)
        ]
        await self.request_generator_queue.join()
        for t in workers:
            await t

        self.spider.state = "closed"
        self.reminder.go(Reminder.spider_close, self.spider)
        self.spider.on_close()
        # for _t in works + handle_items:
        #     _t.cancel()
        self.reminder.go(Reminder.engin_close, self)
        self.log.debug(f" engine stoped..")

    async def handle_request(
            self, _request: Request
    ):
        """
        Wrap request with middleware.
        :param request:
        :return:
        """
        # pass_through
        request = await self._pass_through_schedule(_request)
        callback_result, response = None, None
        try:
            setattr(request, "__spider__", self.spider)
            response = await self.downloader.download(request)
            if response is None:
                return
            if request.callback:
                if inspect.iscoroutinefunction(request.callback):
                    callback_result = await request.callback(response)
                else:
                    callback_result = request.callback(response)
        except Exception as e:
            self.log.error(f"<Callback[{request.callback.__name__}]: {e}")

        return callback_result, response

    def _handle_exception(self, spider, e):
        if spider:
            try:
                self.log.error(f"  occured exceptyion e {e} ", exc_info=True)
                spider.on_exception_occured(e)
            except BaseException:
                pass

    async def start_worker(self):
        while True:
            request_item = await self.request_generator_queue.get()
            self.worker_tasks.append(request_item)
            if self.request_generator_queue.empty():
                results = await asyncio.gather(
                    *self.worker_tasks, return_exceptions=True
                )
                for task_result in results:
                    if not isinstance(task_result, RuntimeError) and task_result:
                        callback_results, response = task_result
                        if isinstance(callback_results, (AsyncGeneratorType, GeneratorType)):
                            await self._process_async_callback(
                                callback_results, response
                            )
                    else:
                        print("task_result",task_result)
                self.worker_tasks = []
            self.request_generator_queue.task_done()

    async def _process_async_callback(
            self, callback_results: AsyncGeneratorType, response: Response = None
    ):
        try:
            if isinstance(callback_results, AsyncGeneratorType):
                async for callback_result in callback_results:
                    if isinstance(callback_result, AsyncGeneratorType):
                        await self._process_async_callback(callback_result)
                    elif isinstance(callback_result, Request):
                        self.request_generator_queue.put_nowait(
                            self.handle_request(callback_result)
                        )
                    elif isinstance(callback_result, typing.Coroutine):
                        self.request_generator_queue.put_nowait(
                            self.handle_callback(
                                aws_callback=callback_result, response=response
                            )
                        )
                    elif isinstance(callback_result, Item):
                        # Process target item
                        # self._hand_piplines(self.spider, callback_result, paralleled=self.pipline_is_paralleled)
                        print('item 暂时不处理')
                        # await self.process_item(callback_result)
                    else:
                        pass
                    # await self.process_callback_result(callback_result=callback_result)

                pass
            else:
                for callback_result in callback_results:
                    if isinstance(callback_result, GeneratorType):
                        await self._process_async_callback(callback_result)
                    elif isinstance(callback_result, Request):
                        self.request_generator_queue.put_nowait(
                            self.handle_request(callback_result)
                        )
                    elif isinstance(callback_result, typing.Coroutine):
                        self.request_generator_queue.put_nowait(
                            self.handle_callback(
                                aws_callback=callback_result, response=response
                            )
                        )
                    elif isinstance(callback_result, Item):
                        # Process target item
                        # self._hand_piplines(self.spider, callback_result, paralleled=self.pipline_is_paralleled)
                        print('item 暂时不处理')
                        # await self.process_item(callback_result)
                    else:
                        pass
        except Exception as e:
            self.log.error(e)

    async def handle_callback(self, aws_callback: typing.Coroutine, response):
        """
        Process coroutine callback function
        """
        callback_result = None
        try:
            callback_result = await aws_callback

        except Exception as e:
            self.log.exception(f"<Callback[{aws_callback.__name__}]: {e}")
        return callback_result, response

    async def _pass_through_schedule(self, request):
        if request:
            none_or_iscoroutinefunction_ = self.scheduler.schedlue(request)
            if inspect.isawaitable(none_or_iscoroutinefunction_):
                await none_or_iscoroutinefunction_
        request_or_iscoroutinefunction_ = self.scheduler.get()
        if inspect.isawaitable(request_or_iscoroutinefunction_):
            request_or_iscoroutinefunction_ = await request_or_iscoroutinefunction_
        return request_or_iscoroutinefunction_
