import logging #导入logging模块 日志默认级别：DEBUG<INFO<[WARNING<ERROR<CRITICAL]
logging.basicConfig(level = logging.INFO)#设置日志级别为INFO类及以上可以显示
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web

#定义处理URL函数：
def index(request):
	return web.Response(body = b'<h1>Awesome<h1>', content_type='text/html')

@asyncio.coroutine
def init(loop):
	#创建WEB服务器实例，用于处理URL的HTTP协议：
	app = web.Application(loop = loop)
	#将处理URL的函数注册进应用路径Application.router，将index与HTTP方法GET及路径‘/’绑定，浏览器输入URL时返回index结果：
	app.router.add_route('GET', '/', index)
	#用协程创建监听服务，使用aiohttp的HTTP协议簇app.make_handler(),
	srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv

#创建协程：
loop = asyncio.get_event_loop()
#开始运行协程初始化：
loop.run_until_complete(init(loop))
#运行协程直到调用stop():
loop.run_forever()