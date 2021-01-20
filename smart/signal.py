# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      signal
# Author:    liangbaikai
# Date:      2021/1/15
# Desc:      gloable sinal trigger
# ------------------------------------------------------------------
from functools import partial

from blinker import Signal, ANY


class _Reminder:
    # 每个爬虫开始启动的时候调用
    spider_start = Signal("spider_start")
    # 每个爬虫发生异常的时候调用
    spider_execption = Signal("spider_execption")
    # 每个爬虫关闭的时候调用
    spider_close = Signal("spider_close")
    # 引擎启动的时候调用
    engin_start = Signal("engin_start")
    # 引擎空闲(将要关闭)的时候调用
    engin_idle = Signal("engin_idle")
    # 引擎关闭的时候调用
    engin_close = Signal("engin_close")
    # 忽略请求的时候调用 如达到最大重试次数 将丢弃
    request_dropped = Signal("request_dropped")
    # 请求被调度器调度的时候调用
    request_scheduled = Signal("request_scheduled")
    # 响应被调度的时候调用
    response_received = Signal("response_received")
    # 响应成功下载的时候调用
    response_downloaded = Signal("response_downloaded")
    # item 丢弃的时候调用
    item_dropped = Signal("item_dropped")

    def __init__(self, *args, **kwargs):
        pass



    def go(self, signal: Signal, *args, **kwargs):
        """
        在对应的时期点触发信号
        如果此信号没有订阅者 那么将不会被真正发送
        :param signal:  信号
        :param args:  参数
        :param kwargs: 字典参数
        :return: none
        """
        if signal is None:
            raise ValueError("signal can not be null")
        has_receivers = bool(signal.receivers)
        if has_receivers:
            try:
                signal.send(*args, **kwargs)
            except Exception as e:
                pass


Reminder = _Reminder
reminder = Reminder()
