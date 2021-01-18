# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      aio
# Author:    liangbaikai
# Date:      2021/1/18
# Desc:      there is a python file description
# ------------------------------------------------------------------
import asyncio
import time

from smart.downloader import AioHttpDown
from smart.request import Request


async def fetch(url):
    try:
        req = Request(url=url)
        res = await AioHttpDown().fetch(req)
        return res
    except Exception as e:
        print(e)
        pass


async def do():
    tasks = []
    for page in range(1000):
        url = f'http://exercise.kingname.info/exercise_middleware_ip/{page}'
        url = "https://www.baidu.com?q=" + str(page)
        task = asyncio.ensure_future(fetch(url))
        tasks.append(task)
    await asyncio.gather(*tasks)

    for t in tasks:
        print(t.result())


if __name__ == '__main__':
    start = time.time()
    loop = asyncio.ProactorEventLoop()
    loop.run_until_complete(do())
    end = time.time()
    print('花费')
    print(end - start)
