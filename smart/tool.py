import hashlib
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


def get_md5(*args):
    """
    @summary: 获取唯一的32位md5
    ---------
    @param *args: 参与联合去重的值
    ---------
    @result: 7c8684bcbdfcea6697650aa53d7b1405
    """

    m = hashlib.md5()
    for arg in args:
        m.update(str(arg).encode())

    return m.hexdigest()


# mutations
def mutations_bkdr_hash(value: str):
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
