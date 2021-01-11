import re
import socket
import urllib

RE_COMPILE = re.compile("(^https?:/{2}\w.+$)|(ftp://)")


def is_valid_url(url):
    """
    验证url是否合法
    :param url:
    :return:
    """
    if RE_COMPILE.match(url):
        return True
    else:
        return False


def get_domain(url):
    proto, rest = urllib.parse.splittype(url)
    domain, rest = urllib.parse.splithost(rest)
    return domain


def get_index_url(url):
    return "/".join(url.split("/")[:3])


def get_ip(domain):
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
