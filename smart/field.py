# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      item
# Author:    liangbaikai
# Date:      2020/12/31
# Desc:      there is a python file description
# ------------------------------------------------------------------
import json
import re
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
    pass
