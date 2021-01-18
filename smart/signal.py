# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      signal
# Author:    liangbaikai
# Date:      2021/1/15
# Desc:      there is a python file description
# ------------------------------------------------------------------
from blinker import Signal


class _Reminder:
    spider_start = Signal("spider_start")
    spider_execption = Signal("spider_execption")
    spider_close = Signal("spider_close")
    engin_start = Signal("engin_start")
    engin_idle = Signal("engin_idle")
    engin_close = Signal("engin_close")
    request_dropped = Signal("request_dropped")
    request_scheduled = Signal("request_scheduled")
    response_received = Signal("response_received")
    response_downloaded = Signal("response_downloaded")
    item_dropped = Signal("item_dropped")

    def __init__(self, *args, **kwargs):
        pass

    def go(self, signal: Signal, *args, **kwargs):
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
