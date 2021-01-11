import json
import threading

from smart.item import Item
from smart.response import Response
from smart.request import Request
from smart.spider import Spider


class TestItem(Item):
    name = "23232"
    age = 900


class IpSpider(Spider):
    name = 'ipspider2'
    start_urls = []
    cutome_setting_dict = {**Spider.cutome_setting_dict, **{"req_per_concurrent": 100}}

    def start_requests(self):
        for page in range(100):
            url = f'http://exercise.kingname.info/exercise_middleware_ip/{page}'
            # url = f'http://exercise.kingname.info/exercise_middleware_ip/{page}'
            # url = 'http://fzggw.zj.gov.cn/art/2020/8/26/art_1621004_55344873.html'
            url = 'https://s.bdstatic.com/common/openjs/amd/eslx.js'
            yield Request(url, callback=self.parse, dont_filter=True, timeout=3)

    def parse(self, response: Response):
        pass
        # yield TestItem(response.text)
        # for page in range(10):
        #     print(page)
        #     url = f'http://exercise.kingname.info/exercise_middleware_ip/{page}'
        #     # url = f'http://exercise.kingname.info/exercise_middleware_ip/{page}'
        #     # url = 'http://fzggw.zj.gov.cn/art/2020/8/26/art_1621004_55344873.html'
        #     url = 'https://s.bdstatic.com/common/openjs/amd/eslx.js'
        #     yield Request(url, callback=self.parse2, dont_filter=True, timeout=3)
        # print(response.status)
        # yield Request(response.url, callback=self.parse2, dont_filter=True)

    def parse2(self, response):
        print(response.status)
        print("parse2222")

    def on_close(self):
        print('我被关闭了')


class IpSpider3(Spider):
    name = 'IpSpider22222'
    start_urls = []

    def on_start(self):
        self.cutome_setting_dict.update({

        })
        print('IpSpider22222 started')

    def start_requests(self):
        for page in range(1122):
            # url = f'http://exercise.kingname.info/exercise_middleware_ip/{page}'
            url = 'https://s.bdstatic.com/common/openjs/amd/eslx.js'
            yield Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: Response):
        # print('#######2')
        print(f'#######{self.name}')
        # print(threading.current_thread().name, "runing...", self.name)
        print(response.status)
        print("222222222222222")
        yield Request(url=response.url, callback=self.parse2, dont_filter=True)

    def parse2(self, response):
        print("222222222222222")
        pass

    def on_close(self):
        print('我被关闭了')


class GovSpider(Spider):
    name = 'GovSpider'
    start_urls = [
        "http://www.nea.gov.cn/xwzx/nyyw.htm"
    ]

    def on_start(self):
        print('GovSpider started')

    def parse(self, response: Response):
        print("run parse...........................................")
        print(response.status)
        res = response.xpath("/html/body//div/ul[@class='list']/li/a/@href")
        getall = res.getall()

        for _url in getall:
            yield Request(url=_url, callback=self.parse_detail, dont_filter=True)
            print(22222222222222222222222222222222222222)
        print(3333)

    def parse_detail(self, response: Response):
        print("xxxxxxxxxxparse_detail")

    def on_close(self):
        print(' GovSpider 关闭了')

    def on_exception_occured(self, e: Exception):
        print(e)


class ApiSpider(Spider):
    name = 'ApiSpider'
    start_urls = [
        "http://search.51job.com"
    ]

    def on_start(self):
        print('ApiSpider started')

    def start_requests(self):
        for i in range(1):
            yield Request(url="http://search.51job.com", callback=self.parse, dont_filter=True,
                          )

    def parse(self, response: Response):
        print("run parse...........................................")
        print(response.status)
        print(response.text)

    def on_exception_occured(self, e: Exception):
        print(e)
