# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      request_buffer
# Author:    liangbaikai
# Date:      2021/1/18
# Desc:      there is a python file description
# ------------------------------------------------------------------
# -*- coding: utf-8 -*-
import collections
import threading
import time

MAX_URL_COUNT = 100  # 缓存中最大request数


class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_inst"):
            cls._inst = super(Singleton, cls).__new__(cls)
        return cls._inst


class RequestBuffer(threading.Thread, Singleton):
    dedup = None

    def __init__(self, table_folder):
        if not hasattr(self, "_requests_deque"):
            super(RequestBuffer, self).__init__()

            self._thread_stop = False
            self._is_adding_to_db = False

            self._requests_deque = collections.deque()
            self._del_requests_deque = collections.deque()
            self._db = RedisDB()

    def run(self):
        while not self._thread_stop:
            try:
                self.__add_request_to_db()
            except Exception as e:
                print(e)
            time.sleep(5)

    def stop(self):
        self._thread_stop = True

    def put_request(self, request):
        self._requests_deque.append(request)

        if self.get_requests_count() > MAX_URL_COUNT:  # 超过最大缓存，主动调用
            self.flush()

    def put_del_request(self, request):
        self._del_requests_deque.append(request)

    def flush(self):
        try:
            self.__add_request_to_db()
        except Exception as e:
            print(e)

    def get_requests_count(self):
        return len(self._requests_deque)

    def is_adding_to_db(self):
        return self._is_adding_to_db

    def __add_request_to_db(self):
        request_list = []
        prioritys = []
        callbacks = []

        while self._requests_deque:
            request = self._requests_deque.popleft()
            self._is_adding_to_db = True

            if callable(request):
                # 函数
                # 注意：应该考虑闭包情况。闭包情况可写成
                # def test(xxx = xxx):
                #     # TODO 业务逻辑 使用 xxx
                # 这么写不会导致xxx为循环结束后的最后一个值
                callbacks.append(request)
                continue

            priority = request.priority

            # 如果需要去重并且库中已重复 则continue
            if (
                    request.filter_repeat
                    and setting.REQUEST_FILTER_ENABLE
                    and not self.__class__.dedup.add(request.fingerprint)
            ):
                continue
            else:
                request_list.append(str(request.to_dict))
                prioritys.append(priority)

            if len(request_list) > MAX_URL_COUNT:
                self._db.zadd(self._table_request, request_list, prioritys)
                request_list = []
                prioritys = []

        # 入库
        if request_list:
            self._db.zadd(self._table_request, request_list, prioritys)

        # 执行回调
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                log.exception(e)

        # 删除已做任务
        if self._del_requests_deque:
            request_done_list = []
            while self._del_requests_deque:
                request_done_list.append(self._del_requests_deque.popleft())

            # 去掉request_list中的requests， 否则可能会将刚添加的request删除
            request_done_list = list(set(request_done_list) - set(request_list))

            if request_done_list:
                self._db.zrem(self._table_request, request_done_list)

        self._is_adding_to_db = False
