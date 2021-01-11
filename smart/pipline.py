# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      middlewire
# Author:    liangbaikai
# Date:      2020/12/28
# Desc:      there is a python file description
# ------------------------------------------------------------------
from copy import copy
from functools import wraps
from typing import Union, Callable


class Piplines:
    def __init__(self):
        # item piplines
        self.piplines = []

    def pipline(self, order_or_func: Union[int, Callable]):
        def outWrap(func):
            """
            Define a Decorate to be called before a request.
            eg: @middleware.request
            """

            @wraps(func)
            def register_pip(*args, **kwargs):
                self.piplines.append((order_or_func, func))
                self.piplines = sorted(self.piplines, key=lambda key: key[0])
                return func

            return register_pip()

        if callable(order_or_func):
            cp_order = copy(order_or_func)
            order_or_func = 0
            return outWrap(cp_order)
        return outWrap

    def __add__(self, other):
        pls = Piplines()
        pls.piplines.extend(self.piplines)
        pls.piplines.extend(other.piplines)
        pls.piplines = sorted(pls.piplines, key=lambda key: key[0])
        return pls
