# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      web
# Author:    liangbaikai
# Date:      2020/12/30
# Desc:      there is a python file description
# ------------------------------------------------------------------

from typing import Optional

from pydantic import BaseModel
from fastapi import FastAPI, Form

app = FastAPI()

import uvicorn


@app.get("/")
def read_root():
    return {"Hello": "World"}


class Item(BaseModel):
    a: int
    b: int


@app.post("/post_info1")
async def post_info1(request_data: Item):
    '''
    必须传json的post接口
    :param request_data: json字段（Item类）
    :return: 返回a+b的和
    '''
    a = request_data.a
    b = request_data.b
    c = a + b
    result = {'a': a, 'b': b, 'a+b': c}
    return result


@app.post('/user')  # 接受post请求
async def get_user(
        username: str = Form(...),  # 直接去请求体里面获取username键对应的值并自动转化成字符串类型
        pwd: int = Form(...)  # 直接去请求体里面获取pwd键对应的值并自动转化成整型
):
    return {
        'username': username,
        'pwd': pwd
    }


if __name__ == '__main__':
    uvicorn.run(app='web:app', host="127.0.0.1", port=8000, reload=True, debug=True)
