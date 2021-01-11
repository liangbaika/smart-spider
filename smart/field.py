# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      item
# Author:    liangbaikai
# Date:      2020/12/31
# Desc:      there is a python file description
# ------------------------------------------------------------------
import json
import re
from abc import abstractmethod, ABC
from typing import Union, Iterable, Callable, Any

import jsonpath
from lxml import etree
from lxml.etree import _ElementUnicodeResult


class BaseField:

    def __init__(self, default=None, many: bool = False):
        self.default = default
        self.many = many

    def extract(self, *args, **kwargs):
        ...


class _LxmlElementField(BaseField):
    def __init__(
            self,
            css_select: str = None,
            xpath_select: str = None,
            default='',
            many: bool = False,
    ):
        """
        :param css_select: css select http://lxml.de/cssselect.html
        :param xpath_select: http://www.w3school.com.cn/xpath/index.asp
        :param default: inherit
        :param many: inherit
        """
        super(_LxmlElementField, self).__init__(default=default, many=many)
        self.css_select = css_select
        self.xpath_select = xpath_select

    def _get_elements(self, *, html_etree: etree._Element):
        if self.css_select:
            elements = html_etree.cssselect(self.css_select)
        elif self.xpath_select:
            elements = html_etree.xpath(self.xpath_select)
        else:
            raise ValueError(
                f"{self.__class__.__name__} field: css_select or xpath_select is expected."
            )
        if not self.many:
            elements = elements[:1]
        return elements

    def _parse_element(self, element):
        raise NotImplementedError

    def extract(self, html: Union[etree._Element, str]):
        if html is None:
            raise ValueError("html_etree can not be null..")

        if html and not isinstance(html, etree._Element):
            html = etree.HTML(html)

        elements = self._get_elements(html_etree=html)

        # if is_source:
        #     return elements if self.many else elements[0]

        if elements:
            results = [self._parse_element(element) for element in elements]
        elif self.default is None:
            raise ValueError(
                f"Extract `{self.css_select or self.xpath_select}` error, "
                "please check selector or set parameter named `default`"
            )
        else:
            results = self.default if type(self.default) == list else [self.default]

        return results if self.many else results[0]


class AttrField(_LxmlElementField):
    """
    This field is used to get attribute.
    """

    def __init__(
            self,
            attr,
            css_select: str = None,
            xpath_select: str = None,
            default="",
            many: bool = False,
    ):
        super(AttrField, self).__init__(
            css_select=css_select, xpath_select=xpath_select, default=default, many=many
        )
        self.attr = attr

    def _parse_element(self, element):
        return element.get(self.attr, self.default)


class ElementField(_LxmlElementField):
    """
    This field is used to get LXML element(s).
    """

    def _parse_element(self, element):
        return element


class HtmlField(_LxmlElementField):
    """
    This field is used to get raw html data.
    """

    def _parse_element(self, element):
        if element is None:
            return None
        if isinstance(element, _ElementUnicodeResult):
            res = element.encode("utf-8").decode(encoding="utf-8")
        else:
            res = etree.tostring(element, encoding="utf-8").decode(encoding="utf-8")
        if res:
            res = res.strip()
        return res


class TextField(_LxmlElementField):
    """
    This field is used to get text.
    """

    def _parse_element(self, element):
        # Extract text appropriately based on it's type
        if isinstance(element, etree._ElementUnicodeResult):
            strings = [node for node in element]
        else:
            strings = [node for node in element.itertext()]

        string = "".join(strings)
        return string if string else self.default


class JsonPathField(BaseField):
    def __init__(self, json_path: str, default="", many: bool = False):
        super(JsonPathField, self).__init__(default=default, many=many)
        self._json_path = json_path

    def extract(self, html: Union[str, dict, etree._Element]):
        if isinstance(html, etree._Element):
            html = etree.tostring(html).decode(encoding="utf-8")
        if isinstance(html, str) or isinstance(html, etree._Element):
            html = json.loads(html)
        json_loads = html
        res = jsonpath.jsonpath(json_loads, self._json_path)
        if isinstance(res, bool) and not res:
            return self.default
        if self.many:
            if isinstance(res, Iterable):
                return res
            else:
                return [res]
        else:
            if isinstance(res, Iterable) and not isinstance(res, str):
                return res[0]
            else:
                return res


class RegexField(BaseField):
    """
    This field is used to get raw html code by regular expression.
    RegexField uses standard library `re` inner, that is to say it has a better performance than _LxmlElementField.
    """

    def __init__(self, re_select: str, re_flags=0, default="", many: bool = False):
        super(RegexField, self).__init__(default=default, many=many)
        self._re_select = re_select
        self._re_object = re.compile(self._re_select, flags=re_flags)

    def _parse_match(self, match):
        if not match:
            if self.default is not None:
                return self.default
            else:
                raise ValueError(
                    f"Extract `{self._re_select}` error, can not founded "
                    f"please check selector or set parameter named `default`"
                )
        else:
            string = match.group()
            groups = match.groups()
            group_dict = match.groupdict()
            if group_dict:
                return group_dict
            if groups:
                return groups[0] if len(groups) == 1 else groups
            return string

    def extract(self, html: Union[str, dict, etree._Element]):
        if isinstance(html, etree._Element):
            html = etree.tostring(html).decode(encoding="utf-8")
        if isinstance(html, dict):
            html = json.dumps(html, ensure_ascii=False)
        if self.many:
            matches = self._re_object.finditer(html)
            return [self._parse_match(match) for match in matches]
        else:
            match = self._re_object.search(html)
            return self._parse_match(match)


class FuncField(BaseField):
    def __init__(self, call: Callable, name: str, default="", many: bool = False):
        super(FuncField, self).__init__(default=default, many=many)
        self._callable = call
        if not callable(self._callable):
            raise TypeError("callable param need a  function or cab be called")
        self._name = name

    def extract(self, html: Any):
        res = self._callable(html, self._name)
        if self.many:
            if isinstance(res, Iterable):
                return res
            else:
                return [res]
        else:
            if isinstance(res, Iterable) and not isinstance(res, str):
                return res[0]
            else:
                return res


if __name__ == '__main__':
    html = """
    
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Cache-Control" content="no-siteapp" />
<meta http-equiv="Cache-Control" content="no-transform" />
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>武动乾坤小说_天蚕土豆_武动乾坤最新章节_武动乾坤无弹窗_新笔趣阁</title>
<meta name="keywords" content="武动乾坤,武动乾坤最新章节" />
<meta name="description" content="如果您喜欢小说武动乾坤，请将武动乾坤最新章节目录加入收藏方便您下次阅读,新笔趣阁将在第一时间更新小说武动乾坤，发现没及时更新，请告知我们,谢谢!" />
<link rel="stylesheet" type="text/css" href="/images/biquge.css"/>
<script type="text/javascript" src="http://libs.baidu.com/jquery/1.4.2/jquery.min.js"></script>
<!--<script type="text/javascript" src="http://cbjs.baidu.com/js/m.js"></script>-->
<script type="text/javascript" src="/images/bqg.js"></script>
<script language="javascript" type="text/javascript">var bookid = "15"; var booktitle = "武动乾坤";</script>
<meta name="mobile-agent" content="format=html5;url=http://m.xbiquge.la/wapbook/15.html"/>
<meta name="mobile-agent" content="format=xhtml;url=http://m.xbiquge.la/wapbook/15.html"/>
<meta property="og:type" content="novel"/>
<meta property="og:title" content="武动乾坤"/>
<meta property="og:description" content="    修炼一途，乃窃阴阳，夺造化，转涅盘，握生死，掌轮回。
    武之极，破苍穹，动乾坤！
    新书求收藏，求推荐，谢大家o(n_n)o~
"/>
<meta property="og:image" content="http://www.xbiquge.la/files/article/image/0/15/15s.jpg"/>
<meta property="og:novel:category" content="玄幻小说"/>
<meta property="og:novel:author" content="天蚕土豆"/>
<meta property="og:novel:book_name" content="武动乾坤"/>
<meta property="og:novel:read_url" content="http://www.xbiquge.la/0/15/"/>
</head>
<body>
    <div id="wrapper">
        <script>login();</script>
        <div class="header">
            <div class="header_logo">
                <a href="http://www.xbiquge.la">新笔趣阁</a>
            </div>
            <script>bqg_panel();</script>
        </div>
        <div class="nav">
            <ul>
                <li><a href="http://www.xbiquge.la/">首页</a></li>
                <li><a href="/modules/article/bookcase.php">我的书架</a></li>
                <li><a href="/xuanhuanxiaoshuo/">玄幻小说</a></li>
                <li><a href="/xiuzhenxiaoshuo/">修真小说</a></li>
                <li><a href="/dushixiaoshuo/">都市小说</a></li>
                <li><a href="/chuanyuexiaoshuo/">穿越小说</a></li>
                <li><a href="/wangyouxiaoshuo/">网游小说</a></li>
                <li><a href="/kehuanxiaoshuo/">科幻小说</a></li>
                <li><a href="/paihangbang/">排行榜单</a></li>
                <li><a href="/xiaoshuodaquan/">全部小说</a></li>
            </ul>
        </div>
<script type="text/javascript">list_top();</script>

        <div class="box_con">
            <div class="con_top">
                <div id="bdshare" class="bdshare_b" style="line-height: 12px;"><img src="http://bdimg.share.baidu.com/static/images/type-button-7.jpg" /><a class="shareCount"></a></div>
                <a href="/">新笔趣阁</a> &gt; <a href="http://www.xbiquge.la/fenlei/1_1.html">玄幻小说</a>  &gt; 武动乾坤最新章节目录
            </div>
            <div id="maininfo">
                <div id="info">
                    <h1>武动乾坤</h1>
                    <p>作&nbsp;&nbsp;&nbsp;&nbsp;者：天蚕土豆</p>
                    <p>动&nbsp;&nbsp;&nbsp;&nbsp;作：<a href="javascript:;" onClick="showpop_addcase(15);">加入书架</a>,  <a href="javascript:;" onClick="showpop_vote(15);">投推荐票</a>,  <a href="#footer">直达底部</a></p>
                    <p>最后更新：2017-11-09 06:33:19</p>
                    <p>最新章节：<a href="http://www.xbiquge.la/0/15/7009895.html">新书大主宰已发。</a></p>
                </div>
                <div id="intro">
                                        <p><font style="color:#0066FF"><a href='http://m.xbiquge.la/wapbook/15.html' target='_blank'>手机阅读《武动乾坤》无弹窗纯文字全文免费阅读</a></font>
 
                                        </p>
                                        
                    <p>    修炼一途，乃窃阴阳，夺造化，转涅盘，握生死，掌轮回。
    武之极，破苍穹，动乾坤！
    新书求收藏，求推荐，谢大家o(n_n)o~
</p>
                </div>
            </div>
            <div id="sidebar">
                <div id="fmimg"><img alt="武动乾坤" src="http://www.xbiquge.la/files/article/image/0/15/15s.jpg" width="120" height="150" /><span class="b"></span></div>
            </div> 
            <div id="listtj">&nbsp;推荐阅读：<a href="http://www.xbiquge.la/9/9785/" target="_blank">剑卒过河</a>、<a href="http://www.xbiquge.la/0/10/" target="_blank">武炼巅峰</a>、<a href="http://www.xbiquge.la/26/26874/" target="_blank">沧元图</a>、<a href="http://www.xbiquge.la/15/15409/" target="_blank">牧神记</a>、<a href="http://www.xbiquge.la/26/26511/" target="_blank">剑徒之路</a>、<a href="http://www.xbiquge.la/2/2029/" target="_blank">极品透视</a>、<a href="http://www.xbiquge.la/13/13959/" target="_blank">圣墟</a>、<a href="http://www.xbiquge.la/1/1988/" target="_blank">龙城</a>、<a href="http://www.xbiquge.la/32/32626/" target="_blank">叶辰孙怡夏若雪</a>、<a href="http://www.xbiquge.la/0/951/" target="_blank">伏天氏</a>、<a href="http://www.xbiquge.la/30/30581/" target="_blank">顶级神豪</a>、<a href="http://www.xbiquge.la/20/20948/" target="_blank">最佳女婿</a>、<a href="http://www.xbiquge.la/0/656/" target="_blank">莽荒纪</a>、<a href="http://www.xbiquge.la/14/14930/" target="_blank">元尊</a>、<a href="http://www.xbiquge.la/7/7552/" target="_blank">万古神帝</a></div>
        </div>
        
        <div class="dahengfu"><script type="text/javascript">list_mid();</script></div>
        
        <div class="box_con">
            <div id="list">
                <dl>  
                    
                      
                <dd><a href='/0/15/12961.html' >第一章 林动</a></dd>
                <dd><a href='/0/15/12962.html' >第二章 通背拳</a></dd>
                <dd><a href='/0/15/12963.html' >第三章 古怪的石池</a></dd>
                <dd><a href='/0/15/12964.html' >第四章 石池之秘</a></dd>
                    
                      
                <dd><a href='/0/15/12965.html' >第五章 神秘石符</a></dd>
                <dd><a href='/0/15/12966.html' >第六章 七响</a></dd>
                <dd><a href='/0/15/12967.html' >第七章 淬体第四重</a></dd>
                <dd><a href='/0/15/12968.html' >第八章 冲突</a></dd>
                    
                      
                <dd><a href='/0/15/12969.html' >第九章 林宏</a></dd>
                <dd><a href='/0/15/12970.html' >第十章 金玉枝</a></dd>
                <dd><a href='/0/15/12971.html' >第十一章 阴珠</a></dd>
                <dd><a href='/0/15/12972.html' >第十二章 第十响</a></dd>
                    
                      
                <dd><a href='/0/15/12973.html' >第十三章 疗伤</a></dd>
                <dd><a href='/0/15/12974.html' >第十四章 五等阴煞之气</a></dd>
                <dd><a href='/0/15/12975.html' >第十五章 淬体第五重</a></dd>
                <dd><a href='/0/15/12976.html' >第十六章 八荒掌</a></dd>
                    
                      
                <dd><a href='/0/15/12977.html' >第十七章 蝎虎</a></dd>
                <dd><a href='/0/15/12978.html' >第十八章 元力种子</a></dd>
                <dd><a href='/0/15/12979.html' >第十九章 族比前的突破</a></dd>
                <dd><a href='/0/15/12980.html' >第二十章 族比开始</a></dd>
                    
                      
                <dd><a href='/0/15/12981.html' >第二十一章 林陨</a></dd>
                <dd><a href='/0/15/12982.html' >第二十二章 艺惊全场</a></dd>
                <dd><a href='/0/15/12983.html' >第二十三章 前三</a></dd>
                <dd><a href='/0/15/12984.html' >第二十四章 完胜</a></dd>
                    
                      
                <dd><a href='/0/15/12985.html' >第二十五章 接管事务</a></dd>
                <dd><a href='/0/15/12986.html' >第二十六章 狩猎</a></dd>
                <dd><a href='/0/15/12987.html' >第二十七章 武学馆</a></dd>
                <dd><a href='/0/15/12988.html' >第二十八章 奇门印，残篇</a></dd>
                    
                      
                <dd><a href='/0/15/12989.html' >第二十九章 石符变故</a></dd>
                <dd><a href='/0/15/12990.html' >第三十章 小成</a></dd>
                <dd><a href='/0/15/12991.html' >第三十一章 妖孽</a></dd>
                <dd><a href='/0/15/12992.html' >第三十二章 地下交易所</a></dd>
                    
                      
                <dd><a href='/0/15/12993.html' >第三十三章 谢婷</a></dd>
                <dd><a href='/0/15/12994.html' >第三十四章 雷力</a></dd>
                <dd><a href='/0/15/12995.html' >第三十五章 初步交手</a></dd>
                <dd><a href='/0/15/12996.html' >第三十六章 聚餐</a></dd>
                    
                      
                <dd><a href='/0/15/12997.html' >第三十七章 突破</a></dd>
                <dd><a href='/0/15/12998.html' >第三十八章 变故</a></dd>
                <dd><a href='/0/15/12999.html' >第三十九章 地元境！</a></dd>
                <dd><a href='/0/15/13000.html' >第四十章 狩猎开始</a></dd>
                    
                      
                <dd><a href='/0/15/13001.html' >第四十一章 罗城</a></dd>
                <dd><a href='/0/15/13002.html' >第四十二章 火蟒虎</a></dd>
                <dd><a href='/0/15/13003.html' >第四十三章 抢崽</a></dd>
                <dd><a href='/0/15/13004.html' >第四十四章 得手</a></dd>
                    
                      
                <dd><a href='/0/15/13005.html' >第四十五章 剑拔弩张</a></dd>
                <dd><a href='/0/15/13006.html' >第四十六章 震惊全场</a></dd>
                <dd><a href='/0/15/13007.html' >第四十七章 激战</a></dd>
                <dd><a href='/0/15/13008.html' >第四十八章 收获</a></dd>
                    
                      
                <dd><a href='/0/15/13009.html' >第四十九章 武学奇才</a></dd>
                <dd><a href='/0/15/13010.html' >第五十章 青元功</a></dd>
                <dd><a href='/0/15/13011.html' >第五十一章 小炎</a></dd>
                <dd><a href='/0/15/13012.html' >第五十二章 家族之事</a></dd>
                    
                      
                <dd><a href='/0/15/13013.html' >第五十三章 铁木庄</a></dd>
                <dd><a href='/0/15/13014.html' >第五十四章 毁土</a></dd>
                <dd><a href='/0/15/13015.html' >第五十五章 搏杀</a></dd>
                <dd><a href='/0/15/13016.html' >第五十六章 泥土中的阳罡之气</a></dd>
                    
                      
                <dd><a href='/0/15/13017.html' >第五十七章 阳元石</a></dd>
                <dd><a href='/0/15/13018.html' >第五十八章 矿脉</a></dd>
                <dd><a href='/0/15/13019.html' >第五十九章 杀豹</a></dd>
                <dd><a href='/0/15/13020.html' >第六十章 磨练</a></dd>
                    
                      
                <dd><a href='/0/15/13021.html' >第六十一章 阳元丹</a></dd>
                <dd><a href='/0/15/13022.html' >第六十二章 炎城</a></dd>
                <dd><a href='/0/15/13023.html' >第六十三章 符师</a></dd>
                <dd><a href='/0/15/13024.html' >第六十四章 岩大师</a></dd>
                    
                      
                <dd><a href='/0/15/13025.html' >第六十五章 绊子</a></dd>
                <dd><a href='/0/15/13026.html' >第六十六章 神动篇</a></dd>
                <dd><a href='/0/15/13027.html' >第六十七章 阴云</a></dd>
                <dd><a href='/0/15/13028.html' >第六十八章 黑龙寨</a></dd>
                    
                      
                <dd><a href='/0/15/13029.html' >第六十九章 大难</a></dd>
                <dd><a href='/0/15/13030.html' >第七十章 震撼</a></dd>
                <dd><a href='/0/15/13031.html' >第七十一章 突破！</a></dd>
                <dd><a href='/0/15/13032.html' >第七十二章 退敌</a></dd>
                    
                      
                <dd><a href='/0/15/13033.html' >第七十三章 暴怒的林震天</a></dd>
                <dd><a href='/0/15/13034.html' >第七十四章 血洗黑龙寨</a></dd>
                <dd><a href='/0/15/13035.html' >第七十五章 碎元梭</a></dd>
                <dd><a href='/0/15/13036.html' >第七十六章 神秘兽骸</a></dd>
                    
                      
                <dd><a href='/0/15/13037.html' >第七十七章 妖异花朵</a></dd>
                <dd><a href='/0/15/13038.html' >第七十八章 暴涨的精神力</a></dd>
                <dd><a href='/0/15/13039.html' >第七十九章 地下坊会</a></dd>
                <dd><a href='/0/15/13040.html' >第八十章 遇袭</a></dd>
                    
                      
                <dd><a href='/0/15/13041.html' >第八十一章 反杀</a></dd>
                <dd><a href='/0/15/13042.html' >第八十二章 一死一伤</a></dd>
                <dd><a href='/0/15/13043.html' >第八十三章 古木</a></dd>
                <dd><a href='/0/15/13044.html' >第八十四章 古漩符印</a></dd>
                    
                      
                <dd><a href='/0/15/13045.html' >第八十五章 一印符师</a></dd>
                <dd><a href='/0/15/13046.html' >第八十六章 救援</a></dd>
                <dd><a href='/0/15/13047.html' >第八十七章 断后</a></dd>
                <dd><a href='/0/15/13048.html' >第八十八章 突破</a></dd>
                    
                      
                <dd><a href='/0/15/13049.html' >第八十九章 试探</a></dd>
                <dd><a href='/0/15/13050.html' >第九十章 小元丹境</a></dd>
                <dd><a href='/0/15/13051.html' >第九十一章 联姻</a></dd>
                <dd><a href='/0/15/13052.html' >第九十二章 雷谢两家的打算</a></dd>
                    
                      
                <dd><a href='/0/15/13053.html' >第九十三章 古大师</a></dd>
                <dd><a href='/0/15/13054.html' >第九十四章 暴露</a></dd>
                <dd><a href='/0/15/13055.html' >第九十五章 符师对决</a></dd>
                <dd><a href='/0/15/13056.html' >第九十六章 本命灵符</a></dd>
                    
                      
                <dd><a href='/0/15/13057.html' >第九十七章 杀！</a></dd>
                <dd><a href='/0/15/13058.html' >第九十八章 隐患</a></dd>
                <dd><a href='/0/15/13059.html' >第九十九章 石符内的“鼠”</a></dd>
                <dd><a href='/0/15/13060.html' >第一百章 天妖貂</a></dd>
                    
                      
                <dd><a href='/0/15/13061.html' >第一百零一章 血衣临门</a></dd>
                <dd><a href='/0/15/13062.html' >第一百零二章 赌约</a></dd>
                <dd><a href='/0/15/13063.html' >第一百零三章 暂离</a></dd>
                <dd><a href='/0/15/13064.html' >第一百零四章 万金拍卖场</a></dd>
                    
                      
                <dd><a href='/0/15/13065.html' >第一百零五章 销金窟</a></dd>
                <dd><a href='/0/15/13066.html' >第一百零六章 萱素</a></dd>
                <dd><a href='/0/15/13067.html' >第一百零七章 丹仙池</a></dd>
                <dd><a href='/0/15/13068.html' >第一百零八章 尖螺波</a></dd>
                    
                      
                <dd><a href='/0/15/13069.html' >第一百零九章 宋青</a></dd>
                <dd><a href='/0/15/13070.html' >第一百一十章 动身</a></dd>
                <dd><a href='/0/15/13071.html' >第一百一十一章 仙池之争</a></dd>
                <dd><a href='/0/15/13072.html' >第一百一十二章 最后一战</a></dd>
                    
                      
                <dd><a href='/0/15/13073.html' >第一百一十三章 化血归元功</a></dd>
                <dd><a href='/0/15/13074.html' >第一百一十四章 进入丹仙池</a></dd>
                <dd><a href='/0/15/13075.html' >第一百一十五章 化气精旋</a></dd>
                <dd><a href='/0/15/13076.html' >第一百一十六章 碧水妖蟒</a></dd>
                    
                      
                <dd><a href='/0/15/13077.html' >第一百一十七章 两兽相斗</a></dd>
                <dd><a href='/0/15/13078.html' >第一百一十八章 供奉与花销</a></dd>
                <dd><a href='/0/15/13079.html' >第一百一十九章 赚钱</a></dd>
                <dd><a href='/0/15/13080.html' >第一百二十章 三阳决</a></dd>
                    
                      
                <dd><a href='/0/15/13081.html' >第一百二十一章 苦修</a></dd>
                <dd><a href='/0/15/13082.html' >第一百二十二章 福不单行</a></dd>
                <dd><a href='/0/15/13083.html' >第一百二十三章 小元丹，二印符师</a></dd>
                <dd><a href='/0/15/13084.html' >第一百二十四章 展现实力</a></dd>
                    
                      
                <dd><a href='/0/15/13085.html' >第一百二十五章 生死斗</a></dd>
                <dd><a href='/0/15/13086.html' >第一百二十六章 对战魏通</a></dd>
                <dd><a href='/0/15/13087.html' >第一百二十七章 激战</a></dd>
                <dd><a href='/0/15/13088.html' >第一百二十八章 杀！</a></dd>
                    
                      
                <dd><a href='/0/15/13089.html' >第一百二十九章 落幕</a></dd>
                <dd><a href='/0/15/13090.html' >第一百三十章 塔斗</a></dd>
                <dd><a href='/0/15/13091.html' >第一百三十一章 紫月</a></dd>
                <dd><a href='/0/15/13092.html' >第一百三十二章 再说一次</a></dd>
                    
                      
                <dd><a href='/0/15/13093.html' >第一百三十三章 曹铸</a></dd>
                <dd><a href='/0/15/13094.html' >第一百三十四章 冰玄剑</a></dd>
                <dd><a href='/0/15/13095.html' >第一百三十五章 塔斗开始</a></dd>
                <dd><a href='/0/15/13096.html' >第一百三十六章 第五层</a></dd>
                    
                      
                <dd><a href='/0/15/13097.html' >第一百三十七章 打劫</a></dd>
                <dd><a href='/0/15/13098.html' >第一百三十八章 追赶</a></dd>
                <dd><a href='/0/15/13099.html' >第一百三十九章 进入第七层</a></dd>
                <dd><a href='/0/15/13100.html' >第一百四十章 意志</a></dd>
                    
                      
                <dd><a href='/0/15/13101.html' >第一百四十一章 化生符阵</a></dd>
                <dd><a href='/0/15/13102.html' >第一百四十二章 胜负</a></dd>
                <dd><a href='/0/15/13103.html' >第一百四十三章 三印符师</a></dd>
                <dd><a href='/0/15/13104.html' >第一百四十四章 祖符</a></dd>
                    
                      
                <dd><a href='/0/15/13105.html' >第一百四十五章 精神地</a></dd>
                <dd><a href='/0/15/13106.html' >第一百四十六章 一波再起</a></dd>
                <dd><a href='/0/15/13107.html' >第一百四十七章 鸟东西</a></dd>
                <dd><a href='/0/15/13108.html' >第一百四十八章 指教</a></dd>
                    
                      
                <dd><a href='/0/15/13109.html' >第一百四十九章 对战鬼阎</a></dd>
                <dd><a href='/0/15/13110.html' >第一百五十章 化生符阵显威</a></dd>
                <dd><a href='/0/15/13111.html' >第一百五十一章 四大势力</a></dd>
                <dd><a href='/0/15/13112.html' >第一百五十二章 震慑</a></dd>
                    
                      
                <dd><a href='/0/15/13113.html' >第一百五十三章 煞魔之体</a></dd>
                <dd><a href='/0/15/13114.html' >第一百五十四章 妖血朱果</a></dd>
                <dd><a href='/0/15/13115.html' >第一百五十五章 古墓府</a></dd>
                <dd><a href='/0/15/13116.html' >第一百五十六章 内族之人</a></dd>
                    
                      
                <dd><a href='/0/15/13117.html' >第一百五十七章 林尘</a></dd>
                <dd><a href='/0/15/13118.html' >第一百五十八章 完美的操控</a></dd>
                <dd><a href='/0/15/13119.html' >第一百五十九章 小圆满</a></dd>
                <dd><a href='/0/15/13120.html' >第一百六十章 天炎山脉</a></dd>
                    
                      
                <dd><a href='/0/15/13121.html' >第一百六十一章 宋刀</a></dd>
                <dd><a href='/0/15/13122.html' >第一百六十二章 灵宝</a></dd>
                <dd><a href='/0/15/13123.html' >第一百六十三章 化生符阵第三重</a></dd>
                <dd><a href='/0/15/13124.html' >第一百六十四章 强夺</a></dd>
                    
                      
                <dd><a href='/0/15/13125.html' >第一百六十五章 夜色下的落幕</a></dd>
                <dd><a href='/0/15/13126.html' >第一百六十六章 林琅天</a></dd>
                <dd><a href='/0/15/13127.html' >第一百六十七章 四大年轻顶尖强者！</a></dd>
                <dd><a href='/0/15/13128.html' >第一百六十八章 破封</a></dd>
                    
                      
                <dd><a href='/0/15/13129.html' >第一百六十九章 暴富</a></dd>
                <dd><a href='/0/15/13130.html' >第一百七十章 洗劫妖灵室</a></dd>
                <dd><a href='/0/15/13131.html' >第一百七十一章 六件灵宝</a></dd>
                <dd><a href='/0/15/13132.html' >第一百七十二章 抢宝</a></dd>
                    
                      
                <dd><a href='/0/15/13133.html' >第一百七十三章 天鳞古戟</a></dd>
                <dd><a href='/0/15/13134.html' >第一百七十四章 符傀</a></dd>
                <dd><a href='/0/15/13135.html' >第一百七十五章 中等符傀</a></dd>
                <dd><a href='/0/15/13136.html' >第一百七十六章 火海</a></dd>
                    
                      
                <dd><a href='/0/15/13137.html' >第一百七十七章 涅盘心</a></dd>
                <dd><a href='/0/15/13138.html' >第一百七十八章 强夺阳气</a></dd>
                <dd><a href='/0/15/13139.html' >第一百七十九章 墓府主人</a></dd>
                <dd><a href='/0/15/13140.html' >第一百八十章 麻烦</a></dd>
                    
                      
                <dd><a href='/0/15/13141.html' >第一百八十一章 今日事，百倍还</a></dd>
                <dd><a href='/0/15/13142.html' >第一百八十二章 符祖</a></dd>
                <dd><a href='/0/15/13143.html' >第一百八十三章 激斗王炎！</a></dd>
                <dd><a href='/0/15/13144.html' >第一百八十四章 符傀之威</a></dd>
                    
                      
                <dd><a href='/0/15/13145.html' >第一百八十五章 救援</a></dd>
                <dd><a href='/0/15/13146.html' >第一百八十六章 山顶之谈</a></dd>
                <dd><a href='/0/15/13147.html' >第一百八十七章 收获</a></dd>
                <dd><a href='/0/15/13148.html' >第一百八十八章 血拼</a></dd>
                    
                      
                <dd><a href='/0/15/13149.html' >第一百八十九章 以一敌三</a></dd>
                <dd><a href='/0/15/13150.html' >第一百九十章 戟法之威</a></dd>
                <dd><a href='/0/15/13151.html' >第一百九十一章 解决</a></dd>
                <dd><a href='/0/15/13152.html' >第一百九十二章 血狼帮之殇</a></dd>
                    
                      
                <dd><a href='/0/15/13153.html' >第一百九十三章 引爆阴煞之气</a></dd>
                <dd><a href='/0/15/13154.html' >第一百九十四章 黑色阴丹</a></dd>
                <dd><a href='/0/15/13155.html' >第一百九十五章 开启石符</a></dd>
                <dd><a href='/0/15/13156.html' >第一百九十六章 大日雷体</a></dd>
                    
                      
                <dd><a href='/0/15/13157.html' >第一百九十七章 离别前的挑战</a></dd>
                <dd><a href='/0/15/13158.html' >第一百九十八章 战城主</a></dd>
                <dd><a href='/0/15/13159.html' >第一百九十九章 化蛟戟</a></dd>
                <dd><a href='/0/15/13160.html' >第两百章 森林修行</a></dd>
                    
                      
                <dd><a href='/0/15/13161.html' >第两百零一章 引雷淬体</a></dd>
                <dd><a href='/0/15/13162.html' >第两百零二章 吞噬雷霆</a></dd>
                <dd><a href='/0/15/13163.html' >第两百零三章 小炎之危</a></dd>
                <dd><a href='/0/15/13164.html' >第两百零四章 大阳郡狄家</a></dd>
                    
                      
                <dd><a href='/0/15/13165.html' >第两百零五章 狄腾</a></dd>
                <dd><a href='/0/15/13166.html' >第两百零六章 雷源晶兽</a></dd>
                <dd><a href='/0/15/13167.html' >第两百零七章 抢夺雷源</a></dd>
                <dd><a href='/0/15/13168.html' >第两百零八章 大战造形境</a></dd>
                    
                      
                <dd><a href='/0/15/13169.html' >第两百零九章 炼化雷源</a></dd>
                <dd><a href='/0/15/13170.html' >第两百一十章 山洞闭关</a></dd>
                <dd><a href='/0/15/13171.html' >第两百一十一章 实力大涨</a></dd>
                <dd><a href='/0/15/13172.html' >第两百一十二章 显威</a></dd>
                    
                      
                <dd><a href='/0/15/13173.html' >第两百一十三章 击溃</a></dd>
                <dd><a href='/0/15/13174.html' >第两百一十四章 敲诈</a></dd>
                <dd><a href='/0/15/13175.html' >第两百一十五章 迷雾森林</a></dd>
                <dd><a href='/0/15/13176.html' >第两百一十六章 鹰之武馆</a></dd>
                    
                      
                <dd><a href='/0/15/13177.html' >第两百一十七章 迷雾豹鳄王</a></dd>
                <dd><a href='/0/15/13178.html' >第两百一十八章 露底</a></dd>
                <dd><a href='/0/15/13179.html' >第两百一十九章 大荒古碑</a></dd>
                <dd><a href='/0/15/13180.html' >第两百二十章 血鹫武馆</a></dd>
                    
                      
                <dd><a href='/0/15/13181.html' >第两百二十一章 狠揍</a></dd>
                <dd><a href='/0/15/13182.html' >第两百二十二章 美人献身</a></dd>
                <dd><a href='/0/15/13183.html' >第两百二十三章 罗鹫</a></dd>
                <dd><a href='/0/15/13184.html' >第两百二十四章 武斗台</a></dd>
                    
                      
                <dd><a href='/0/15/13185.html' >第两百二十五章 战造形境大成</a></dd>
                <dd><a href='/0/15/13186.html' >第两百二十六章 魔猿变</a></dd>
                <dd><a href='/0/15/13187.html' >第两百二十七章 击溃</a></dd>
                <dd><a href='/0/15/13188.html' >第两百二十八章 邂逅</a></dd>
                    
                      
                <dd><a href='/0/15/13189.html' >第两百二十九章 魔猿精血</a></dd>
                <dd><a href='/0/15/13190.html' >第两百三十章 远古龙猿</a></dd>
                <dd><a href='/0/15/13191.html' >第两百三十一章 远古废涧</a></dd>
                <dd><a href='/0/15/13192.html' >第两百三十二章 古剑门</a></dd>
                    
                      
                <dd><a href='/0/15/13193.html' >第两百三十三章 万兽果</a></dd>
                <dd><a href='/0/15/13194.html' >第两百三十四章 驱虎吞狼</a></dd>
                <dd><a href='/0/15/13195.html' >第两百三十五章 古剑憾龙猿</a></dd>
                <dd><a href='/0/15/13196.html' >第两百三十六章 惊天大战</a></dd>
                    
                      
                <dd><a href='/0/15/13197.html' >第两百三十七章 精血到手</a></dd>
                <dd><a href='/0/15/13198.html' >第两百三十八章 炼化龙猿精血</a></dd>
                <dd><a href='/0/15/13199.html' >第两百三十九章 炼化成功</a></dd>
                <dd><a href='/0/15/13200.html' >第两百四十章 肉搏</a></dd>
                    
                      
                <dd><a href='/0/15/13201.html' >第两百四十一章 大傀城</a></dd>
                <dd><a href='/0/15/13202.html' >第两百四十二章 慕芊芊</a></dd>
                <dd><a href='/0/15/13203.html' >第两百四十三章 拍卖会</a></dd>
                <dd><a href='/0/15/13204.html' >第两百四十四章 蕴神蒲团</a></dd>
                    
                      
                <dd><a href='/0/15/13205.html' >第两百四十五章 程大师</a></dd>
                <dd><a href='/0/15/13206.html' >第两百四十六章 进化的天鳞古戟</a></dd>
                <dd><a href='/0/15/13207.html' >第两百四十七章 节外生枝</a></dd>
                <dd><a href='/0/15/13208.html' >第两百四十八章 蒲团之谜</a></dd>
                    
                      
                <dd><a href='/0/15/13209.html' >第四百四十九章 元精之力</a></dd>
                <dd><a href='/0/15/13210.html' >第两百五十章 围剿</a></dd>
                <dd><a href='/0/15/13211.html' >第两百五十一章 灵符师</a></dd>
                <dd><a href='/0/15/13212.html' >第两百五十二章 激斗华宗</a></dd>
                    
                      
                <dd><a href='/0/15/13213.html' >第两百五十三章 破甲</a></dd>
                <dd><a href='/0/15/13214.html' >第两百五十四章 轰杀</a></dd>
                <dd><a href='/0/15/13215.html' >第两百五十五章 大丰收</a></dd>
                <dd><a href='/0/15/13216.html' >第两百五十六章 全力突破</a></dd>
                    
                      
                <dd><a href='/0/15/13217.html' >第两百五十七章 争分夺秒</a></dd>
                <dd><a href='/0/15/13218.html' >第两百五十八章 追寻而至</a></dd>
                <dd><a href='/0/15/13219.html' >第两百五十九章 硬憾造气大成</a></dd>
                <dd><a href='/0/15/13220.html' >第两百六十章 震退</a></dd>
                    
                      
                <dd><a href='/0/15/13221.html' >第两百六十一章 黑衣青年</a></dd>
                <dd><a href='/0/15/13222.html' >第两百六十二章 大荒古原</a></dd>
                <dd><a href='/0/15/13223.html' >第两百六十三章 腾儡</a></dd>
                <dd><a href='/0/15/13224.html' >第两百六十四章 再遇</a></dd>
                    
                      
                <dd><a href='/0/15/13225.html' >第两百六十五章 再战王炎</a></dd>
                <dd><a href='/0/15/13226.html' >第两百六十六章 完虐</a></dd>
                <dd><a href='/0/15/13227.html' >第两百六十七章 犀利言辞</a></dd>
                <dd><a href='/0/15/13228.html' >第两百六十八章 封印消失</a></dd>
                    
                      
                <dd><a href='/0/15/13229.html' >第两百六十九章 古碑空间</a></dd>
                <dd><a href='/0/15/13230.html' >第两百七十章 阴风炼体</a></dd>
                <dd><a href='/0/15/13231.html' >第两百七十一章 石亭骸骨</a></dd>
                <dd><a href='/0/15/13232.html' >第两百七十二章 冤家路窄</a></dd>
                    
                      
                <dd><a href='/0/15/13233.html' >第两百七十三章 断臂</a></dd>
                <dd><a href='/0/15/13234.html' >第两百七十四章 核心地带</a></dd>
                <dd><a href='/0/15/13235.html' >第两百七十五章 符傀巢穴</a></dd>
                <dd><a href='/0/15/13236.html' >第两百七十六章 抢夺</a></dd>
                    
                      
                <dd><a href='/0/15/13237.html' >第两百七十七章 收服高等符傀</a></dd>
                <dd><a href='/0/15/13238.html' >第两百七十八章 黑色祭坛</a></dd>
                <dd><a href='/0/15/13239.html' >第两百七十九章 黑瞳老人</a></dd>
                <dd><a href='/0/15/13240.html' >第两百八十章 封锁</a></dd>
                    
                      
                <dd><a href='/0/15/13241.html' >第两百八十一章 阴魔杀</a></dd>
                <dd><a href='/0/15/13242.html' >第两百八十二章 高等符傀之力</a></dd>
                <dd><a href='/0/15/13243.html' >第两百八十三章 造化武碑</a></dd>
                <dd><a href='/0/15/13244.html' >第两百八十四章 十道蒲团</a></dd>
                    
                      
                <dd><a href='/0/15/13245.html' >第两百八十五章 抢夺席位</a></dd>
                <dd><a href='/0/15/13246.html' >第两百八十六章 显凶威</a></dd>
                <dd><a href='/0/15/13247.html' >第两百八十七章 强势擒获</a></dd>
                <dd><a href='/0/15/13248.html' >第两百八十八章 占据</a></dd>
                    
                      
                <dd><a href='/0/15/13249.html' >第两百八十九章 大荒囚天指</a></dd>
                <dd><a href='/0/15/13250.html' >第两百九十章 传承武学</a></dd>
                <dd><a href='/0/15/13251.html' >第两百九十一章 造气境</a></dd>
                <dd><a href='/0/15/13252.html' >第两百九十二章 宗派宝藏</a></dd>
                    
                      
                <dd><a href='/0/15/13253.html' >第两百九十三章 远古血蝠龙</a></dd>
                <dd><a href='/0/15/13254.html' >第两百九十四章 斩杀血蝠龙</a></dd>
                <dd><a href='/0/15/13255.html' >第两百九十五章 飞来横财</a></dd>
                <dd><a href='/0/15/13256.html' >第两百九十六章 逃</a></dd>
                    
                      
                <dd><a href='/0/15/13257.html' >第两百九十七章 夺宝再逃</a></dd>
                <dd><a href='/0/15/13258.html' >第两百九十八章 黑色符文</a></dd>
                <dd><a href='/0/15/13259.html' >第两百九十九章 诅咒之力</a></dd>
                <dd><a href='/0/15/13260.html' >第三百章 实力提升</a></dd>
                    
                      
                <dd><a href='/0/15/13261.html' >第三百零一章 上门挑衅</a></dd>
                <dd><a href='/0/15/13262.html' >第三百零二章 强势出手</a></dd>
                <dd><a href='/0/15/13263.html' >第三百零三章 血屠手曹震</a></dd>
                <dd><a href='/0/15/13264.html' >第三百零四章 对战半步造化</a></dd>
                    
                      
                <dd><a href='/0/15/13265.html' >第三百零五章 九步震天踏</a></dd>
                <dd><a href='/0/15/13266.html' >第三百零六章 安然而退</a></dd>
                <dd><a href='/0/15/13267.html' >第三百零七章 情报</a></dd>
                <dd><a href='/0/15/13268.html' >第三百零八章 紫影九破</a></dd>
                    
                      
                <dd><a href='/0/15/13269.html' >第三百零九章 阴傀城</a></dd>
                <dd><a href='/0/15/13270.html' >第三百一十章 腾刹</a></dd>
                <dd><a href='/0/15/13271.html' >第三百一十一章 黑瞳虚影</a></dd>
                <dd><a href='/0/15/13272.html' >第三百一十二章 破阵</a></dd>
                    
                      
                <dd><a href='/0/15/13273.html' >第三百一十三章 造化境大成</a></dd>
                <dd><a href='/0/15/13274.html' >第三百一十四章 抢了就跑</a></dd>
                <dd><a href='/0/15/13275.html' >第三百一十五章 大乱</a></dd>
                <dd><a href='/0/15/13276.html' >第三百一十六章 心狠手辣</a></dd>
                    
                      
                <dd><a href='/0/15/13277.html' >第三百一十七章 玄阴涧</a></dd>
                <dd><a href='/0/15/13278.html' >第三百一十八章 无路可逃</a></dd>
                <dd><a href='/0/15/13279.html' >第三百一十九章 绝境</a></dd>
                <dd><a href='/0/15/13280.html' >第三百二十章 封印破解</a></dd>
                    
                      
                <dd><a href='/0/15/13281.html' >第三百二十一章 黑暗之界</a></dd>
                <dd><a href='/0/15/13282.html' >第三百二十二章 祖符认可</a></dd>
                <dd><a href='/0/15/13283.html' >第三百二十三章 高级灵符师</a></dd>
                <dd><a href='/0/15/13284.html' >第三百二十四章 实力暴涨</a></dd>
                    
                      
                <dd><a href='/0/15/13285.html' >第三百二十五章 深入玄阴涧</a></dd>
                <dd><a href='/0/15/13286.html' >第三百二十六章 危难</a></dd>
                <dd><a href='/0/15/13287.html' >第三百二十七章 晋入半步造化</a></dd>
                <dd><a href='/0/15/13288.html' >第三百二十八章 滔天杀意</a></dd>
                    
                      
                <dd><a href='/0/15/13289.html' >第三百二十九章 复仇</a></dd>
                <dd><a href='/0/15/13290.html' >第三百三十章 大战造化大成</a></dd>
                <dd><a href='/0/15/13291.html' >第三百三十一章 血战</a></dd>
                <dd><a href='/0/15/13292.html' >第三百三十二章 煞气逼人</a></dd>
                    
                      
                <dd><a href='/0/15/13293.html' >第三百三十三章 祖符之威</a></dd>
                <dd><a href='/0/15/13294.html' >第三百三十四章 灭宗</a></dd>
                <dd><a href='/0/15/13295.html' >第三百三十五章 斩草除根</a></dd>
                <dd><a href='/0/15/13296.html' >第三百三十六章 血灵傀</a></dd>
                    
                      
                <dd><a href='/0/15/13297.html' >第三百三十七章 下狠心</a></dd>
                <dd><a href='/0/15/13298.html' >第三百三十八章 封印血灵傀</a></dd>
                <dd><a href='/0/15/13299.html' >第三百三十九章 晋级的需求</a></dd>
                <dd><a href='/0/15/13300.html' >第三百四十章 离开</a></dd>
                    
                      
                <dd><a href='/0/15/13301.html' >第三百四十一章 凑齐妖血</a></dd>
                <dd><a href='/0/15/13302.html' >第三百四十二章 雷体大成</a></dd>
                <dd><a href='/0/15/13303.html' >第三百四十三章 麻衣老人</a></dd>
                <dd><a href='/0/15/13304.html' >第三百四十四章 险象环生</a></dd>
                    
                      
                <dd><a href='/0/15/13305.html' >第三百四十五章 大炎郡</a></dd>
                <dd><a href='/0/15/13306.html' >第三百四十六章 族会！</a></dd>
                <dd><a href='/0/15/13307.html' >第三百四十七章 强大的青檀</a></dd>
                <dd><a href='/0/15/13308.html' >第三百四十八章 林动归来！</a></dd>
                    
                      
                <dd><a href='/0/15/13309.html' >第三百四十九章 滚下来</a></dd>
                <dd><a href='/0/15/13310.html' >第三百五十章 何谓嚣张</a></dd>
                <dd><a href='/0/15/13311.html' >第三百五十一章 一拳轰爆</a></dd>
                <dd><a href='/0/15/13312.html' >第三百五十二章 给你一个字</a></dd>
                    
                      
                <dd><a href='/0/15/13313.html' >第三百五十三章 对战林琅天！</a></dd>
                <dd><a href='/0/15/13314.html' >第三百五十四章 龙争虎斗</a></dd>
                <dd><a href='/0/15/13315.html' >第三百五十五章 大天凰印！</a></dd>
                <dd><a href='/0/15/13316.html' >第三百五十六章 底牌层出</a></dd>
                    
                      
                <dd><a href='/0/15/13317.html' >第三百五十七章 灵轮镜</a></dd>
                <dd><a href='/0/15/13318.html' >第三百五十八章 拼命相搏</a></dd>
                <dd><a href='/0/15/13319.html' >第三百五十九章 林梵</a></dd>
                <dd><a href='/0/15/13320.html' >第三百六十章 落幕</a></dd>
                    
                      
                <dd><a href='/0/15/13321.html' >第三百六十一章 种子选拔</a></dd>
                <dd><a href='/0/15/13322.html' >第三百六十二章 大炎王朝外的世界</a></dd>
                <dd><a href='/0/15/13323.html' >第三百六十三章 族藏</a></dd>
                <dd><a href='/0/15/13324.html' >第三百六十四章 暗袭</a></dd>
                    
                      
                <dd><a href='/0/15/13325.html' >第三百六十五章 神秘的黑色小山</a></dd>
                <dd><a href='/0/15/13326.html' >第三百六十六章 重狱峰</a></dd>
                <dd><a href='/0/15/13327.html' >第三百六十七章 造化境小成</a></dd>
                <dd><a href='/0/15/13328.html' >第三百六十八章 给脸不要脸</a></dd>
                    
                      
                <dd><a href='/0/15/13329.html' >第三百六十九章 不留情面</a></dd>
                <dd><a href='/0/15/13330.html' >第三百七十章 再次相对</a></dd>
                <dd><a href='/0/15/13331.html' >第三百七十一章 残酷</a></dd>
                <dd><a href='/0/15/13332.html' >第三百七十二章 赶往皇城</a></dd>
                    
                      
                <dd><a href='/0/15/13333.html' >第三百七十三章 天才云集</a></dd>
                <dd><a href='/0/15/13334.html' >第三百七十四章 青衫莫凌</a></dd>
                <dd><a href='/0/15/13335.html' >第三百七十五章 选拔开始</a></dd>
                <dd><a href='/0/15/13336.html' >第三百七十六章 搬山二将</a></dd>
                    
                      
                <dd><a href='/0/15/13337.html' >第三百七十七章 皇普影</a></dd>
                <dd><a href='/0/15/13338.html' >第三百七十八章 暗袭之术</a></dd>
                <dd><a href='/0/15/13339.html' >第三百七十九章 破影</a></dd>
                <dd><a href='/0/15/13340.html' >第三百八十章 最后的对手</a></dd>
                    
                      
                <dd><a href='/0/15/13341.html' >第三百八十一章 王钟</a></dd>
                <dd><a href='/0/15/13342.html' >第三百八十二章 血魔修罗枪</a></dd>
                <dd><a href='/0/15/13343.html' >第三百八十三章 苦战</a></dd>
                <dd><a href='/0/15/13344.html' >第三百八十四章 血战</a></dd>
                    
                      
                <dd><a href='/0/15/13345.html' >第三百八十五章 名额</a></dd>
                <dd><a href='/0/15/13346.html' >第三百八十六章 选拔落幕</a></dd>
                <dd><a href='/0/15/13347.html' >第三百八十七章 暴怒的王雷</a></dd>
                <dd><a href='/0/15/13348.html' >第三百八十八章 夜谈</a></dd>
                    
                      
                <dd><a href='/0/15/13349.html' >第三百八十九章 圣灵潭</a></dd>
                <dd><a href='/0/15/13350.html' >第三百九十章 各施手段</a></dd>
                <dd><a href='/0/15/13351.html' >第三百九十一章 抢夺能量</a></dd>
                <dd><a href='/0/15/13352.html' >第三百九十二章 抢光</a></dd>
                    
                      
                <dd><a href='/0/15/13353.html' >第三百九十三章 林琅天体内的神秘存在</a></dd>
                <dd><a href='/0/15/13354.html' >第三百九十四章 收获不小</a></dd>
                <dd><a href='/0/15/13355.html' >第三百九十五章 骨枪</a></dd>
                <dd><a href='/0/15/13356.html' >第三百九十六章 炼化天鳄骨枪</a></dd>
                    
                      
                <dd><a href='/0/15/13357.html' >第三百九十七章 血灵傀之变</a></dd>
                <dd><a href='/0/15/13358.html' >第三百九十八章 进入远古战场！</a></dd>
                <dd><a href='/0/15/13359.html' >第三百九十九章 陌生的空间</a></dd>
                <dd><a href='/0/15/13360.html' >第四百章 聚集点</a></dd>
                    
                      
                <dd><a href='/0/15/13361.html' >第四百零一章 圣光王朝</a></dd>
                <dd><a href='/0/15/13362.html' >第四百零二章 妖潮</a></dd>
                <dd><a href='/0/15/13363.html' >第四百零三章 冲突</a></dd>
                <dd><a href='/0/15/13364.html' >第四百零四章 屠戮</a></dd>
                    
                      
                <dd><a href='/0/15/13365.html' >第四百零五章 虎口夺食</a></dd>
                <dd><a href='/0/15/13366.html' >第四百零六章 黎盛</a></dd>
                <dd><a href='/0/15/13367.html' >第四百零七章 战造化境巅峰</a></dd>
                <dd><a href='/0/15/13368.html' >第四百零八章 圣象崩天撞</a></dd>
                    
                      
                <dd><a href='/0/15/13369.html' >第四百零九章 五指动乾坤</a></dd>
                <dd><a href='/0/15/13370.html' >第四百一十章 尽数轰杀</a></dd>
                <dd><a href='/0/15/13371.html' >第四百一十一章 逼走</a></dd>
                <dd><a href='/0/15/13372.html' >第四百一十二章 清点收获</a></dd>
                    
                      
                <dd><a href='/0/15/13373.html' >第四百一十三章 圣光王朝大师兄</a></dd>
                <dd><a href='/0/15/13374.html' >第四百一十四章 情报</a></dd>
                <dd><a href='/0/15/13375.html' >第四百一十五章 小涅盘金身</a></dd>
                <dd><a href='/0/15/13376.html' >第四百一十六章 修炼金身</a></dd>
                    
                      
                <dd><a href='/0/15/13377.html' >第四百一十七章 麻烦上门</a></dd>
                <dd><a href='/0/15/13378.html' >第四百一十八章 轰杀</a></dd>
                <dd><a href='/0/15/13379.html' >第四百一十九章 前往阳城</a></dd>
                <dd><a href='/0/15/13380.html' >第四百二十章 三人突破</a></dd>
                    
                      
                <dd><a href='/0/15/13381.html' >第四百二十一章 交易场</a></dd>
                <dd><a href='/0/15/13382.html' >第四百二十二章 晋牧</a></dd>
                <dd><a href='/0/15/13383.html' >第四百二十三章 对战半步涅盘</a></dd>
                <dd><a href='/0/15/13384.html' >第四百二十四章 震慑</a></dd>
                    
                      
                <dd><a href='/0/15/13385.html' >第四百二十五章 名誉扫地</a></dd>
                <dd><a href='/0/15/13386.html' >第四百二十六章 凑齐</a></dd>
                <dd><a href='/0/15/13387.html' >第四百二十七章 天符灵树</a></dd>
                <dd><a href='/0/15/13388.html' >第四百二十八章 净化血灵傀</a></dd>
                    
                      
                <dd><a href='/0/15/13389.html' >第四百二十九章 动身</a></dd>
                <dd><a href='/0/15/13390.html' >第四百三十章 进入雷岩山脉</a></dd>
                <dd><a href='/0/15/13391.html' >第四百三十一章 再遇妖潮</a></dd>
                <dd><a href='/0/15/13392.html' >第四百三十二章 斩杀</a></dd>
                    
                      
                <dd><a href='/0/15/13393.html' >第四百三十三章 狠毒</a></dd>
                <dd><a href='/0/15/13394.html' >第四百三十四章 收割</a></dd>
                <dd><a href='/0/15/13395.html' >第四百三十五章 再度提升</a></dd>
                <dd><a href='/0/15/13396.html' >第四百三十六章 讨债</a></dd>
                    
                      
                <dd><a href='/0/15/13397.html' >第四百三十七章 斩杀晋牧</a></dd>
                <dd><a href='/0/15/13398.html' >第四百三十八章 凌志，柳元</a></dd>
                <dd><a href='/0/15/13399.html' >第四百三十九章 雷岩谷</a></dd>
                <dd><a href='/0/15/13400.html' >第四百四十章 两大高级王朝</a></dd>
                    
                      
                <dd><a href='/0/15/13401.html' >第四百四十一章 赌约</a></dd>
                <dd><a href='/0/15/13402.html' >第四百四十二章 承让</a></dd>
                <dd><a href='/0/15/13403.html' >第四百四十三章 暗流涌动</a></dd>
                <dd><a href='/0/15/13404.html' >第四百四十四章 石殿</a></dd>
                    
                      
                <dd><a href='/0/15/13405.html' >第四百四十五章 树纹符文</a></dd>
                <dd><a href='/0/15/13406.html' >第四百四十六章 底牌</a></dd>
                <dd><a href='/0/15/13407.html' >第四百四十七章 主殿</a></dd>
                <dd><a href='/0/15/13408.html' >第四百四十八章 机关</a></dd>
                    
                      
                <dd><a href='/0/15/13409.html' >第四百四十九章 石像</a></dd>
                <dd><a href='/0/15/13410.html' >第四百五十章 红衣女子</a></dd>
                <dd><a href='/0/15/13411.html' >第四百五十一章 穆红绫</a></dd>
                <dd><a href='/0/15/13412.html' >第四百五十二章 变故</a></dd>
                    
                      
                <dd><a href='/0/15/13413.html' >第四百五十三章 夺舍</a></dd>
                <dd><a href='/0/15/13414.html' >第四百五十四章 天符师</a></dd>
                <dd><a href='/0/15/13415.html' >第四百五十五章 李盘</a></dd>
                <dd><a href='/0/15/13416.html' >第四百五十六章 现身</a></dd>
                    
                      
                <dd><a href='/0/15/13417.html' >第四百五十七章 天符师的强大</a></dd>
                <dd><a href='/0/15/13418.html' >第四百五十八章 杀手</a></dd>
                <dd><a href='/0/15/13419.html' >第四百五十九章 麻烦</a></dd>
                <dd><a href='/0/15/13420.html' >第四百六十章 算计</a></dd>
                    
                      
                <dd><a href='/0/15/13421.html' >第四百六十一章 来临</a></dd>
                <dd><a href='/0/15/13422.html' >第四百六十二章 交手</a></dd>
                <dd><a href='/0/15/13423.html' >第四百六十三章 雷蛇</a></dd>
                <dd><a href='/0/15/13424.html' >第四百六十四章 吞噬之界</a></dd>
                    
                      
                <dd><a href='/0/15/13425.html' >第四百六十五章 肥羊</a></dd>
                <dd><a href='/0/15/13426.html' >第四百六十六章 绑架勒索</a></dd>
                <dd><a href='/0/15/13427.html' >第四百六十七章 冲击半步涅盘</a></dd>
                <dd><a href='/0/15/13428.html' >第四百六十八章 取丹</a></dd>
                    
                      
                <dd><a href='/0/15/13429.html' >第四百六十九章 石轩</a></dd>
                <dd><a href='/0/15/13430.html' >第四百七十章 一元涅盘</a></dd>
                <dd><a href='/0/15/13431.html' >第四百七十一章 状况</a></dd>
                <dd><a href='/0/15/13432.html' >第四百七十二章 体内阵法</a></dd>
                    
                      
                <dd><a href='/0/15/13433.html' >第四百七十三章 乾坤古阵</a></dd>
                <dd><a href='/0/15/13434.html' >第四百七十四章 改变血脉</a></dd>
                <dd><a href='/0/15/13435.html' >第四百七十五章 远古之地</a></dd>
                <dd><a href='/0/15/13436.html' >第四百七十六章 大力裂地虎</a></dd>
                    
                      
                <dd><a href='/0/15/13437.html' >第四百七十七章 激斗</a></dd>
                <dd><a href='/0/15/13438.html' >第四百七十八章 出手</a></dd>
                <dd><a href='/0/15/13439.html' >第四百七十九章 惊退</a></dd>
                <dd><a href='/0/15/13440.html' >第四百八十章 虎骨到手</a></dd>
                    
                      
                <dd><a href='/0/15/13441.html' >第四百八十一章 融合虎骨</a></dd>
                <dd><a href='/0/15/13442.html' >第四百八十二章 脱胎换骨的小炎</a></dd>
                <dd><a href='/0/15/13443.html' >第四百八十三章 三兄弟</a></dd>
                <dd><a href='/0/15/13444.html' >第四百八十四章 远古之殿</a></dd>
                    
                      
                <dd><a href='/0/15/13445.html' >第四百八十五章 大殿</a></dd>
                <dd><a href='/0/15/13446.html' >第四百八十六章 小炎之威</a></dd>
                <dd><a href='/0/15/13447.html' >第四百八十七章 精元大吞掌</a></dd>
                <dd><a href='/0/15/13448.html' >第四百八十八章 立威</a></dd>
                    
                      
                <dd><a href='/0/15/13449.html' >第四百八十九章 各方势力</a></dd>
                <dd><a href='/0/15/13450.html' >第四百九十章 秘藏开启</a></dd>
                <dd><a href='/0/15/13451.html' >第四百九十一章 金身舍利</a></dd>
                <dd><a href='/0/15/13452.html' >第四百九十二章 丹河</a></dd>
                    
                      
                <dd><a href='/0/15/13453.html' >第四百九十三章 天鹰王朝</a></dd>
                <dd><a href='/0/15/13454.html' >第四百九十四章 冲击涅盘</a></dd>
                <dd><a href='/0/15/13455.html' >第四百九十五章 双劫齐至</a></dd>
                <dd><a href='/0/15/13456.html' >第四百九十六章 厚积薄发</a></dd>
                    
                      
                <dd><a href='/0/15/13457.html' >第四百九十七章 实力大涨</a></dd>
                <dd><a href='/0/15/13458.html' >第四百九十八章 摧枯拉朽</a></dd>
                <dd><a href='/0/15/13459.html' >第四百九十九章 麻烦上门</a></dd>
                <dd><a href='/0/15/13460.html' >第五百章 灵武学</a></dd>
                    
                      
                <dd><a href='/0/15/13461.html' >第五百零一章 灵武学</a></dd>
                <dd><a href='/0/15/13462.html' >第五百零二章 再遇</a></dd>
                <dd><a href='/0/15/13463.html' >第五百零三章 宗派遗迹</a></dd>
                <dd><a href='/0/15/13464.html' >第五百零四章 威慑力</a></dd>
                    
                      
                <dd><a href='/0/15/13465.html' >第五百零五章 柳白</a></dd>
                <dd><a href='/0/15/13466.html' >第五百零六章 天罡联盟</a></dd>
                <dd><a href='/0/15/13467.html' >第五百零七章 涅盘焚天阵</a></dd>
                <dd><a href='/0/15/13468.html' >第五百零八章 涅盘魔炎</a></dd>
                    
                      
                <dd><a href='/0/15/13469.html' >第五百零九章 神秘人</a></dd>
                <dd><a href='/0/15/13470.html' >第五百一十章 八极宗</a></dd>
                <dd><a href='/0/15/13471.html' >第五百一十一章 魔龙犬</a></dd>
                <dd><a href='/0/15/13472.html' >第五百一十二章 掌印，拳印，指洞</a></dd>
                    
                      
                <dd><a href='/0/15/13473.html' >第五百一十三章 磅礴拳意</a></dd>
                <dd><a href='/0/15/13474.html' >第五百一十四章 八极拳意</a></dd>
                <dd><a href='/0/15/13475.html' >第五百一十五章 拳意之威</a></dd>
                <dd><a href='/0/15/13476.html' >第五百一十六章 轰翻</a></dd>
                    
                      
                <dd><a href='/0/15/13477.html' >第五百一十七章 四玄宗遗迹</a></dd>
                <dd><a href='/0/15/13478.html' >第五百一十八章 丹场</a></dd>
                <dd><a href='/0/15/13479.html' >第五百一十九章 丹室</a></dd>
                <dd><a href='/0/15/13480.html' >第五百二十章 生死转轮丹</a></dd>
                    
                      
                <dd><a href='/0/15/13481.html' >第五百二十一章 暴狼田震</a></dd>
                <dd><a href='/0/15/13482.html' >第五百二十二章 小炎战田震</a></dd>
                <dd><a href='/0/15/13483.html' >第五百二十三章 再遇</a></dd>
                <dd><a href='/0/15/13484.html' >第五百二十四章 灵武学之斗</a></dd>
                    
                      
                <dd><a href='/0/15/13485.html' >第五百二十五章 群雄</a></dd>
                <dd><a href='/0/15/13486.html' >第五百二十六章 青铜大门</a></dd>
                <dd><a href='/0/15/13487.html' >第五百二十七章 动用底牌</a></dd>
                <dd><a href='/0/15/13488.html' >第五百二十八章 召唤远古天鳄</a></dd>
                    
                      
                <dd><a href='/0/15/13489.html' >第五百二十九章 天鳄之威</a></dd>
                <dd><a href='/0/15/13490.html' >第五百三十章 杀心</a></dd>
                <dd><a href='/0/15/13491.html' >第五百三十一章 斩杀？</a></dd>
                <dd><a href='/0/15/13492.html' >第五百三十二章 进入青铜大门</a></dd>
                    
                      
                <dd><a href='/0/15/13493.html' >第五百三十三章</a></dd>
                <dd><a href='/0/15/13494.html' >第五百三十四章</a></dd>
                <dd><a href='/0/15/13495.html' >第五百三十五章</a></dd>
                <dd><a href='/0/15/13496.html' >第五百三十六章 神秘的青雉</a></dd>
                    
                      
                <dd><a href='/0/15/13497.html' >第五百三十七章 青天化龙诀</a></dd>
                <dd><a href='/0/15/13498.html' >第五百三十八章 闭关</a></dd>
                <dd><a href='/0/15/13499.html' >第五百三十九章 第三次涅盘劫</a></dd>
                <dd><a href='/0/15/13500.html' >第五百四十章 对抗</a></dd>
                    
                      
                <dd><a href='/0/15/13501.html' >第五百四十一章 涅盘火雷珠</a></dd>
                <dd><a href='/0/15/13502.html' >第五百四十二章 真正的天妖貂</a></dd>
                <dd><a href='/0/15/13503.html' >第五百四十三章 神秘老人</a></dd>
                <dd><a href='/0/15/13504.html' >第五百四十四章 出关</a></dd>
                    
                      
                <dd><a href='/0/15/13505.html' >第五百四十五章 大乾王朝</a></dd>
                <dd><a href='/0/15/13506.html' >第五百四十六章 火将，山将</a></dd>
                <dd><a href='/0/15/13507.html' >第五百四十七章 针锋相对</a></dd>
                <dd><a href='/0/15/13508.html' >第五百四十八章 激战</a></dd>
                    
                      
                <dd><a href='/0/15/13509.html' >第五百四十九章 青龙撕天手</a></dd>
                <dd><a href='/0/15/13510.html' >第五百五十章 败二将</a></dd>
                <dd><a href='/0/15/13511.html' >第五百五十一章 离去</a></dd>
                <dd><a href='/0/15/13512.html' >第五百五十二章 被盯上了</a></dd>
                    
                      
                <dd><a href='/0/15/13513.html' >第五百五十三章 小貂之力</a></dd>
                <dd><a href='/0/15/13514.html' >第五百五十四章 夜遇</a></dd>
                <dd><a href='/0/15/13515.html' >第五百五十五章 苏柔</a></dd>
                <dd><a href='/0/15/13516.html' >第五百五十六章 出手</a></dd>
                    
                      
                <dd><a href='/0/15/13517.html' >第五百五十七章 狠手段</a></dd>
                <dd><a href='/0/15/13518.html' >第五百五十八章 同行</a></dd>
                <dd><a href='/0/15/13519.html' >第五百五十九章 涅盘碑</a></dd>
                <dd><a href='/0/15/13520.html' >第五百六十章 涅盘碑测试</a></dd>
                    
                      
                <dd><a href='/0/15/13521.html' >第五百六十一章 常凌</a></dd>
                <dd><a href='/0/15/13522.html' >第五百六十二章 包揽</a></dd>
                <dd><a href='/0/15/13523.html' >第五百六十三章 万象拍卖会</a></dd>
                <dd><a href='/0/15/13524.html' >第五百六十四章 罗通</a></dd>
                    
                      
                <dd><a href='/0/15/13525.html' >第五百六十五章 强势对碰</a></dd>
                <dd><a href='/0/15/13526.html' >第五百六十六章 青龙指</a></dd>
                <dd><a href='/0/15/13527.html' >第五百六十七章 风雨欲来</a></dd>
                <dd><a href='/0/15/13528.html' >第五百六十八章 四大超级王朝</a></dd>
                    
                      
                <dd><a href='/0/15/13529.html' >第五百六十九章 拍卖会开始</a></dd>
                <dd><a href='/0/15/13530.html' >第五百七十章 平衡灵果</a></dd>
                <dd><a href='/0/15/13531.html' >第五百七十一章 天荒神牛</a></dd>
                <dd><a href='/0/15/13532.html' >第五百七十二章 黑龙啸天印</a></dd>
                    
                      
                <dd><a href='/0/15/13533.html' >第五百七十三章 财力比拼</a></dd>
                <dd><a href='/0/15/13534.html' >第五百七十四章 最终归属</a></dd>
                <dd><a href='/0/15/13535.html' >第五百七十五章 即将对决</a></dd>
                <dd><a href='/0/15/13536.html' >第五百七十六章 百朝大战，开启！</a></dd>
                    
                      
                <dd><a href='/0/15/13537.html' >第五百七十七章 对决</a></dd>
                <dd><a href='/0/15/13538.html' >第五百七十八章 血战</a></dd>
                <dd><a href='/0/15/13539.html' >第五百七十七章 天阶灵宝的威力</a></dd>
                <dd><a href='/0/15/13540.html' >第五百七十八章 惊天动地</a></dd>
                    
                      
                <dd><a href='/0/15/13541.html' >第五百七十九章 夺宝</a></dd>
                <dd><a href='/0/15/13542.html' >第五百八十章 败亡</a></dd>
                <dd><a href='/0/15/13543.html' >第五百八十一章 序幕拉开</a></dd>
                <dd><a href='/0/15/13544.html' >第五百八十二章 死灵将</a></dd>
                    
                      
                <dd><a href='/0/15/13545.html' >第五百八十三章 二段封印</a></dd>
                <dd><a href='/0/15/13546.html' >第五百八十四章 苏醒</a></dd>
                <dd><a href='/0/15/13547.html' >第五百八十五章 赶尽杀绝</a></dd>
                <dd><a href='/0/15/13548.html' >第五百八十六章 实力精进</a></dd>
                    
                      
                <dd><a href='/0/15/13549.html' >第五百八十七章 挺进深处</a></dd>
                <dd><a href='/0/15/13550.html' >第五百八十八章 敢不敢</a></dd>
                <dd><a href='/0/15/13551.html' >第五百八十九章 抗</a></dd>
                <dd><a href='/0/15/13552.html' >第五百九十章 地煞联盟</a></dd>
                    
                      
                <dd><a href='/0/15/13553.html' >第五百九十一章 对头</a></dd>
                <dd><a href='/0/15/13554.html' >第五百九十二章 找上门来</a></dd>
                <dd><a href='/0/15/13555.html' >第五百九十三章 萧山</a></dd>
                <dd><a href='/0/15/13556.html' >第五百九十四章 龙灵战朱厌</a></dd>
                    
                      
                <dd><a href='/0/15/13557.html' >第五百九十五章 横扫</a></dd>
                <dd><a href='/0/15/13558.html' >第五百九十六章 再遇</a></dd>
                <dd><a href='/0/15/13559.html' >第五百九十七章 蓝樱</a></dd>
                <dd><a href='/0/15/13560.html' >第五百九十八章 七大超级宗派</a></dd>
                    
                      
                <dd><a href='/0/15/13561.html' >第五百九十九章 合作</a></dd>
                <dd><a href='/0/15/13562.html' >第六百章 应战</a></dd>
                <dd><a href='/0/15/13563.html' >第六百零一章 宋家三魔</a></dd>
                <dd><a href='/0/15/13564.html' >第六百零二章 怪异之举</a></dd>
                    
                      
                <dd><a href='/0/15/13565.html' >第六百零三章 变态啊</a></dd>
                <dd><a href='/0/15/13566.html' >第六百零四章 四元涅盘境</a></dd>
                <dd><a href='/0/15/13567.html' >第六百零五章 饕鬄凶灵</a></dd>
                <dd><a href='/0/15/13568.html' >第六百零六章 吞食与吞噬</a></dd>
                    
                      
                <dd><a href='/0/15/13569.html' >第六百零七章 胜负</a></dd>
                <dd><a href='/0/15/13570.html' >第六百零八章 你还有力量么？</a></dd>
                <dd><a href='/0/15/13571.html' >第六百零九章 惨</a></dd>
                <dd><a href='/0/15/13572.html' >第六百一十章 秦天</a></dd>
                    
                      
                <dd><a href='/0/15/13573.html' >第六百一十一章 百朝山开</a></dd>
                <dd><a href='/0/15/13574.html' >第六百一十二章 上山</a></dd>
                <dd><a href='/0/15/13575.html' >第六百一十三章 八大超级宗派</a></dd>
                <dd><a href='/0/15/13576.html' >第六百一十四章 熟面孔</a></dd>
                    
                      
                <dd><a href='/0/15/13577.html' >第六百一十五章 涅盘金榜之战</a></dd>
                <dd><a href='/0/15/13578.html' >第六百一十六章 合作</a></dd>
                <dd><a href='/0/15/13579.html' >第六百一十七章 再战林琅天</a></dd>
                <dd><a href='/0/15/13580.html' >第六百一十八章 聚武灵</a></dd>
                    
                      
                <dd><a href='/0/15/13581.html' >第六百一十九章 手段尽施</a></dd>
                <dd><a href='/0/15/13582.html' >第六百二十章 不动青龙钟</a></dd>
                <dd><a href='/0/15/13583.html' >第六百二十一章 暴力</a></dd>
                <dd><a href='/0/15/13584.html' >第六百二十二章 斩杀林琅天</a></dd>
                    
                      
                <dd><a href='/0/15/13585.html' >第六百二十三章 斩尽杀绝</a></dd>
                <dd><a href='/0/15/13586.html' >第六百二十四章 争夺空间</a></dd>
                <dd><a href='/0/15/13587.html' >第六百二十五章 曹羽</a></dd>
                <dd><a href='/0/15/13588.html' >第六百二十六章 出手</a></dd>
                    
                      
                <dd><a href='/0/15/13589.html' >第六百二十七章 底牌尽出</a></dd>
                <dd><a href='/0/15/13590.html' >第六百二十八章 叠加</a></dd>
                <dd><a href='/0/15/13591.html' >第六百二十九章 三劫叠加</a></dd>
                <dd><a href='/0/15/13592.html' >第六百三十章 雷劫憾阵</a></dd>
                    
                      
                <dd><a href='/0/15/13593.html' >第六百三十一章 解困</a></dd>
                <dd><a href='/0/15/13594.html' >第六百三十二章 再见绫清竹？</a></dd>
                <dd><a href='/0/15/13595.html' >第六百三十三章 四年</a></dd>
                <dd><a href='/0/15/13596.html' >第六百三十四章 来历</a></dd>
                    
                      
                <dd><a href='/0/15/13597.html' >第六百三十五章 挑选宗派</a></dd>
                <dd><a href='/0/15/13598.html' >第六百三十六章 加入道宗</a></dd>
                <dd><a href='/0/15/13599.html' >第六百三十七章 百朝大战落幕</a></dd>
                <dd><a href='/0/15/13600.html' >第六百三十八章 震撼大炎</a></dd>
                    
                      
                <dd><a href='/0/15/13601.html' >第六百三十九章 道域，道宗！</a></dd>
                <dd><a href='/0/15/13602.html' >第六百四十章 四大奇经</a></dd>
                <dd><a href='/0/15/13603.html' >第六百四十一章 择殿</a></dd>
                <dd><a href='/0/15/13604.html' >第六百四十二章 赏赐</a></dd>
                    
                      
                <dd><a href='/0/15/13605.html' >第六百四十三章 指教</a></dd>
                <dd><a href='/0/15/13606.html' >第六百四十四章 交手</a></dd>
                <dd><a href='/0/15/13607.html' >第六百四十五章 荒刀</a></dd>
                <dd><a href='/0/15/13608.html' >第六百四十六章</a></dd>
                    
                      
                <dd><a href='/0/15/13609.html' >第六百四十七章 涅盘金气</a></dd>
                <dd><a href='/0/15/13610.html' >第六百四十八章 丹河之底</a></dd>
                <dd><a href='/0/15/13611.html' >第六百四十九章 动静</a></dd>
                <dd><a href='/0/15/13612.html' >第六百五十章 轰动</a></dd>
                    
                      
                <dd><a href='/0/15/13613.html' >第六百五十一章 龙元轮</a></dd>
                <dd><a href='/0/15/13614.html' >第六百五十二章 五元涅盘劫</a></dd>
                <dd><a href='/0/15/13615.html' >第六百五十三章 破河而出</a></dd>
                <dd><a href='/0/15/13616.html' >第六百五十四章 亲传大弟子</a></dd>
                    
                      
                <dd><a href='/0/15/13617.html' >第六百五十五章 蒋浩的阻拦</a></dd>
                <dd><a href='/0/15/13618.html' >第六百五十六章 武学殿</a></dd>
                <dd><a href='/0/15/13619.html' >第六百五十七章 荒决</a></dd>
                <dd><a href='/0/15/13620.html' >第六百五十八章 荒石</a></dd>
                    
                      
                <dd><a href='/0/15/13621.html' >第六百五十九章 凝聚荒种</a></dd>
                <dd><a href='/0/15/13622.html' >第六百六十章 四座石碑</a></dd>
                <dd><a href='/0/15/13623.html' >第六百六十一章 荒芜妖眼</a></dd>
                <dd><a href='/0/15/13624.html' >第六百六十二章 荒</a></dd>
                    
                      
                <dd><a href='/0/15/13625.html' >第六百六十三章 成功与否？</a></dd>
                <dd><a href='/0/15/13626.html' >第六百六十四章 月比</a></dd>
                <dd><a href='/0/15/13627.html' >第六百六十五章 激斗蒋浩</a></dd>
                <dd><a href='/0/15/13628.html' >第六百六十六章 大星罡拳</a></dd>
                    
                      
                <dd><a href='/0/15/13629.html' >第六百六十七章 妖眼之力</a></dd>
                <dd><a href='/0/15/13630.html' >第六百六十八章 第五位亲传大弟子</a></dd>
                <dd><a href='/0/15/13631.html' >第六百六十九章 月谈</a></dd>
                <dd><a href='/0/15/13632.html' >第六百七十章 宁静</a></dd>
                    
                      
                <dd><a href='/0/15/13633.html' >第六百七十一章 出宗</a></dd>
                <dd><a href='/0/15/13634.html' >第六百七十二章 血岩地</a></dd>
                <dd><a href='/0/15/13635.html' >第六百七十三章 仙元古树</a></dd>
                <dd><a href='/0/15/13636.html' >第六百七十四章 猿王</a></dd>
                    
                      
                <dd><a href='/0/15/13637.html' >第六百七十五章 斗猿王</a></dd>
                <dd><a href='/0/15/13638.html' >第六百七十六章 斩杀</a></dd>
                <dd><a href='/0/15/13639.html' >第六百七十七章 动静</a></dd>
                <dd><a href='/0/15/13640.html' >第六百七十八章 不妙</a></dd>
                    
                      
                <dd><a href='/0/15/13641.html' >第六百七十九章 麻烦的局面</a></dd>
                <dd><a href='/0/15/13642.html' >第六百八十章 激斗屠夫</a></dd>
                <dd><a href='/0/15/13643.html' >第六百八十一章 荒兽之灵</a></dd>
                <dd><a href='/0/15/13644.html' >第六百八十二章 撤退</a></dd>
                    
                      
                <dd><a href='/0/15/13645.html' >第六百八十三章 无相菩提音</a></dd>
                <dd><a href='/0/15/13646.html' >第六百八十四章 救人</a></dd>
                <dd><a href='/0/15/13647.html' >第六百八十五章 恩怨</a></dd>
                <dd><a href='/0/15/13648.html' >第六百八十六章 血斗</a></dd>
                    
                      
                <dd><a href='/0/15/13649.html' >第六百八十七章 吞噬仙元古果</a></dd>
                <dd><a href='/0/15/13650.html' >第六百八十八章 斩杀苏雷</a></dd>
                <dd><a href='/0/15/13651.html' >第六百八十九章 魔元咒体</a></dd>
                <dd><a href='/0/15/13652.html' >第六百九十章 重伤</a></dd>
                    
                      
                <dd><a href='/0/15/13653.html' >第六百九十一章 休养</a></dd>
                <dd><a href='/0/15/13654.html' >第六百九十二章 应笑笑，青叶</a></dd>
                <dd><a href='/0/15/13655.html' >第六百九十三章 道宗掌教</a></dd>
                <dd><a href='/0/15/13656.html' >第六百九十四章 锁灵阵</a></dd>
                    
                      
                <dd><a href='/0/15/13657.html' >第六百九十五章 再渡双劫</a></dd>
                <dd><a href='/0/15/13658.html' >第六百九十六章 大荒芜碑</a></dd>
                <dd><a href='/0/15/13659.html' >第六百九十七章 波动</a></dd>
                <dd><a href='/0/15/13660.html' >第六百九十八章 荒芜</a></dd>
                    
                      
                <dd><a href='/0/15/13661.html' >第六百九十九章 你病了</a></dd>
                <dd><a href='/0/15/13662.html' >第七百章 破局</a></dd>
                <dd><a href='/0/15/13663.html' >第七百零一章 未知生物</a></dd>
                <dd><a href='/0/15/13664.html' >第七百零二章 参悟大荒芜经</a></dd>
                    
                      
                <dd><a href='/0/15/13665.html' >第七百零三章 成功</a></dd>
                <dd><a href='/0/15/13666.html' >第七百零四章 拜山</a></dd>
                <dd><a href='/0/15/13667.html' >第七百零五章 洪崖洞</a></dd>
                <dd><a href='/0/15/13668.html' >第七百零六章 暴力</a></dd>
                    
                      
                <dd><a href='/0/15/13669.html' >第七百零七章 洪崖洞经</a></dd>
                <dd><a href='/0/15/13670.html' >第七百零八章 强化的大荒囚天手</a></dd>
                <dd><a href='/0/15/13671.html' >第七百零九章 弹琴的少女</a></dd>
                <dd><a href='/0/15/13672.html' >第七百一十章 王阎</a></dd>
                    
                      
                <dd><a href='/0/15/13673.html' >第七百一十一章 对恃</a></dd>
                <dd><a href='/0/15/13674.html' >第七百一十二章 殿试开始</a></dd>
                <dd><a href='/0/15/13675.html' >第七百一十三章 对战应欢欢</a></dd>
                <dd><a href='/0/15/13676.html' >第七百一十四章 对手</a></dd>
                    
                      
                <dd><a href='/0/15/13677.html' >第七百一十五章 顶尖交锋</a></dd>
                <dd><a href='/0/15/13678.html' >第七百一十六章 激战</a></dd>
                <dd><a href='/0/15/13679.html' >第七百一十七章 地龙封神印</a></dd>
                <dd><a href='/0/15/13680.html' >第七百一十八章 龙翼</a></dd>
                    
                      
                <dd><a href='/0/15/13681.html' >第七百一十九章 最顶尖的较量</a></dd>
                <dd><a href='/0/15/13682.html' >第七百二十章 王阎对应笑笑</a></dd>
                <dd><a href='/0/15/13683.html' >第七百二十一章 天皇经的对碰</a></dd>
                <dd><a href='/0/15/13684.html' >第七百二十二章 出手</a></dd>
                    
                      
                <dd><a href='/0/15/13685.html' >第七百二十三章 龙争虎斗</a></dd>
                <dd><a href='/0/15/13686.html' >第七百二十四章 黑魔鉴VS大荒芜经</a></dd>
                <dd><a href='/0/15/13687.html' >第七百二十五章 惨烈</a></dd>
                <dd><a href='/0/15/13688.html' >第七百二十六章 胜败</a></dd>
                    
                      
                <dd><a href='/0/15/13689.html' >第七百二十七章 指挥权归属</a></dd>
                <dd><a href='/0/15/13690.html' >第七百二十八章 选宝</a></dd>
                <dd><a href='/0/15/13691.html' >第七百二十九章 静止之牌</a></dd>
                <dd><a href='/0/15/13692.html' >第七百三十章 妖灵烙印的动静</a></dd>
                    
                      
                <dd><a href='/0/15/13693.html' >第七百三十一章 借琴</a></dd>
                <dd><a href='/0/15/13694.html' >第七百三十二章 三人再聚</a></dd>
                <dd><a href='/0/15/13695.html' >第七百三十三章 地心孕神涎</a></dd>
                <dd><a href='/0/15/13696.html' >第七百三十四章 魔音山</a></dd>
                    
                      
                <dd><a href='/0/15/13697.html' >第七百三十五章 突来之人</a></dd>
                <dd><a href='/0/15/13698.html' >第七百三十六章 变故</a></dd>
                <dd><a href='/0/15/13699.html' >第七百三十七章 局势转变</a></dd>
                <dd><a href='/0/15/13700.html' >第七百三十八章 不过如此</a></dd>
                    
                      
                <dd><a href='/0/15/13701.html' >第七百三十九章 斩草除根</a></dd>
                <dd><a href='/0/15/13702.html' >第七百四十章 天妖貂的力量</a></dd>
                <dd><a href='/0/15/13703.html' >第七百四十一章 收获颇丰</a></dd>
                <dd><a href='/0/15/13704.html' >第七百四十二章 斗法</a></dd>
                    
                      
                <dd><a href='/0/15/13705.html' >第七百四十三章 抹除</a></dd>
                <dd><a href='/0/15/13706.html' >第七百四十四章 破丹孕神</a></dd>
                <dd><a href='/0/15/13707.html' >第七百四十五章 实力大涨</a></dd>
                <dd><a href='/0/15/13708.html' >第七百四十六章 轮回者</a></dd>
                    
                      
                <dd><a href='/0/15/13709.html' >第七百四十七章 回宗</a></dd>
                <dd><a href='/0/15/13710.html' >第七百四十八章 谈话</a></dd>
                <dd><a href='/0/15/13711.html' >第七百四十九章 可还记得</a></dd>
                <dd><a href='/0/15/13712.html' >第七百五十章 动身</a></dd>
                    
                      
                <dd><a href='/0/15/13713.html' >第七百五十一章 异魔城</a></dd>
                <dd><a href='/0/15/13714.html' >第七百五十二章 冲突</a></dd>
                <dd><a href='/0/15/13715.html' >第七百五十三章 如鹰如隼</a></dd>
                <dd><a href='/0/15/13716.html' >第七百五十四章 滑稽的交手</a></dd>
                    
                      
                <dd><a href='/0/15/13717.html' >第七百五十五章 认识一下</a></dd>
                <dd><a href='/0/15/13718.html' >第七百五十六章 五年后的见面</a></dd>
                <dd><a href='/0/15/13719.html' >第七百五十七章 想死？</a></dd>
                <dd><a href='/0/15/13720.html' >第七百五十八章 焚天古藏</a></dd>
                    
                      
                <dd><a href='/0/15/13721.html' >第七百五十九章 妖孽云集</a></dd>
                <dd><a href='/0/15/13722.html' >第七百六十章 针锋相对</a></dd>
                <dd><a href='/0/15/13723.html' >第七百六十一章 异魔域，开启</a></dd>
                <dd><a href='/0/15/13724.html' >第七百六十二章 生玄骨珠</a></dd>
                    
                      
                <dd><a href='/0/15/13725.html' >第七百六十三章 变故</a></dd>
                <dd><a href='/0/15/13726.html' >第七百六十四章 苦战魔尸</a></dd>
                <dd><a href='/0/15/13727.html' >第七百六十五章 操控魔尸</a></dd>
                <dd><a href='/0/15/13728.html' >第七百六十六章 骚扰</a></dd>
                    
                      
                <dd><a href='/0/15/13729.html' >第七百六十七章 古藏信息</a></dd>
                <dd><a href='/0/15/13730.html' >第七百六十八章 赶往古藏</a></dd>
                <dd><a href='/0/15/13731.html' >第七百六十九章 借刀杀人</a></dd>
                <dd><a href='/0/15/13732.html' >第七百七十章 兄妹相见</a></dd>
                    
                      
                <dd><a href='/0/15/13733.html' >第七百七十一章 青檀</a></dd>
                <dd><a href='/0/15/13734.html' >第七百七十二章 战书</a></dd>
                <dd><a href='/0/15/13735.html' >第七百七十三章 激战雷千</a></dd>
                <dd><a href='/0/15/13736.html' >第七百七十四章 雷帝典</a></dd>
                    
                      
                <dd><a href='/0/15/13737.html' >第七百七十五章 逆转之威</a></dd>
                <dd><a href='/0/15/13738.html' >第七百七十六章 对恃</a></dd>
                <dd><a href='/0/15/13739.html' >第七百七十七章 焚天古藏开启</a></dd>
                <dd><a href='/0/15/13740.html' >第七百七十八章 诡异的空间</a></dd>
                    
                      
                <dd><a href='/0/15/13741.html' >第七百七十九章 中枢</a></dd>
                <dd><a href='/0/15/13742.html' >第七百八十章 确定</a></dd>
                <dd><a href='/0/15/13743.html' >第七百八十一章 变故</a></dd>
                <dd><a href='/0/15/13744.html' >第七百八十二章 鼎炉</a></dd>
                    
                      
                <dd><a href='/0/15/13745.html' >第七百八十三章 赤袍人</a></dd>
                <dd><a href='/0/15/13746.html' >第七百八十四章 赤袍对黑雾</a></dd>
                <dd><a href='/0/15/13747.html' >第七百八十五章 镇压</a></dd>
                <dd><a href='/0/15/13748.html' >第七百八十六章 焚天</a></dd>
                    
                      
                <dd><a href='/0/15/13749.html' >第七百八十七章 炼化</a></dd>
                <dd><a href='/0/15/13750.html' >第七百八十八章 八元涅盘境</a></dd>
                <dd><a href='/0/15/13751.html' >第七百八十九章 太清仙池</a></dd>
                <dd><a href='/0/15/13752.html' >第七百九十章 杨氏兄弟</a></dd>
                    
                      
                <dd><a href='/0/15/13753.html' >第七百九十一章 武帝典</a></dd>
                <dd><a href='/0/15/13754.html' >第七百九十二章 焚天阵之威</a></dd>
                <dd><a href='/0/15/13755.html' >第七百九十三章 武帝</a></dd>
                <dd><a href='/0/15/13756.html' >第七百九十四章 池底变故</a></dd>
                    
                      
                <dd><a href='/0/15/13757.html' >第七百九十五章 后果</a></dd>
                <dd><a href='/0/15/13758.html' >第七百九十六章 动手</a></dd>
                <dd><a href='/0/15/13759.html' >第七百九十七章 开战</a></dd>
                <dd><a href='/0/15/13760.html' >第七百九十八章 恩怨</a></dd>
                    
                      
                <dd><a href='/0/15/13761.html' >第七百九十九章 弟子之战</a></dd>
                <dd><a href='/0/15/13762.html' >第八百章 混战</a></dd>
                <dd><a href='/0/15/13763.html' >第八百零一章 元苍的灵印</a></dd>
                <dd><a href='/0/15/13764.html' >第八百零二章 两女联手</a></dd>
                    
                      
                <dd><a href='/0/15/13765.html' >第八百零三章 惨烈</a></dd>
                <dd><a href='/0/15/13766.html' >第八百零四章 能耐</a></dd>
                <dd><a href='/0/15/13767.html' >第八百零五章 顶尖交锋</a></dd>
                <dd><a href='/0/15/13768.html' >第八百零六章 再现大荒芜经</a></dd>
                    
                      
                <dd><a href='/0/15/13769.html' >第八百零七章 激斗元苍</a></dd>
                <dd><a href='/0/15/13770.html' >第八百零八章 焚天鼎之威</a></dd>
                <dd><a href='/0/15/13771.html' >第八百零九章 局势转换</a></dd>
                <dd><a href='/0/15/13772.html' >第八百一十章 疯子</a></dd>
                    
                      
                <dd><a href='/0/15/13773.html' >第八百一十一章 荒芜石珠</a></dd>
                <dd><a href='/0/15/13774.html' >第八百一十二章 惨胜</a></dd>
                <dd><a href='/0/15/13775.html' >第八百一十三章 落幕</a></dd>
                <dd><a href='/0/15/13776.html' >第八百一十四章 震动</a></dd>
                    
                      
                <dd><a href='/0/15/13777.html' >第八百一十五章 归来</a></dd>
                <dd><a href='/0/15/13778.html' >第八百一十六章 纠纷</a></dd>
                <dd><a href='/0/15/13779.html' >第八百一十七章 再聚首</a></dd>
                <dd><a href='/0/15/13780.html' >第八百一十八章 小貂之威</a></dd>
                    
                      
                <dd><a href='/0/15/13781.html' >第八百一十九章 以一敌六</a></dd>
                <dd><a href='/0/15/13782.html' >第八百二十章 人元子</a></dd>
                <dd><a href='/0/15/13783.html' >第八百二十一章 惨烈</a></dd>
                <dd><a href='/0/15/13784.html' >第八百二十二章 惨败的三兄弟</a></dd>
                    
                      
                <dd><a href='/0/15/13785.html' >第八百二十三章 一份情</a></dd>
                <dd><a href='/0/15/13786.html' >第八百二十四章 顶尖强者云集</a></dd>
                <dd><a href='/0/15/13787.html' >第八百二十五章 退宗</a></dd>
                <dd><a href='/0/15/13788.html' >第八百二十七章（上） 拼命</a></dd>
                    
                      
                <dd><a href='/0/15/13789.html' >第八百二十七章（下） 空间挪移</a></dd>
                <dd><a href='/0/15/13790.html' >第八百二十八章</a></dd>
                <dd><a href='/0/15/13791.html' >第八百二十九章 逃离</a></dd>
                <dd><a href='/0/15/13792.html' >第八百三十章 他会回来的</a></dd>
                    
                      
                <dd><a href='/0/15/13793.html' >第八百三十一章 陌生的地方</a></dd>
                <dd><a href='/0/15/13794.html' >第八百三十二章 乱魔海，天风海域</a></dd>
                <dd><a href='/0/15/13795.html' >第八百三十三章 生生玄灵果</a></dd>
                <dd><a href='/0/15/13796.html' >第八百三十四章 玄元丹</a></dd>
                    
                      
                <dd><a href='/0/15/13797.html' >第八百三十五章 夜袭</a></dd>
                <dd><a href='/0/15/13798.html' >第八百三十六章 仙符师</a></dd>
                <dd><a href='/0/15/13799.html' >第八百三十七章 报酬</a></dd>
                <dd><a href='/0/15/13800.html' >第八百三十八章 冲击九元涅盘境</a></dd>
                    
                      
                <dd><a href='/0/15/13801.html' >第八百三十九章 玄灵山</a></dd>
                <dd><a href='/0/15/13802.html' >第八百四十章 震慑</a></dd>
                <dd><a href='/0/15/13803.html' >第八百四十一章 各方云集</a></dd>
                <dd><a href='/0/15/13804.html' >第八百四十二章</a></dd>
                    
                      
                <dd><a href='/0/15/13805.html' >第八百四十三章 青龙之力</a></dd>
                <dd><a href='/0/15/13806.html' >第八百四十四章 三头魔蛟</a></dd>
                <dd><a href='/0/15/13807.html' >第八百四十五章 混战</a></dd>
                <dd><a href='/0/15/13808.html' >第八百四十六章 各施手段</a></dd>
                    
                      
                <dd><a href='/0/15/13809.html' >第八百四十七章 到手</a></dd>
                <dd><a href='/0/15/13810.html' >第八百四十八章 局势</a></dd>
                <dd><a href='/0/15/13811.html' >第八百四十九章 吸进鼎炉</a></dd>
                <dd><a href='/0/15/13812.html' >第八百五十章 峥嵘</a></dd>
                    
                      
                <dd><a href='/0/15/13813.html' >第八百五十一章 抹杀</a></dd>
                <dd><a href='/0/15/13814.html' >第八百五十二章 地心生灵浆</a></dd>
                <dd><a href='/0/15/13815.html' >第八百五十三章 进湖</a></dd>
                <dd><a href='/0/15/13816.html' >第八百五十四章 岩浆之后</a></dd>
                    
                      
                <dd><a href='/0/15/13817.html' >第八百五十五章 虎口夺食</a></dd>
                <dd><a href='/0/15/13818.html' >第八百五十六章 神秘的空间</a></dd>
                <dd><a href='/0/15/13819.html' >第八百五十七章 令牌</a></dd>
                <dd><a href='/0/15/13820.html' >第八百五十八章 外援</a></dd>
                    
                      
                <dd><a href='/0/15/13821.html' >第八百五十九章 生玄境</a></dd>
                <dd><a href='/0/15/13822.html' >第八百六十章 洪荒塔</a></dd>
                <dd><a href='/0/15/13823.html' >第三百六十一章 动身</a></dd>
                <dd><a href='/0/15/13824.html' >第三百六十二章 武会岛</a></dd>
                    
                      
                <dd><a href='/0/15/13825.html' >第八百六十三章 争端</a></dd>
                <dd><a href='/0/15/13826.html' >第八百六十四章 承让</a></dd>
                <dd><a href='/0/15/13827.html' >第八百六十五章 油盐不进</a></dd>
                <dd><a href='/0/15/13828.html' >第八百六十六章 合作</a></dd>
                    
                      
                <dd><a href='/0/15/13829.html' >第八百六十七章 冤家路窄</a></dd>
                <dd><a href='/0/15/13830.html' >第八百六十八章 武会</a></dd>
                <dd><a href='/0/15/13831.html' >第八百六十九章 分配</a></dd>
                <dd><a href='/0/15/13832.html' >第八百七十章 激斗苏岩</a></dd>
                    
                      
                <dd><a href='/0/15/13833.html' >第八百七十一章 一掌</a></dd>
                <dd><a href='/0/15/13834.html' >第八百七十二章 获胜</a></dd>
                <dd><a href='/0/15/13835.html' >第八百七十三章 修罗模式</a></dd>
                <dd><a href='/0/15/13836.html' >第八百七十四章 挑战</a></dd>
                    
                      
                <dd><a href='/0/15/13837.html' >第八百七十五章 武帝怒</a></dd>
                <dd><a href='/0/15/13838.html' >第八百七十六章 强势</a></dd>
                <dd><a href='/0/15/13839.html' >第八百七十七章 初步接触</a></dd>
                <dd><a href='/0/15/13840.html' >第八百七十八章 海</a></dd>
                    
                      
                <dd><a href='/0/15/13841.html' >第八百七十九章 此路，不通</a></dd>
                <dd><a href='/0/15/13842.html' >第八百八十章 青龙武装</a></dd>
                <dd><a href='/0/15/13843.html' >第八百八十一章 青龙战修罗</a></dd>
                <dd><a href='/0/15/13844.html' >第八百八十二章 修罗地煞狱</a></dd>
                    
                      
                <dd><a href='/0/15/13845.html' >第八百八十三章 底牌频出</a></dd>
                <dd><a href='/0/15/13846.html' >第八百八十四章 胜</a></dd>
                <dd><a href='/0/15/13847.html' >第八百八十五章 落幕</a></dd>
                <dd><a href='/0/15/13848.html' >第八百八十六章 进入洪荒塔</a></dd>
                    
                      
                <dd><a href='/0/15/13849.html' >第八百八十七章 如海般的洪荒之气</a></dd>
                <dd><a href='/0/15/13850.html' >第八百八十八章 获益匪浅</a></dd>
                <dd><a href='/0/15/13851.html' >第八百八十九章 紫金之皮</a></dd>
                <dd><a href='/0/15/13852.html' >第八百九十章 祖石之灵</a></dd>
                    
                      
                <dd><a href='/0/15/13853.html' >第八百九十一章 麻烦上门</a></dd>
                <dd><a href='/0/15/13854.html' >第八百九十二章 邪骨老人</a></dd>
                <dd><a href='/0/15/13855.html' >第八百九十三章 设计</a></dd>
                <dd><a href='/0/15/13856.html' >第八百九十四章 离开</a></dd>
                    
                      
                <dd><a href='/0/15/13857.html' >第八百九十五章 斗邪骨</a></dd>
                <dd><a href='/0/15/13858.html' >第八百九十六章 炎神古牌之力</a></dd>
                <dd><a href='/0/15/13859.html' >第八百九十七章 重伤</a></dd>
                <dd><a href='/0/15/13860.html' >第八百九十八章 血魔鲨族</a></dd>
                    
                      
                <dd><a href='/0/15/13861.html' >第八百九十九章 青衣女童</a></dd>
                <dd><a href='/0/15/13862.html' >第九百章 慕灵珊</a></dd>
                <dd><a href='/0/15/13863.html' >第九百零一章 救人</a></dd>
                <dd><a href='/0/15/13864.html' >第九百零二章 交手</a></dd>
                    
                      
                <dd><a href='/0/15/13865.html' >第九百零三章 先下手</a></dd>
                <dd><a href='/0/15/13866.html' >第九百零四章 屠戮</a></dd>
                <dd><a href='/0/15/13867.html' >第九百零五章 海上激战</a></dd>
                <dd><a href='/0/15/13868.html' >第九百零六章 魔鲨之牙</a></dd>
                    
                      
                <dd><a href='/0/15/13869.html' >第九百零七章 斩草除根</a></dd>
                <dd><a href='/0/15/13870.html' >第九百零八章 天商城</a></dd>
                <dd><a href='/0/15/13871.html' >第九百零九章 唐冬灵</a></dd>
                <dd><a href='/0/15/13872.html' >第九百一十章 炼制焚天门</a></dd>
                    
                      
                <dd><a href='/0/15/13873.html' >第九百一十一章 完整的焚天鼎</a></dd>
                <dd><a href='/0/15/13874.html' >第九百一十二章 天商拍卖会</a></dd>
                <dd><a href='/0/15/13875.html' >第九百一十三章 对立</a></dd>
                <dd><a href='/0/15/13876.html' >第九百一十四章 吞噬天尸</a></dd>
                    
                      
                <dd><a href='/0/15/13877.html' >第九百一十五章 竞价</a></dd>
                <dd><a href='/0/15/13878.html' >第九百一十六章 压箱底之物？</a></dd>
                <dd><a href='/0/15/13879.html' >第九百一十七章 雷霆祖符的线索</a></dd>
                <dd><a href='/0/15/13880.html' >第九百一十八章 争夺银塔</a></dd>
                    
                      
                <dd><a href='/0/15/13881.html' >第九百一十九章 操控天尸</a></dd>
                <dd><a href='/0/15/13882.html' >第九百二十章 好戏</a></dd>
                <dd><a href='/0/15/13883.html' >第九百二十一章 变故</a></dd>
                <dd><a href='/0/15/13884.html' >第九百二十二章 动手</a></dd>
                    
                      
                <dd><a href='/0/15/13885.html' >第九百二十三章 焚天门之威</a></dd>
                <dd><a href='/0/15/13886.html' >第九百二十四章 夺塔而走</a></dd>
                <dd><a href='/0/15/13887.html' >第九百二十五章 追兵</a></dd>
                <dd><a href='/0/15/13888.html' >第九百二十六章 天雷海域</a></dd>
                    
                      
                <dd><a href='/0/15/13889.html' >第九百二十七章 途遇</a></dd>
                <dd><a href='/0/15/13890.html' >第九百二十八章 无轩</a></dd>
                <dd><a href='/0/15/13891.html' >第九百二十九章 两大转轮境</a></dd>
                <dd><a href='/0/15/13892.html' >第九百三十章 薄礼</a></dd>
                    
                      
                <dd><a href='/0/15/13893.html' >第九百三十一章 夜谈</a></dd>
                <dd><a href='/0/15/13894.html' >第九百三十二章 抵达</a></dd>
                <dd><a href='/0/15/13895.html' >第九百三十三章 算计</a></dd>
                <dd><a href='/0/15/13896.html' >第九百三十四章 杀鸡儆猴</a></dd>
                    
                      
                <dd><a href='/0/15/13897.html' >第九百三十五章 水深</a></dd>
                <dd><a href='/0/15/13898.html' >第九百三十六章 进入天雷海域</a></dd>
                <dd><a href='/0/15/13899.html' >第九百三十七章 凶险的天雷海域</a></dd>
                <dd><a href='/0/15/13900.html' >第九百三十八章 洞府开启</a></dd>
                    
                      
                <dd><a href='/0/15/13901.html' >第九百三十九章 雷光战场</a></dd>
                <dd><a href='/0/15/13902.html' >第九百四十章 洞府之内</a></dd>
                <dd><a href='/0/15/13903.html' >第九百四十一章 追杀</a></dd>
                <dd><a href='/0/15/13904.html' >第九百四十二章 抹杀</a></dd>
                    
                      
                <dd><a href='/0/15/13905.html' >第九百四十三章 神秘红袍人</a></dd>
                <dd><a href='/0/15/13906.html' >第九百四十四章 雷霆之心</a></dd>
                <dd><a href='/0/15/13907.html' >第九百四十五章 交手</a></dd>
                <dd><a href='/0/15/13908.html' >第九百四十六章 热闹</a></dd>
                    
                      
                <dd><a href='/0/15/13909.html' >第九百四十七章 雷岩沟壑</a></dd>
                <dd><a href='/0/15/13910.html' >第九百四十八章 收取</a></dd>
                <dd><a href='/0/15/13911.html' >第九百四十九章 湖底混战</a></dd>
                <dd><a href='/0/15/13912.html' >第九百五十章 拖下水</a></dd>
                    
                      
                <dd><a href='/0/15/13913.html' >第九百五十一章 激战庞昊</a></dd>
                <dd><a href='/0/15/13914.html' >第九百五十二章 凶狠</a></dd>
                <dd><a href='/0/15/13915.html' >第九百五十三章 异魔？</a></dd>
                <dd><a href='/0/15/13916.html' >第九百五十四章 退避</a></dd>
                    
                      
                <dd><a href='/0/15/13917.html' >第九百五十五章 帮</a></dd>
                <dd><a href='/0/15/13918.html' >第九百五十六章 三大神物</a></dd>
                <dd><a href='/0/15/13919.html' >第九百五十七章 抹除魔纹</a></dd>
                <dd><a href='/0/15/13920.html' >第九百五十八章 左费</a></dd>
                    
                      
                <dd><a href='/0/15/13921.html' >第九百五十九章 吸收</a></dd>
                <dd><a href='/0/15/13922.html' >第九百六十章 雷殿</a></dd>
                <dd><a href='/0/15/13923.html' >第九百六十一章 强者汇聚</a></dd>
                <dd><a href='/0/15/13924.html' >第九百六十二章 九幽镇灵阵</a></dd>
                    
                      
                <dd><a href='/0/15/13925.html' >第九百六十三章 引尸</a></dd>
                <dd><a href='/0/15/13926.html' >第九百六十四章（上） 断手</a></dd>
                <dd><a href='/0/15/13927.html' >第九百六十四章（下） 雷帝权杖</a></dd>
                <dd><a href='/0/15/13928.html' >第九百六十五章 争夺</a></dd>
                    
                      
                <dd><a href='/0/15/13929.html' >第九百六十六章 降服</a></dd>
                <dd><a href='/0/15/13930.html' >第九百六十七章 上一届的元门三小王</a></dd>
                <dd><a href='/0/15/13931.html' >第九百六十八章 摩罗</a></dd>
                <dd><a href='/0/15/13932.html' >第九百六十九章 驱逐</a></dd>
                    
                      
                <dd><a href='/0/15/13933.html' >第九百七十章 雷界</a></dd>
                <dd><a href='/0/15/13934.html' >第九百七十一章 联手诛魔</a></dd>
                <dd><a href='/0/15/13935.html' >第九百七十二章 三大祖符</a></dd>
                <dd><a href='/0/15/13936.html' >第九百七十三章 抹杀异魔王</a></dd>
                    
                      
                <dd><a href='/0/15/13937.html' >第九百七十四章 争执</a></dd>
                <dd><a href='/0/15/13938.html' >第九百七十五章 倾尽手段</a></dd>
                <dd><a href='/0/15/13939.html' >第九百七十六章 血拼到底</a></dd>
                <dd><a href='/0/15/13940.html' >第九百七十七章 我赢了</a></dd>
                    
                      
                <dd><a href='/0/15/13941.html' >第九百七十八章 诱饵</a></dd>
                <dd><a href='/0/15/13942.html' >第九百七十九章 我自巍然</a></dd>
                <dd><a href='/0/15/13943.html' >第九百八十章 十万雷霆铸雷身</a></dd>
                <dd><a href='/0/15/13944.html' >第九百八十一章 炼化雷霆祖符</a></dd>
                    
                      
                <dd><a href='/0/15/13945.html' >第九百八十二章 实力大进</a></dd>
                <dd><a href='/0/15/13946.html' >第九百八十三章（上） 蹲守</a></dd>
                <dd><a href='/0/15/13947.html' >第九百八十三章（下） 救人</a></dd>
                <dd><a href='/0/15/13948.html' >第九百八十四章 诛杀</a></dd>
                    
                      
                <dd><a href='/0/15/13949.html' >第九百八十五章 狠手段</a></dd>
                <dd><a href='/0/15/13950.html' >第九百八十六章 魔迹</a></dd>
                <dd><a href='/0/15/13951.html' >第九百八十七章 除魔</a></dd>
                <dd><a href='/0/15/13952.html' >第九百八十八章 两大祖符</a></dd>
                    
                      
                <dd><a href='/0/15/13953.html' >第九百八十九章 诛杀</a></dd>
                <dd><a href='/0/15/13954.html' >第九百九十章 解决</a></dd>
                <dd><a href='/0/15/13955.html' >第九百九十一章 震动</a></dd>
                <dd><a href='/0/15/13956.html' >第九百九十二章 新秀榜</a></dd>
                    
                      
                <dd><a href='/0/15/13957.html' >第九百九十三章 火炎城</a></dd>
                <dd><a href='/0/15/13958.html' >第九百九十四章 熟人</a></dd>
                <dd><a href='/0/15/13959.html' >第九百九十五章 冲突</a></dd>
                <dd><a href='/0/15/13960.html' >第九百九十六章 交手</a></dd>
                    
                      
                <dd><a href='/0/15/13961.html' >第九百九十七章 唐心莲</a></dd>
                <dd><a href='/0/15/13962.html' >第九百九十八章 水深</a></dd>
                <dd><a href='/0/15/13963.html' >第九百九十九章 报我的名</a></dd>
                <dd><a href='/0/15/13964.html' >第一零零零章 大赛前的平静</a></dd>
                    
                      
                <dd><a href='/0/15/13965.html' >第一千零一章 开启</a></dd>
                <dd><a href='/0/15/13966.html' >第一千零二章 血之斩头卫</a></dd>
                <dd><a href='/0/15/13967.html' >第一千零三章 一路向前</a></dd>
                <dd><a href='/0/15/13968.html' >第一千零四章 遇上</a></dd>
                    
                      
                <dd><a href='/0/15/13969.html' >第一千零五章 初次交手</a></dd>
                <dd><a href='/0/15/13970.html' >第一千零六章 无量山</a></dd>
                <dd><a href='/0/15/13971.html' >第一千零七章 登山</a></dd>
                <dd><a href='/0/15/13972.html' >第一千零八章 鲨力</a></dd>
                    
                      
                <dd><a href='/0/15/13973.html' >第一千零九章 登顶</a></dd>
                <dd><a href='/0/15/13974.html' >第一千一十章 顶上之争</a></dd>
                <dd><a href='/0/15/13975.html' >第一千一十一章 巅峰之战</a></dd>
                <dd><a href='/0/15/13976.html' >第一千一十二章 隐忍待发</a></dd>
                    
                      
                <dd><a href='/0/15/13977.html' >第一千一十三章 青锋出鞘</a></dd>
                <dd><a href='/0/15/13978.html' >第一千一十四章 斗两魔</a></dd>
                <dd><a href='/0/15/13979.html' >第一千一十五章 手段尽出</a></dd>
                <dd><a href='/0/15/13980.html' >第一千一十六章 三重攻势</a></dd>
                    
                      
                <dd><a href='/0/15/13981.html' >第一千一十七章 断臂</a></dd>
                <dd><a href='/0/15/13982.html' >第一千一十八章 各施手段</a></dd>
                <dd><a href='/0/15/13983.html' >第一千一十九章 三百道</a></dd>
                <dd><a href='/0/15/13984.html' >第一千二十章 破镜</a></dd>
                    
                      
                <dd><a href='/0/15/13985.html' >第一千二十一章 柔软</a></dd>
                <dd><a href='/0/15/13986.html' >第一千二十二章 魔现</a></dd>
                <dd><a href='/0/15/13987.html' >第一千二十三章 天冥王</a></dd>
                <dd><a href='/0/15/13988.html' >第一千二十四章 青雉再现</a></dd>
                    
                      
                <dd><a href='/0/15/13989.html' >第一千二十五章 炎神殿的统帅</a></dd>
                <dd><a href='/0/15/13990.html' >第一千二十六章 恐怖的女孩</a></dd>
                <dd><a href='/0/15/13991.html' >第一千二十七章</a></dd>
                <dd><a href='/0/15/13992.html' >第一千二十八章 冲击</a></dd>
                    
                      
                <dd><a href='/0/15/13993.html' >第一千二十九章 镇压</a></dd>
                <dd><a href='/0/15/13994.html' >第一千三十章 灭王天盘</a></dd>
                <dd><a href='/0/15/13995.html' >第一千三十一章 生死祖符</a></dd>
                <dd><a href='/0/15/13996.html' >第一千三十二章 灭王天盘</a></dd>
                    
                      
                <dd><a href='/0/15/13997.html' >第一千三十三章 魔狱</a></dd>
                <dd><a href='/0/15/13998.html' >第一千三十四章 踪迹</a></dd>
                <dd><a href='/0/15/13999.html' >第一千三十五章 死炎灵池</a></dd>
                <dd><a href='/0/15/14000.html' >第一千三十六章 死气冲刷</a></dd>
                    
                      
                <dd><a href='/0/15/14001.html' >第一千三十七章 最后一道</a></dd>
                <dd><a href='/0/15/14002.html' >第一千三十八章 离开</a></dd>
                <dd><a href='/0/15/14003.html' >第一千三十九章 暗云涌动</a></dd>
                <dd><a href='/0/15/14004.html' >第一千四十章 兽战域</a></dd>
                    
                      
                <dd><a href='/0/15/14005.html' >第一千四十一章 抢我的烤肉</a></dd>
                <dd><a href='/0/15/14006.html' >第一千四十二章 带走</a></dd>
                <dd><a href='/0/15/14007.html' >第一千四十三章 垫脚石</a></dd>
                <dd><a href='/0/15/14008.html' >第一千四十四章 曹赢</a></dd>
                    
                      
                <dd><a href='/0/15/14009.html' >第一千四十五章 露峥嵘</a></dd>
                <dd><a href='/0/15/14010.html' >第一千四十六章 达到目的</a></dd>
                <dd><a href='/0/15/14011.html' >第一千四十七章 抵达</a></dd>
                <dd><a href='/0/15/14012.html' >第一千四十八章 九尾寨</a></dd>
                    
                      
                <dd><a href='/0/15/14013.html' >第一千四十九章 秦刚与蒙山</a></dd>
                <dd><a href='/0/15/14014.html' >第一千五十章 兄弟相聚</a></dd>
                <dd><a href='/0/15/14015.html' >第一千五十一章 炎将</a></dd>
                <dd><a href='/0/15/14016.html' >第一千五十二章 小炎的经历</a></dd>
                    
                      
                <dd><a href='/0/15/14017.html' >第一千五十三章 相谈</a></dd>
                <dd><a href='/0/15/14018.html' >第一千五十四章 秘辛</a></dd>
                <dd><a href='/0/15/14019.html' >第一千五十五章 祖魂殿</a></dd>
                <dd><a href='/0/15/14020.html' >第一千五十六章 九尾灵狐</a></dd>
                    
                      
                <dd><a href='/0/15/14021.html' >第一千五十七章 传承</a></dd>
                <dd><a href='/0/15/14022.html' >第一千五十八章 吞噬神殿</a></dd>
                <dd><a href='/0/15/14023.html' >第一千五十九章 希望</a></dd>
                <dd><a href='/0/15/14024.html' >第一千六十章 还有怀疑吗</a></dd>
                    
                      
                <dd><a href='/0/15/14025.html' >第一千六十一章慑服</a></dd>
                <dd><a href='/0/15/14026.html' >第一千六十二章 雷渊山脉</a></dd>
                <dd><a href='/0/15/14027.html' >第一千六十三章 妖帅徐钟</a></dd>
                <dd><a href='/0/15/14028.html' >第一千六十四章 各自的准备</a></dd>
                    
                      
                <dd><a href='/0/15/14029.html' >第一千六十五章 斗妖帅</a></dd>
                <dd><a href='/0/15/14030.html' >第一千六十六章 雷渊山之战</a></dd>
                <dd><a href='/0/15/14031.html' >第一千六十七章 发狂</a></dd>
                <dd><a href='/0/15/14032.html' >第一千六十八章 抹杀</a></dd>
                    
                      
                <dd><a href='/0/15/14033.html' >第一千六十九章 易主</a></dd>
                <dd><a href='/0/15/14034.html' >第一千七十章 精血传承</a></dd>
                <dd><a href='/0/15/14035.html' >第一千七十一章 神物宝库</a></dd>
                <dd><a href='/0/15/14036.html' >第一千七十二章 无间神狱盘</a></dd>
                    
                      
                <dd><a href='/0/15/14037.html' >第一千七十三章 锤锻精神</a></dd>
                <dd><a href='/0/15/14038.html' >第一千七十四章 血龙殿</a></dd>
                <dd><a href='/0/15/14039.html' >第一千七十五章 两大统领</a></dd>
                <dd><a href='/0/15/14040.html' >第一千七十六章 天龙妖帅</a></dd>
                    
                      
                <dd><a href='/0/15/14041.html' >第一千七十七章 风波暂息</a></dd>
                <dd><a href='/0/15/14042.html' >第一千七十八章 暴风雨前的宁静</a></dd>
                <dd><a href='/0/15/14043.html' >第一千七十九章 神物山脉</a></dd>
                <dd><a href='/0/15/14044.html' >第一千八十章 投鼠忌器</a></dd>
                    
                      
                <dd><a href='/0/15/14045.html' >第一千八十一章 宝库出现</a></dd>
                <dd><a href='/0/15/14046.html' >第一千八十二章 取宝</a></dd>
                <dd><a href='/0/15/14047.html' >第一千八十三章 各施手段</a></dd>
                <dd><a href='/0/15/14048.html' >第一千八十四章 玄天殿内</a></dd>
                    
                      
                <dd><a href='/0/15/14049.html' >第一千八十五章 万魔蚀阵</a></dd>
                <dd><a href='/0/15/14050.html' >第一千八十六章 联手</a></dd>
                <dd><a href='/0/15/14051.html' >第一千八十七章 背水一战</a></dd>
                <dd><a href='/0/15/14052.html' >第一千八十八章 战转轮</a></dd>
                    
                      
                <dd><a href='/0/15/14053.html' >第一千八十九章 玄天殿</a></dd>
                <dd><a href='/0/15/14054.html' >第一千九十章 再说一次</a></dd>
                <dd><a href='/0/15/14055.html' >第一千九十一章 三兄弟，终聚首</a></dd>
                <dd><a href='/0/15/14056.html' >第一千九十二章 霸道的天妖貂</a></dd>
                    
                      
                <dd><a href='/0/15/14057.html' >第一千九十三章 小貂斗天龙</a></dd>
                <dd><a href='/0/15/14058.html' >第一千九十四章 龙族</a></dd>
                <dd><a href='/0/15/14059.html' >第一千九十五章 对恃</a></dd>
                <dd><a href='/0/15/14060.html' >第一千九十六章 龙族的问题</a></dd>
                    
                      
                <dd><a href='/0/15/14061.html' >第一千九十七章 前往龙族</a></dd>
                <dd><a href='/0/15/14062.html' >第一千九十八章 龙族</a></dd>
                <dd><a href='/0/15/14063.html' >第一千九十九章 龙族的麻烦</a></dd>
                <dd><a href='/0/15/14064.html' >第一千一百章 棘手</a></dd>
                    
                      
                <dd><a href='/0/15/14065.html' >第一千一百零一章 镇魔狱</a></dd>
                <dd><a href='/0/15/14066.html' >第一千一百零二章 黑暗之主</a></dd>
                <dd><a href='/0/15/14067.html' >第一千一百零三章 解决魔海</a></dd>
                <dd><a href='/0/15/14068.html' >第一千一百零四章 名额</a></dd>
                    
                      
                <dd><a href='/0/15/14069.html' >第一千一百零五章 严山</a></dd>
                <dd><a href='/0/15/14070.html' >第一千一百零六章 龙骨</a></dd>
                <dd><a href='/0/15/14071.html' >第一千一百零七章 化龙潭开启</a></dd>
                <dd><a href='/0/15/14072.html' >第一千一百零八章 化龙骨</a></dd>
                    
                      
                <dd><a href='/0/15/14073.html' >第一千一百零九章 埋骨之地</a></dd>
                <dd><a href='/0/15/14074.html' >第一千一百一十章 远古龙骨</a></dd>
                <dd><a href='/0/15/14075.html' >第一千一百一十一章 六指圣龙帝</a></dd>
                <dd><a href='/0/15/14076.html' >第一千一百一十二章 帮手</a></dd>
                    
                      
                <dd><a href='/0/15/14077.html' >第一千一百一十三章 巅峰交手</a></dd>
                <dd><a href='/0/15/14078.html' >第一千一百一十四章 洪荒龙骨</a></dd>
                <dd><a href='/0/15/14079.html' >第一千一百一十五章 刑罚长老</a></dd>
                <dd><a href='/0/15/14080.html' >第一千一百一十六章 离开</a></dd>
                    
                      
                <dd><a href='/0/15/14081.html' >第一千一百一十七章 邙山</a></dd>
                <dd><a href='/0/15/14082.html' >第一千一百一十八章 联手</a></dd>
                <dd><a href='/0/15/14083.html' >第一千一百一十九章 四象宫</a></dd>
                <dd><a href='/0/15/14084.html' >第一千一百二十章 妖兽古原</a></dd>
                    
                      
                <dd><a href='/0/15/14085.html' >第一千一百二十一章 天擂台</a></dd>
                <dd><a href='/0/15/14086.html' >第一千一百二十二章 连败</a></dd>
                <dd><a href='/0/15/14087.html' >第一千一百二十三章 神锤憾玄武</a></dd>
                <dd><a href='/0/15/14088.html' >第一千一百二十四章 最后一场</a></dd>
                    
                      
                <dd><a href='/0/15/14089.html' >第一千一百二十五章 激战罗通</a></dd>
                <dd><a href='/0/15/14090.html' >第一千一百二十六章 九凤化生光</a></dd>
                <dd><a href='/0/15/14091.html' >第一千一百二十七章 惨烈</a></dd>
                <dd><a href='/0/15/14092.html' >第一千一百二十八章 结束</a></dd>
                    
                      
                <dd><a href='/0/15/14093.html' >第一千一百二十九章 大整顿</a></dd>
                <dd><a href='/0/15/14094.html' >第一千一百三十章 小貂的麻烦</a></dd>
                <dd><a href='/0/15/14095.html' >第一千一百三十一章 魔狱再现</a></dd>
                <dd><a href='/0/15/14096.html' >第一千一百三十二章 天洞</a></dd>
                    
                      
                <dd><a href='/0/15/14097.html' >第一千一百三十三章 永恒幻魔花</a></dd>
                <dd><a href='/0/15/14098.html' >第一千一百三十四章 苏醒</a></dd>
                <dd><a href='/0/15/14099.html' >第一千一百三十五章 对决</a></dd>
                <dd><a href='/0/15/14100.html' >第一千一百三十六章 孰强孰弱</a></dd>
                    
                      
                <dd><a href='/0/15/14101.html' >第一千一百三十七章 昊九幽的手段</a></dd>
                <dd><a href='/0/15/14102.html' >第一千一百三十八章 抓魔</a></dd>
                <dd><a href='/0/15/14103.html' >第一千一百三十九章 异魔王再现</a></dd>
                <dd><a href='/0/15/14104.html' >第一千一百四十章 大礼</a></dd>
                    
                      
                <dd><a href='/0/15/14105.html' >第一千一百四十一章 出手</a></dd>
                <dd><a href='/0/15/14106.html' >第一千一百四十二章 荒芜再现</a></dd>
                <dd><a href='/0/15/14107.html' >第一千一百四十三章 永恒花魔身</a></dd>
                <dd><a href='/0/15/14108.html' >第一千一百四十四章 祖符之手</a></dd>
                    
                      
                <dd><a href='/0/15/14109.html' >第一千一百四十五章 解局</a></dd>
                <dd><a href='/0/15/14110.html' >第一千一百四十六章 冲击符宗</a></dd>
                <dd><a href='/0/15/14111.html' >第一千一百四十七章 炼狱</a></dd>
                <dd><a href='/0/15/14112.html' >第一千一百四十八章 化茧</a></dd>
                    
                      
                <dd><a href='/0/15/14113.html' >第一千一百四十九章 守关者</a></dd>
                <dd><a href='/0/15/14114.html' >第一千一百五十章 晋入符宗</a></dd>
                <dd><a href='/0/15/14115.html' >第一千一百五十一章 出关</a></dd>
                <dd><a href='/0/15/14116.html' >第一千一百五十二章 投诚</a></dd>
                    
                      
                <dd><a href='/0/15/14117.html' >第一千一百五十三章 打压</a></dd>
                <dd><a href='/0/15/14118.html' >第一千一百五十四章 一剑败双雄</a></dd>
                <dd><a href='/0/15/14119.html' >第一千一百五十五章 震慑</a></dd>
                <dd><a href='/0/15/14120.html' >第一千一百五十六章 妖域震动</a></dd>
                    
                      
                <dd><a href='/0/15/14121.html' >第一千一百五十七章 群强云集</a></dd>
                <dd><a href='/0/15/14122.html' >第一千一百五十八章 柳青</a></dd>
                <dd><a href='/0/15/14123.html' >第一千一百五十九章 鲲灵</a></dd>
                <dd><a href='/0/15/14124.html' >第一千一百六十章 进荒原</a></dd>
                    
                      
                <dd><a href='/0/15/14125.html' >第一千一百六十一章 抵达</a></dd>
                <dd><a href='/0/15/14126.html' >第一千一百六十二章 黑暗圣虎</a></dd>
                <dd><a href='/0/15/14127.html' >第一千一百六十三章 三大虎族</a></dd>
                <dd><a href='/0/15/14128.html' >第一千一百六十四章 以一敌二</a></dd>
                    
                      
                <dd><a href='/0/15/14129.html' >第一千一百六十五章 孤峰上的大殿</a></dd>
                <dd><a href='/0/15/14130.html' >第一千一百六十六章 神秘黑影</a></dd>
                <dd><a href='/0/15/14131.html' >第一千一百六十七章 闯关</a></dd>
                <dd><a href='/0/15/14132.html' >第一千一百六十八章 九峰</a></dd>
                    
                      
                <dd><a href='/0/15/14133.html' >第一千一百六十九章 黑暗之中</a></dd>
                <dd><a href='/0/15/14134.html' >第一千一百七十章 两股吞噬之力</a></dd>
                <dd><a href='/0/15/14135.html' >第一千一百七十一章 吞噬之主</a></dd>
                <dd><a href='/0/15/14136.html' >第一千一百七十二章 传承之秘</a></dd>
                    
                      
                <dd><a href='/0/15/14137.html' >第一千一百七十三章 借身斩魔</a></dd>
                <dd><a href='/0/15/14138.html' >第一千一百七十四章 恐怖的吞噬之主</a></dd>
                <dd><a href='/0/15/14139.html' >第一千一百七十五章 福泽</a></dd>
                <dd><a href='/0/15/14140.html' >第一千一百七十六章 三重轮回劫</a></dd>
                    
                      
                <dd><a href='/0/15/14141.html' >第一千一百七十七章 轮回之海</a></dd>
                <dd><a href='/0/15/14142.html' >第一千一百七十八章 战争</a></dd>
                <dd><a href='/0/15/14143.html' >第一千一百七十九章 杀回去</a></dd>
                <dd><a href='/0/15/14144.html' >第一千一百八十章 调遣人马</a></dd>
                    
                      
                <dd><a href='/0/15/14145.html' >第一千一百八十一章 重回东玄域</a></dd>
                <dd><a href='/0/15/14146.html' >第一千一百八十二章 东玄域的局势</a></dd>
                <dd><a href='/0/15/14147.html' >第一千一百八十三章 归来</a></dd>
                <dd><a href='/0/15/14148.html' >第一千一百八十四章 打</a></dd>
                    
                      
                <dd><a href='/0/15/14149.html' >第一千一百八十五章 传奇</a></dd>
                <dd><a href='/0/15/14150.html' >第一千一百八十六章 再见应欢欢</a></dd>
                <dd><a href='/0/15/14151.html' >第一千一百八十七章 壮我道宗！</a></dd>
                <dd><a href='/0/15/14152.html' >第一千一百八十八章 归宗</a></dd>
                    
                      
                <dd><a href='/0/15/14153.html' >第一千一百八十九章 表现</a></dd>
                <dd><a href='/0/15/14154.html' >第一千一百九十章 进碑</a></dd>
                <dd><a href='/0/15/14155.html' >第一千一百九十一章 联手斩魔</a></dd>
                <dd><a href='/0/15/14156.html' >第一千一百九十二章 撞车</a></dd>
                    
                      
                <dd><a href='/0/15/14157.html' >第一千一百九十三章 判断失误</a></dd>
                <dd><a href='/0/15/14158.html' >第一千一百九十四章 太清宫之难</a></dd>
                <dd><a href='/0/15/14159.html' >第一千一百九十五章 太上宫</a></dd>
                <dd><a href='/0/15/14160.html' >第一千一百九十六章 孤寂芳影，一人迎敌</a></dd>
                    
                      
                <dd><a href='/0/15/14161.html' >第一千一百九十七章 没人能伤你</a></dd>
                <dd><a href='/0/15/14162.html' >第一千一百九十八章 小心点</a></dd>
                <dd><a href='/0/15/14163.html' >第一千一百九十九章 讨债开始</a></dd>
                <dd><a href='/0/15/14164.html' >第一千两百章 显威</a></dd>
                    
                      
                <dd><a href='/0/15/14165.html' >第一千两百零一章 第八道祖符</a></dd>
                <dd><a href='/0/15/14166.html' >第一千两百零二章 空间祖符</a></dd>
                <dd><a href='/0/15/14167.html' >第一千两百零三章 诛元盟</a></dd>
                <dd><a href='/0/15/14168.html' >第一千两百零四章 汇聚，决战来临</a></dd>
                    
                      
                <dd><a href='/0/15/14169.html' >第一千两百零五章 元门之外</a></dd>
                <dd><a href='/0/15/14170.html' >第一千两百零六章 周通</a></dd>
                <dd><a href='/0/15/14171.html' >第一千两百零七章 林动vs周通</a></dd>
                <dd><a href='/0/15/14172.html' >第一千两百零八章 魔皇锁</a></dd>
                    
                      
                <dd><a href='/0/15/14173.html' >第一千两百零九章 解救</a></dd>
                <dd><a href='/0/15/14174.html' >第一千两百一十章 盛大魔宴</a></dd>
                <dd><a href='/0/15/14175.html' >第一千两百一十一章 龙，虎，貂</a></dd>
                <dd><a href='/0/15/14176.html' >第一千两百一十二章 斗魔</a></dd>
                    
                      
                <dd><a href='/0/15/14177.html' >第一千两百一十三章 雪耻之战</a></dd>
                <dd><a href='/0/15/14178.html' >第一千两百一十四章 祖符之眼</a></dd>
                <dd><a href='/0/15/14179.html' >第一千两百一十五章 斩杀三巨头</a></dd>
                <dd><a href='/0/15/14180.html' >第一千两百一十六章 两女联手</a></dd>
                    
                      
                <dd><a href='/0/15/14181.html' >第一千两百一十七章 四王殿</a></dd>
                <dd><a href='/0/15/14182.html' >第一千两百一十八章 炎主</a></dd>
                <dd><a href='/0/15/14183.html' >第一千两百一十九章 树静风止</a></dd>
                <dd><a href='/0/15/14184.html' >第一千两百二十章 大符宗</a></dd>
                    
                      
                <dd><a href='/0/15/14185.html' >第一千两百二十一章 怒斗炎主</a></dd>
                <dd><a href='/0/15/14186.html' >第一千两百二十二章 大雪初晴</a></dd>
                <dd><a href='/0/15/14187.html' >第一千两百二十三章 相谈</a></dd>
                <dd><a href='/0/15/14188.html' >第一千两百二十四章 太上感应诀</a></dd>
                    
                      
                <dd><a href='/0/15/14189.html' >第一千两百二十五章 山顶之谈</a></dd>
                <dd><a href='/0/15/14190.html' >第一千两百二十六章 千万大山</a></dd>
                <dd><a href='/0/15/14191.html' >第一千两百二十七章 再遇辰傀</a></dd>
                <dd><a href='/0/15/14192.html' >第一千两百二十八章 青檀之事</a></dd>
                    
                      
                <dd><a href='/0/15/14193.html' >第一千两百二十九章 黑暗之城</a></dd>
                <dd><a href='/0/15/14194.html' >第一千两百三十章 逼宫</a></dd>
                <dd><a href='/0/15/14195.html' >第一千两百三十一章 相见</a></dd>
                <dd><a href='/0/15/14196.html' >第一千两百三十二章 显威</a></dd>
                    
                      
                <dd><a href='/0/15/14197.html' >第一千两百三十三章 镰灵</a></dd>
                <dd><a href='/0/15/14198.html' >第一千两百三十四章 手段</a></dd>
                <dd><a href='/0/15/14199.html' >第一千两百三十五章 魔袭而来</a></dd>
                <dd><a href='/0/15/14200.html' >第一千两百三十六章 七王殿</a></dd>
                    
                      
                <dd><a href='/0/15/14201.html' >第一千两百三十七章 魔皇甲</a></dd>
                <dd><a href='/0/15/14202.html' >第一千两百三十八章 力战</a></dd>
                <dd><a href='/0/15/14203.html' >第一千两百三十九章 修炼之法</a></dd>
                <dd><a href='/0/15/14204.html' >第一千两百四十章 感应</a></dd>
                    
                      
                <dd><a href='/0/15/14205.html' >第一千两百四十一章 雷弓黑箭</a></dd>
                <dd><a href='/0/15/14206.html' >第一千两百四十二章 雷主</a></dd>
                <dd><a href='/0/15/14207.html' >第一千两百四十三章 魔狱之事</a></dd>
                <dd><a href='/0/15/14208.html' >第一千两百四十四章 再回异魔域</a></dd>
                    
                      
                <dd><a href='/0/15/14209.html' >第一千两百四十五章 唤醒焚天</a></dd>
                <dd><a href='/0/15/14210.html' >第一千两百四十六章 相聚</a></dd>
                <dd><a href='/0/15/14211.html' >第一千两百四十七章 安宁</a></dd>
                <dd><a href='/0/15/14212.html' >第一千两百四十八章 鹰宗</a></dd>
                    
                      
                <dd><a href='/0/15/14213.html' >第一千两百四十九章 故人</a></dd>
                <dd><a href='/0/15/14214.html' >第一千两百五十章 碑中之魔</a></dd>
                <dd><a href='/0/15/14215.html' >第一千两百五十一章 九王殿</a></dd>
                <dd><a href='/0/15/14216.html' >第一千两百五十二章 诛杀</a></dd>
                    
                      
                <dd><a href='/0/15/14217.html' >第一千两百五十三章 差之丝毫</a></dd>
                <dd><a href='/0/15/14218.html' >第一千两百五十四章 回宗</a></dd>
                <dd><a href='/0/15/14219.html' >第一千两百五十五章 师徒相聚</a></dd>
                <dd><a href='/0/15/14220.html' >第一千两百五十六章 位面裂缝</a></dd>
                    
                      
                <dd><a href='/0/15/14221.html' >第一千两百五十七章 晋入轮回</a></dd>
                <dd><a href='/0/15/14222.html' >第一千两百五十八章 动荡之始</a></dd>
                <dd><a href='/0/15/14223.html' >第一千两百五十九章 再至乱魔海</a></dd>
                <dd><a href='/0/15/14224.html' >第一千两百六十章 万魔围岛</a></dd>
                    
                      
                <dd><a href='/0/15/14225.html' >第一千两百六十一章 熟人</a></dd>
                <dd><a href='/0/15/14226.html' >第一千两百六十二章 洪荒之主</a></dd>
                <dd><a href='/0/15/14227.html' >第一千两百六十三章 大战来临</a></dd>
                <dd><a href='/0/15/14228.html' >第一千两百六十四章 再遇七王殿</a></dd>
                    
                      
                <dd><a href='/0/15/14229.html' >第一千两百六十五章 血战</a></dd>
                <dd><a href='/0/15/14230.html' >第一千两百六十六章 魔皇虚影</a></dd>
                <dd><a href='/0/15/14231.html' >第一千两百六十七章 混沌之箭</a></dd>
                <dd><a href='/0/15/14232.html' >第一千两百六十八章 应欢欢出手</a></dd>
                    
                      
                <dd><a href='/0/15/14233.html' >第一千两百六十九章 空间之主</a></dd>
                <dd><a href='/0/15/14234.html' >第一千两百七十章 诸强汇聚</a></dd>
                <dd><a href='/0/15/14235.html' >第一千两百七十一章 巅峰对恃</a></dd>
                <dd><a href='/0/15/14236.html' >第一千两百七十二章 祖宫阙</a></dd>
                    
                      
                <dd><a href='/0/15/14237.html' >第一千两百七十三章 联盟</a></dd>
                <dd><a href='/0/15/14238.html' >第一千两百七十四章 大殿盛宴</a></dd>
                <dd><a href='/0/15/14239.html' >第一千两百七十五章 大会</a></dd>
                <dd><a href='/0/15/14240.html' >第一千两百七十六章 开启祖宫阙</a></dd>
                    
                      
                <dd><a href='/0/15/14241.html' >第一千两百七十七章 修炼之路</a></dd>
                <dd><a href='/0/15/14242.html' >第一千两百七十八章 动荡</a></dd>
                <dd><a href='/0/15/14243.html' >第一千两百七十九章 凝聚神宫</a></dd>
                <dd><a href='/0/15/14244.html' >第一千两百八十章 三大联盟</a></dd>
                    
                      
                <dd><a href='/0/15/14245.html' >第一千两百八十一章 天王殿</a></dd>
                <dd><a href='/0/15/14246.html' >第一千两百八十二章 一瞬十年</a></dd>
                <dd><a href='/0/15/14247.html' >第一千两百八十三章 青雉战魔</a></dd>
                <dd><a href='/0/15/14248.html' >第一千两百八十四章 平定乱魔海</a></dd>
                    
                      
                <dd><a href='/0/15/14249.html' >第一千两百八十五章 四玄域联盟</a></dd>
                <dd><a href='/0/15/14250.html' >第一千两百八十六章 争吵</a></dd>
                <dd><a href='/0/15/14251.html' >第一千两百八十七章 生死之主</a></dd>
                <dd><a href='/0/15/14252.html' >第一千两百八十八章 大军齐聚</a></dd>
                    
                      
                <dd><a href='/0/15/14253.html' >第一千两百八十九章 进攻西玄域</a></dd>
                <dd><a href='/0/15/14254.html' >第一千两百九十章 西玄大沙漠</a></dd>
                <dd><a href='/0/15/14255.html' >第一千两百九十一章 天地大战</a></dd>
                <dd><a href='/0/15/14256.html' >第一千两百九十二章 激斗三王殿</a></dd>
                    
                      
                <dd><a href='/0/15/14257.html' >第一千两百九十三章 魔皇之像</a></dd>
                <dd><a href='/0/15/14258.html' >第一千两百九十四章 魔皇之手</a></dd>
                <dd><a href='/0/15/14259.html' >第一千两百九十五章 自己来守护</a></dd>
                <dd><a href='/0/15/14260.html' >第一千两百九十六章 位面裂缝</a></dd>
                    
                      
                <dd><a href='/0/15/14261.html' >第一千两百九十七章 后手</a></dd>
                <dd><a href='/0/15/14262.html' >第一千两百九十八章 抉择</a></dd>
                <dd><a href='/0/15/14263.html' >第一千两百九十九章 青阳镇</a></dd>
                <dd><a href='/0/15/14264.html' >第一千三百章 一年</a></dd>
                    
                      
                <dd><a href='/0/15/14265.html' >第一千三百零一章 成功与否</a></dd>
                <dd><a href='/0/15/14266.html' >第一千三百零二章 祈愿</a></dd>
                <dd><a href='/0/15/14267.html' >第一千三百零三章 轮回</a></dd>
                <dd><a href='/0/15/14268.html' >第一千三百零四章 封印破碎</a></dd>
                    
                      
                <dd><a href='/0/15/14269.html' >第一千三百零五章 晋入祖境</a></dd>
                <dd><a href='/0/15/14270.html' >第一千三百零六章 最后一战</a></dd>
                <dd><a href='/0/15/14271.html' >第一千三百零七章 我要把你找回来</a></dd>
                <dd><a href='/0/15/14272.html' >结局感言以及新书</a></dd>
                    
                      
                <dd><a href='/0/15/14273.html' >大结局活动，1744，欢迎大家。</a></dd>
                <dd><a href='/0/15/14274.html' >应欢欢篇</a></dd>
                <dd><a href='/0/15/14275.html' >绫清竹篇</a></dd>
                <dd><a href='/0/15/7009895.html' >新书大主宰已发。</a></dd>
                </dl>
            </div>
        </div>
        
        <div class="dahengfu"><script type="text/javascript">list_bot();</script></div>
        
        <div id="footer" name="footer">
            <div class="footer_link">&nbsp;新书推荐：<a href="http://www.qtshu.com/wdqk/" target="_blank">武动乾坤</a>、<a href="http://www.xbiquge.la/72/72758/" target="_blank">洪荒之开局怒撕封神榜</a>、<a href="http://www.xbiquge.la/72/72757/" target="_blank">洁白之誓</a>、<a href="http://www.xbiquge.la/72/72756/" target="_blank">此刻我为东方守护神</a>、<a href="http://www.xbiquge.la/72/72755/" target="_blank">请叫我超人吧</a>、<a href="http://www.xbiquge.la/72/72754/" target="_blank">文娱业的幕后大佬</a></div>
            <div class="footer_cont">
                <p>《武动乾坤》情节跌宕起伏、扣人心弦1，是一本情节与文笔俱佳的玄幻小说，新笔趣阁转载收集武动乾坤最新章节。</p>
                <script>footer();right();dl();</script>
            </div>
        </div>
        <script>
    (function(){
        var bp = document.createElement('script');
        bp.src = '//push.zhanzhang.baidu.com/push.js';
        var s = document.getElementsByTagName("script")[0];
        s.parentNode.insertBefore(bp, s);
    })();
</script>
    """
    res = AttrField("href", css_select='#list > dl > dd:nth-child(1) > a').extract(html)
    print(res)
