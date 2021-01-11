# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      item
# Author:    liangbaikai
# Date:      2020/12/31
# Desc:      there is a python file description
# ------------------------------------------------------------------
from __future__ import annotations

import copy
import inspect
from typing import Any, Union

from lxml import etree
from ruia.exceptions import InvalidFuncType

from smart.field import BaseField, RegexField, FuncField


class ItemMeta(type):
    """
    Metaclass for an item
    """

    def __new__(cls, name, bases, attrs):
        __fields = dict(
            {
                (field_name, attrs.get(field_name))
                for field_name, object in list(attrs.items())
                if not field_name.startswith("_") and not inspect.isfunction(object)
                # if isinstance(object, BaseField)
                # and not field_name.startswith("_")
            }
        )
        attrs["__fields"] = __fields
        new_class = type.__new__(cls, name, bases, attrs)
        return new_class


# class Item(metaclass=ItemMeta):
#     """
#     Item class for each item
#     """
#
#     def __init__(self, source):
#         self.__source = source
#         results = self.__get_item() or {}
#         self.__dict__.update(results)
#
#     def to_dict(self):
#         dict___items = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
#         return dict___items
#
#     def extract(self, key, other_source):
#         if not key or not other_source:
#             return None
#         cls = self.__class__
#         fields = getattr(cls, "__fields")
#         if key not in fields.keys():
#             return None
#         for k, v in fields.items():
#             if isinstance(v, BaseField):
#                 value = v.extract(other_source)
#                 self.__dict__.update(key=value)
#                 return value
#
#     def __get_item(
#             self,
#     ) -> Any:
#         cls = self.__class__
#         fields = getattr(cls, "__fields")
#         dict = {}
#         for k, v in fields.items():
#             if isinstance(v, BaseField):
#                 value = v.extract(self.__source)
#             else:
#                 value = v
#             dict.setdefault(k, value)
#         for k, v in cls.__dict__.items():
#             if k.startswith("_"):
#                 continue
#             dict.setdefault(k, v)
#         return dict
#
#     def __getitem__(self, key):
#         return self.__dict__[key]
#
#     def __setitem__(self, key, value):
#         if key in self.__dict__.keys():
#             self.__dict__[key] = value
#         else:
#             raise KeyError("%s does not support field: %s" %
#                            (self.__class__.__name__, key))


class Item(metaclass=ItemMeta):
    """
    Item class for each item
    """

    def __init__(self):
        self.ignore_item = False
        self.results = {}

    @classmethod
    def _get_html(cls, html: str = "", **kwargs):
        if html:
            return etree.HTML(html)
        else:
            raise ValueError("<Item: html(url or html_etree) is expected.")

    @classmethod
    def _parse_html(cls, html_etree: Union[str, dict, etree._Element]):
        if html_etree is None:
            raise ValueError("<Item: html_etree or str or dict  is expected>")
        item_ins = cls()
        fields_dict = getattr(item_ins, "__fields", {})
        for field_name, field_value in fields_dict.items():
            if not field_name.startswith("target_"):
                clean_method = getattr(item_ins, f"clean_{field_name}", None)
                if isinstance(field_value, BaseField):
                    value = field_value.extract(html_etree)
                else:
                    value = getattr(item_ins, field_name)
                if clean_method is not None and callable(clean_method):
                    try:
                        value = clean_method(value)
                    except Exception:
                        item_ins.ignore_item = True

                setattr(item_ins, field_name, value)
                item_ins.results[field_name] = value
        return item_ins

    @classmethod
    def get_item(
            cls,
            html: str = "",
            **kwargs,
    ) -> Any:
        return cls._parse_html(html_etree=html)

    @classmethod
    def get_items(
            cls,
            html: Union[str, dict, etree._Element],
            **kwargs,
    ):
        items_field = getattr(cls, "__fields", {}).get("target_item", None)
        if items_field:
            items_field.many = True
            items_html_etree = items_field.extract(
                html=html
            )
            if items_html_etree:
                for each_html_etree in items_html_etree:
                    item = cls._parse_html(html_etree=each_html_etree)
                    if not item.ignore_item:
                        yield item
            else:
                value_error_info = "<Item: Failed to get target_item's value from"
                if html:
                    value_error_info = f"{value_error_info} html.>"
                raise ValueError(value_error_info)
        else:
            raise ValueError(
                "<Item: target_item is expected, more info: https://docs.python-ruia.org/en/apis/item.html>"
            )

    def __repr__(self):
        return "<Item %s>" % (self.results,)

    def __getitem__(self, key):
        return self.results.get(key)

    def __setitem__(self, key, value):
        if key in self.results.keys():
            self.results[key] = value
        else:
            raise KeyError("%s does not support field: %s" %
                           (self.__class__.__name__, key))

    def __setattr__(self, name, value):
        if self.__dict__.get("results") is None:
            self.__dict__[name] = value
        else:
            self.__dict__["results"][name] = value

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration()
