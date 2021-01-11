
from tinepeas import Spider, Request


class IpSpider(Spider):
    name = 'ipspider'
    start_urls = [
        "http://www.nea.gov.cn/xwzx/nyyw.htm"
    ]

    def parse(self, response):
        print("run parse...........................................")
        print(response.status)
        res = response.xpath("/html/body//div/ul[@class='list']/li/a/@href")
        getall = res.getall()
        for _url in getall:
            yield Request(url=str(_url), callback=self.parse_detail, dont_filter=True)
            print(22)

    def parse_detail(self, response):
        print(333)
