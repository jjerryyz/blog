官方文档地址：<https://www.tornadoweb.org/en/stable/>



## 准备

python存在多个版本，不同的项目有时候需要不同的python版本，我们希望不同的项目可以运行在各自的python环境中，这个时候就用到 virtualenv 这个工具了

#### 安装虚拟环境
`pip install virtualenv` 

#### 当前目录下安装 python3.7 虚拟环境

`virtualenv.exe venv -p C:\Users\Administrator\AppData\Local\Programs\Python\Python37-32\python.exe`

#### 激活环境
`.\venv\Scripts\activate`

#### 列出当前已经安装的模块
`pip list`

#### 退出当前 python3.7 虚拟环境
`deactivate`

#### python寻找路径

- 当前目录
- PYTHONPATH 环境变量下
- 默认路径。UNIX下，默认路径一般为/usr/local/lib/python/



## 安装

#### 不使用 WSGI

WSGI（Web Server Gateway Interface） 定义了 web 应用和 web 服务器之间的接口，tornado 没有实现 WSGI

#### 线程安全
tornado 不是线程安全的，唯一可以安全的从别的线程调用的方法是 IOLoop.add_callback; 还可以使用 IOLoop.run_in_executor 调用别的线程的阻塞方法，但要注意不要在传入 run_in_executor 的方法中引用任何 tornado对象

#### asyncio
tornado 使用 asyncio 作为异步 io 库

#### 安装 toranado 环境
`pip install tornado`

或者从下载源码，本地安装

`git clone https://github.com/tornadoweb/tornado.git`
`python setup.py install`



## 引入

tornado 包含四个部分

- 一个web框架提供创建web应用的能力
- 实现了client和server端的http协议
- 一个异步io网络库，支撑构造http组件以及其他协议的实现
- 一个协程库（torado.gen)



## 异步与非阻塞

web框架的同步请求模型为每一个请求创建一条线程，极大的消耗资源；tornado使用基于消息队列的异步请求模型解决这个问题

tornado框架具有异步和阻塞两大特点：

#### 阻塞

调用函数时，占用cpu资源并一直等待某些工作完成，这成为阻塞。阻塞的原因可以是磁盘I/O，网络I/O，互斥锁（mutexes）。在tornado，一般指的是网络 I/O。

#### 异步

异步模型有多种实现方式，无论哪一种方式对于调用者来说都是不透明的

- 传入回调参数
- 传入占位符（placeholder），比如Future、Promise、Defered
- 消息队列
- 注册回调函数表，比如 POSIX 的信号量

tornado中使用的Future模型，也就是使用占位符的方式，一个简单的例子

```python
from tornado.httpclient import HTTPClient,AsyncHTTPClient

# 同步实现http获取一个资源
def synchronous_fetch(url):
    http_client = HTTPClient()
    response = http_client.fetch(url)
    return response.body
# 异步实现
async def asynchronous_fetch(url):
    http_client = AsyncHTTPClient()
    # 不会等待http_client获取到资源才返回
    response = await http_client.fetch(url)
    # 返回给这个方法的调用者的同样是一个future对象，因此调用者本身也需要使用 await 关键字
    return response.body
```



## 协程

#### 原理

<https://www.jianshu.com/p/d63a0ab93805>

#### 使用协程

- 协程方法返回的异常只有在下一次 `yield` 的时候，才能捕捉到
- 大部分情况，只有协程方法本身可以调用协程方法
- 使用`IOLoop.spawn_callback` 处理不关心的协程方法返回，发生异常时，`IOLoop`负责打印一条消息
- 使用`IOLoop.current().run_sync()`启动IOLoop，这通常在基于批处理的程序的顶层逻辑中使用

#### 范式

调用阻塞方法

```python
# run_in_executor方法返回一个与协程兼容的Future对象
async def call_blocking():
	await IOLoop.current().run_in_executor(None, blocking_func, args)
```

调用并行方法

```python
from tornado.gen import multi

async def parallel_fetch(url1, url2):
    resp1, resp2 = await multi([http_client.fetch(url1),
                                http_client.fetch(url2)])

async def parallel_fetch_many(urls):
    responses = await multi ([http_client.fetch(url) for url in urls])
    # responses is a list of HTTPResponses in the same order

async def parallel_fetch_dict(urls):
    responses = await multi({url: http_client.fetch(url)
                             for url in urls})
    # responses is a dict {url: HTTPResponse}
```

将协程转为await调用

```python
from tornado.gen import convert_yielded

async def get(self):
    # convert_yielded() 在后台启动一个本地的协程，相当于转为await的形式
    # 也可以用asyncio.ensure_future()实现
    fetch_future = convert_yielded(self.fetch_next_chunk())
    while True:
        chunk = yield fetch_future
        if chunk is None: break
        self.write(chunk)
        # 将协程转为await形式，因此程序不会在这里让出执行权
        fetch_future = convert_yielded(self.fetch_next_chunk())
        yield self.flush()
```

循环中调用

旧版的python，无法在`for`或者`while`中使用`yield`关键字，需要在代码中分离循环和获取结果的逻辑

```python
import motor
db = motor.MotorClient().test

@gen.coroutine
def loop_example(collection):
    cursor = db.collection.find()
    while (yield cursor.fetch_next):
        doc = cursor.next_object()
```

后台定时任务

```python
# 每次执行都延时60秒
async def minute_loop():
    while True:
        await do_something()
        await gen.sleep(60)

# 准确的花费60秒执行任务
async def minute_loop2():
    while True:
        nxt = gen.sleep(60)   # Start the clock.
        await do_something()  # Run while the clock is ticking.
        await nxt             # Wait for the timer to run out.

# Coroutines that loop forever are generally started with
# spawn_callback().
IOLoop.current().spawn_callback(minute_loop)
```



## Web应用架构

一个tornado web应用最少包含以下元素：

- 继承`RequestHandler`的类，用于具体处理请求
- Application对象，负责路由请求到前面定义的`RequestHandler`
- main入口，负责启动服务，监听端口

#### Application对象

负责路由请求和具体的请求处理类

- 路由是一个正则，系统会使用首个匹配到的路由
- url的路径参数将会作为参数传递个`RequestHandler`
- 路由第三个参数指定传递给`RequestHandler.initialize`方法的字典，从字面上看用作初始化请求
- 第四个参数指定这个`URLSec`的名字

```python
class MainHandler(RequestHandler):
    def get(self):
        self.write('<a href="%s">link to story 1</a>' %
                   self.reverse_url("story", "1"))

class StoryHandler(RequestHandler):
    def initialize(self, db):
        self.db = db

    def get(self, story_id):
        self.write("this is story %s" % story_id)

app = Application([
    url(r"/", MainHandler),
    url(r"/story/([0-9]+)", StoryHandler, dict(db=db), name="story")
    ])
```

`Application.setting`负责自定义`Application`的行为

#### RequestHandler

- `get()`、`post()`等方法被用作处理http请求，这些方法会被以前面解析出来的正确的参数调用
- `RequestHandler.render()`渲染模板
- `RequestHandler.write()`可以传入`strings`、`byte`和`dict`（被编码为JSON）

#### 处理表单

HTML表单已经被解析成方便的形式，通过`get_body_argument`和`get_query_argument`获取

```python
class MyFormHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('<html><body><form action="/myform" method="POST">'
                   '<input type="text" name="message">'
                   '<input type="submit" value="Submit">'
                   '</form></body></html>')

    def post(self):
        self.set_header("Content-Type", "text/plain")
        self.write("You wrote " + self.get_body_argument("message"))
```

- `RequestHandler.get_query_argument()` 返回一个list
- `RequestHandler.get_body_argument()` 返回整个body

#### 上传文件

表单文件被解析成`self.request.files`，`files`对象是一个`map`，`name`是<input type="file"/>的名字，`key`是一个`form`对象字典`{"filename":..., "content_type":..., "body":...}`

- `Content-Type`为`multipart/form-data`，以正常方式处理
- 否则将以原生数据的形式存在内存中，使用`self.request.body`访问
- 如果上传的数据量太大，内存不足，使用`stream_request_body`类修饰器

#### 处理其他格式数据的表单

由于HTML表单对于单个值和多个参数混淆不清，tornado并没有做其他格式的解析，用户可以覆写`prepare()`来自己处理，如处理JSON格式数据

```python
def prepare(self):
    if self.request.headers.get("Content-Type", "").startswith("application/json"):
        self.json_args = json.loads(self.request.body)
    else:
        self.json_args = None
```

#### 覆写RequestHandler中的方法

按照一个请求从先到后顺序，可以覆写以下方法:

1. 每次请求创建一个`RequestHandler`实例
2. `initialize()` 处理`Application`配置
3. `prepare()`处理数据解析，每个http请求都会调用；`finish()`或`redirect()`表示中断本次请求
4. `get()`、`post()`、`put()`等其中一个http方法被调用
5. 无论请求是否此时已经结束，`on_finish()`都会在http方法后被调用

#### 错误处理

- 使用`RequestHandler.write_error`响应错误页
- 默认返回500错，也可以使用`tornado.web.HTTPError`产生错误码

#### 转发（Redirection)

使用`RequestHandler.redirect()`或`RequestHandler`转发请求，它们都有一个可选的参数`perminent`，表示调用时返回不同的状态码。

- `permanent`为`false`，产生`302 Found`；否则产生`301 Moved Permanently`
- `self.redirect()` 用在执行请求过程中转发，默认`permanent`为`false`
- `RequestHandler`用在既定的路由表中，默认`permanent`为`true`

```python
app = tornado.web.Application([
    url(r"/photos/(.*)", MyPhotoHandler),
    url(r"/pictures/(.*)", tornado.web.RedirectHandler,
        dict(url=r"/photos/{0}")),
    ])
```



## 模板和UI

`tornado`本身包含一个模板系统，同时也支持扩展其他python模板库，框架并没有对渲染的实现做任何约束，外部扩展框架只要完成渲染后，调用`RequestHandler.write()`即可

#### 配置模板

- 默认在脚本执行目录下寻找模板文件，配置Application对象的template_path自定义路径
- 默认模板渲染缓存是打开的，配置`compiled_template_cache=False`或者`debug=True`关闭功能

#### 模板语法

- 以`{%` 和`%}`包裹表达式
- 控制语句使用 `{%`和 `%}`括起来，如`{% if len(items) > 2 %}`
- 表达式使用`{}`，如`{ items[0] }`，允许使用任意表达式，其中可以调用的函数列表在官方文档中列出
- 使用`extends`和`block`表达式继承模板

