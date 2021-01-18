# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      spider
# Author:    liangbaikai
# Date:      2020/12/21
# Desc:      there is a  utils module
# ------------------------------------------------------------------
import hashlib
import re
import socket
import urllib

# 验证Url 是否合法的正则
RE_COMPILE = re.compile("(^https?:/{2}\w.+$)|(ftp://)")


def is_valid_url(url):
    """
    验证url是否合法
    :param url: url
    :return: bool
    """
    if RE_COMPILE.match(url):
        return True
    else:
        return False


def get_domain(url):
    """
    获取 url 的domain
    :param url:
    :return:
    """
    proto, rest = urllib.parse.splittype(url)
    domain, rest = urllib.parse.splithost(rest)
    return domain


def get_index_url(url):
    """
    获取 主页地址
    :param url:
    :return:
    """
    return "/".join(url.split("/")[:3])


def get_ip(domain):
    """
    获取ip
    :param domain:
    :return:
    """
    ip = socket.getaddrinfo(domain, "http")[0][4][0]
    return ip


def get_localhost_ip():
    """
    利用 UDP 协议来实现的，生成一个UDP包，把自己的 IP 放如到 UDP 协议头中，然后从UDP包中获取本机的IP。
    这个方法并不会真实的向外部发包，所以用抓包工具是看不到的
    :return:
    """
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        if s:
            s.close()

    return ip


def get_md5(*args):
    """
    @summary: 获取唯一的32位md5
    ---------
    @param *args: 参与联合去重的值
    ---------
    @result: asasa788533325sasas111
    """

    m = hashlib.md5()
    for arg in args:
        m.update(str(arg).encode())

    return m.hexdigest()


def mutations_bkdr_hash(value: str):
    """
    获取hash编码 此处的hash 不会随环境改变
    若过长 直接使用md5编码
    :param value: 字符串
    :return: 34856558
    """
    if value is None:
        value = ''
    if not isinstance(value, str):
        value = str(value)
    if len(value) >= 10000:
        value = get_md5(value)

    seed = 131
    h = 0
    for v in value:
        h = seed * h + ord(v)
    return h & 0x7FFFFFFF
