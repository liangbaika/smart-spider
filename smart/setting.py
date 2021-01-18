# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      setting
# Author:    liangbaikai
# Date:      2021/1/4
# Desc:      there is a python file description
# ------------------------------------------------------------------

gloable_setting_dict = {
    # 请求延迟
    "req_delay": 0,
    # request timeout 10 s
    "req_timeout": 10,
    # 每个爬虫的请求并发数
    "req_per_concurrent": 100,
    # 每个请求的最大重试次数
    "req_max_retry": 3,
    # 默认请求头
    "default_headers": {
        "Accept": "*/*;",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        # 百度搜索引擎爬虫ua
        "user-agent": "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)"
    },
    # 请求url 去重处理器
    # 自己实现需要继承 BaseDuplicateFilter 实现相关抽象方法 系统默认SampleDuplicateFilter
    "duplicate_filter_class": "smart.scheduler.SampleDuplicateFilter",
    # 请求url调度器容器
    # 自己实现需要继承 BaseSchedulerContainer 实现相关抽象方法  系统默认DequeSchedulerContainer
    "scheduler_container_class": "smart.scheduler.DequeSchedulerContainer",
    # 请求网络的方法  输入 request  输出 response
    # 自己实现需要继承 BaseDown 实现相关抽象方法  系统默认AioHttpDown
    "net_download_class": "smart.downloader.AioHttpDown",
    # 线程池数  当 middwire pipline 有不少耗时的同步方法时 适当调大
    "thread_pool_max_size": 50,
    # 根据响应的状态码 忽略以下响应
    "ignore_response_codes": [401, 403, 404, 405, 500, 502, 504],
    # 是否是分布式爬虫
    "is_single": 1,
    # pipline之间 处理item 是否并行处理 默认  0 串行   1 并行
    "pipline_is_paralleled": 0,
    # 启动时网络是否畅通检查地址
    "net_healthy_check_url": "https://www.baidu.com",
    # log level
    "log_level": "info",
    "log_name": "smart-spider",
    "log_path": ".logs/smart.log",
    "is_write_to_file": False,
}
