import asyncio
import time
from concurrent.futures.thread import ThreadPoolExecutor

from smart.middlewire import Middleware

middleware2 = Middleware()

total_res = 0
succedd = 0


class ReqInte:

    @staticmethod
    @middleware2.request(-1)
    def print_on_request1(spider_ins, request):
        print(f"ReqInteReqInteReqInteReqInt{spider_ins.name} e#{request}######################")


@middleware2.request(1)
async def print_on_request(spider_ins, request):
    request.metadata = {"url": request.url}
    global total_res
    total_res += 1
    print(f"requesssst: {request.metadata}")
    print(f"total_res: {total_res}")

    # Just operate request object, and do not return anything.


@middleware2.response
def print_on_response(spider_ins, request, response):
    if response and 0 < response.status <= 200:
        global succedd
        succedd += 1
    print(f"response0: {response.status}")
    print(f"succedd: {succedd}")
