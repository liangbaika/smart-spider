# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      si
# Author:    liangbaikai
# Date:      2021/1/15
# Desc:      there is a python file description
# ------------------------------------------------------------------

from blinker import Signal


class AltProcessor:
    on_start = Signal()
    on_complete = Signal()

    def __init__(self, name):
        self.name = name

    def _on_start(self):
        print("Alternate processing.")
        self.on_complete.send(1,2,3,a=2)

    def __repr__(self):
        return '<AltProcesso>'


apc = AltProcessor('c')


# 爬虫启动 爬虫发生异常  爬虫关闭   引擎启动 引擎关闭
# request_dropped  request_scheduled  response_received item_dropped response_downloaded

@apc.on_complete.connect
def completed(*args,**kwargs):
    print("AltProcessor %s completed!")


apc._on_start()
