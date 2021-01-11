# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      js_spider
# Author:    liangbaikai
# Date:      2021/1/7
# Desc:      there is a python file description
# ------------------------------------------------------------------
from asyncio import Lock

from pyppeteer import launch

from smart.downloader import BaseDown
from smart.request import Request
from smart.response import Response
from smart.spider import Spider


class Broswer(BaseDown):

    def __init__(self):
        self.browser = None
        self.lock = Lock()

    async def fetch(self, request: Request) -> Response:
        # 双重检查锁 “并发” 防止打开多个浏览器
        if self.browser is None:
            async with self.lock:
                if self.browser is None:
                    self.browser = await launch({
                        'headless': False,
                        'dumpio': True,  # 'dumpio':True 浏览器就不会卡住了
                        'autoClose': True,
                        'executablePath': r'D:\soft\googlechrome\Application\77.0.3865.120\chrome.exe',
                        # 浏览器的存放地址,指定路径可快速运行
                        'args': ['–no - sandbox']
                    })

        page = await self.browser.newPage()
        res = await page.goto(request.url)
        page_text = await page.content()
        await page.close()
        return Response(body=page_text.encode(), status=res.status, request=request, headers=res.headers)


class JsSpider(Spider):

    cutome_setting_dict = {**Spider.cutome_setting_dict,
                           **{"net_download_class": "spiders.js.js_spider.Broswer", "req_per_concurrent": 15}}

    def start_requests(self):
        start_urls = ["https://www.jianshu.com/p/e8f7f6c82be6" for i in range(30)]
        for url in start_urls:
            yield Request(url=url, callback=self.parse, dont_filter=True)

    def parse(self, response: Response):
        print(response.ok)
