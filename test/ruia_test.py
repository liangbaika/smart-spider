# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      ruia_test
# Author:    liangbaikai
# Date:      2020/12/31
# Desc:      there is a python file description
# ------------------------------------------------------------------

from ruia import AttrField, Item, Request, Spider, TextField
from ruia_ua import middleware


class ArchivesItem(Item):
    """
    eg: http://www.ruanyifeng.com/blog/archives.html
    """
    target_item = TextField(css_select='div#beta-inner li.module-list-item')
    href = AttrField(css_select='li.module-list-item>a', attr='href')


class ArticleListItem(Item):
    """
    eg: http://www.ruanyifeng.com/blog/essays/
    """
    target_item = TextField(css_select='div#alpha-inner li.module-list-item')
    title = TextField(css_select='li.module-list-item>a')
    href = AttrField(css_select='li.module-list-item>a', attr='href')


class BlogSpider(Spider):
    """
    针对博客源 http://www.ruanyifeng.com/blog/archives.html 的爬虫
    这里为了模拟ua，引入了一个ruia的第三方扩展
        - ruia-ua: https://github.com/howie6879/ruia-ua
        - pipenv install ruia-ua
        - 此扩展会自动为每一次请求随机添加 User-Agent
    """
    # 设置启动URL
    start_urls = ['http://www.ruanyifeng.com/blog/archives.html']
    # 爬虫模拟请求的配置参数
    request_config = {
        'RETRIES': 3,
        'DELAY': 0,
        'TIMEOUT': 3
    }
    # 请求信号量
    concurrency = 400
    blog_nums = 0

    async def parse(self, res):
        for page in range(1113):
            print(page)
            url = f'http://exercise.kingname.info/exercise_middleware_ip/{page}'
            yield Request(
                url,
                callback=self.parse_item
            )

    async def parse_item(self, res):
        print(res.html)



class RuiaTestSpider(Spider):
    request_config = {
        'RETRIES': 3,
        'DELAY': 0,
        'TIMEOUT': 3
    }
    pass

if __name__ == '__main__':
    BlogSpider.start(middleware=middleware)
