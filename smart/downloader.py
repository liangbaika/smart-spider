# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      downloader
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      there is a python file description
# ------------------------------------------------------------------
import asyncio
import inspect
from abc import ABC, abstractmethod
from asyncio import Queue, QueueEmpty
from contextlib import suppress
from typing import Optional
import aiohttp
from concurrent.futures import TimeoutError

from smart.log import log
from smart.middlewire import Middleware
from smart.response import Response
from smart.scheduler import Scheduler
from smart.setting import gloable_setting_dict
from .request import Request


class BaseDown(ABC):

    @abstractmethod
    def fetch(self, request: Request) -> Response:
        pass


class AioHttpDown(BaseDown):

    async def fetch(self, request: Request) -> Response:
        session = None
        resp = None
        try:
            session = request.session or aiohttp.ClientSession()
            resp = await session.request(request.method,
                                         request.url,
                                         timeout=request.timeout or 10,
                                         headers=request.header or {},
                                         cookies=request.cookies or {},
                                         data=request.data or {},
                                         **request.extras or {}
                                         )
            byte_content = await resp.read()
            headers = {}
            if resp.headers:
                headers = {k: v for k, v in resp.headers.items()}
            response = Response(body=byte_content,
                                status=resp.status,
                                headers=headers,
                                cookies=resp.cookies
                                )
        finally:
            if resp:
                resp.release()
            if request.session is None and session:
                await session.close()

        return response


class Downloader:

    def __init__(self, scheduler: Scheduler, middwire: Middleware = None, seq=100, downer: BaseDown = AioHttpDown()):
        self.log = log
        self.scheduler = scheduler
        self.middwire = middwire
        self.response_queue: asyncio.Queue = Queue()
        #  the file handle opens too_much to report an error
        self.semaphore = asyncio.Semaphore(seq)
        # the real to fetch resource from internet
        self.downer = downer
        self.log.info(f" downer loaded {self.downer.__class__.__name__}")

    async def download(self, request: Request):
        spider = request.__spider__
        max_retry = spider.cutome_setting_dict.get("req_max_retry") or gloable_setting_dict.get(
            "req_max_retry")
        if max_retry <= 0:
            raise ValueError("req_max_retry must >0")
        header_dict = spider.cutome_setting_dict.get("default_headers") or gloable_setting_dict.get(
            "default_headers")
        req_timeout = request.timeout or spider.cutome_setting_dict.get("req_timeout") or gloable_setting_dict.get(
            "req_timeout")
        request.timeout = req_timeout
        header = request.header or {}
        request.header = header.update(header_dict)
        request.header = header
        ignore_response_codes = spider.cutome_setting_dict.get("ignore_response_codes") or gloable_setting_dict.get(
            "ignore_response_codes")
        req_delay = spider.cutome_setting_dict.get("req_delay") or gloable_setting_dict.get("req_delay")

        if request and request.retry >= max_retry:
            # reached max retry times
            self.log.error(f'reached max retry times... {request}')
            return
        request.retry = request.retry + 1
        # when canceled
        loop = asyncio.get_running_loop()
        if loop.is_closed() or not loop.is_running():
            self.log.warning(f'loop is closed in download')
            return
        with suppress(asyncio.CancelledError):
            async  with self.semaphore:
                await self._before_fetch(request)

                fetch = self.downer.fetch
                iscoroutinefunction = inspect.iscoroutinefunction(fetch)
                # support sync or async request
                try:
                    # req_delay
                    if req_delay > 0:
                        await asyncio.sleep(req_delay)
                    self.log.debug(
                        f"send a request:  \r\n【 \r\n url: {request.url} \r\n method: {request.method} \r\n header: {request.header} \r\n 】")
                    #
                    if iscoroutinefunction:
                        response = await fetch(request)
                    else:
                        self.log.debug(f'fetch may be an snyc func  so it will run in executor ')
                        response = await asyncio.get_event_loop() \
                            .run_in_executor(None, fetch, request)
                except TimeoutError as e:
                    # delay retry
                    self.scheduler.schedlue(request)
                    self.log.debug(
                        f'req  to fetch is timeout now so this req will dely to sechdule for retry {request.url}')
                    return
                except asyncio.CancelledError as e:
                    self.log.debug(f' task is cancel..')
                    return
                except BaseException as e:
                    self.log.error(f'occured some exception in downloader e:{e}')
                    return
                if response is None or not isinstance(response, Response):
                    self.log.error(
                        f'the downer {self.downer.__class__.__name__} fetch function must return a response,'
                        'that is a no-null response, and response must be a '
                        'smart.Response instance or sub Response instance.  ')
                    return

                if response.status not in ignore_response_codes:
                    await self._after_fetch(request, response)

        if response.status not in ignore_response_codes:
            response.request = request
            response.__spider__ = spider
            await self.response_queue.put(response)

    def get(self) -> Optional[Response]:
        with suppress(QueueEmpty):
            return self.response_queue.get_nowait()

    async def _before_fetch(self, request):
        if self.middwire and len(self.middwire.request_middleware) > 0:
            for item_tuple in self.middwire.request_middleware:
                user_func = item_tuple[1]
                if callable(user_func):
                    try:
                        # res not used
                        if inspect.iscoroutinefunction(user_func):
                            res = await user_func(request.__spider__, request)
                        else:
                            res = await asyncio.get_event_loop() \
                                .run_in_executor(None, user_func, request.__spider__, request)
                    except Exception as e:
                        self.log.error(f"in middwire,before do send a request occured an error: {e}", exc_info=True)
                        return

    async def _after_fetch(self, request, response):
        if response and self.middwire and len(self.middwire.response_middleware) > 0:
            for item_tuple in self.middwire.response_middleware:
                if callable(item_tuple[1]):
                    try:
                        # res not used
                        if inspect.iscoroutinefunction(item_tuple[1]):
                            res = await item_tuple[1](request.__spider__, request, response)
                        else:
                            res = await asyncio.get_event_loop() \
                                .run_in_executor(None, item_tuple[1], request.__spider__, request, response)
                    except Exception as e:
                        self.log.error(f"in middwire,after a request sended, occured an error: {e}", exc_info=True)
                        return
