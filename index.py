import tornado.ioloop
import tornado.locks
import tornado.web
import tornado.options
import os.path
import mistune
import pymongo
from tornado.options import define, options
import unicodedata
import re

define("db_port", default=27017, help="run on the given port", type=int)
define("db_host", default="127.0.0.1", help="run on the given host")
define("db_name", default="jj_blog", help="blog database name")

class NoResultError(Exception):
    pass

class Application(tornado.web.Application):
    # 在 __new__之后调用，创建对象后，在这里初始化对象
    def __init__(self, db):
        self.db = db
        handler = [
            (r"/", HomeHandler),
            (r"/compose", ComposeHandler),
            (r"/entry/([^/]+)", EntryHandler)
        ]
        settings = dict(
            blog_title=u"Tornado Blog",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={"Entry": EntryModule},
            # xsrf_cookies=True,
            # cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            # login_url="/auth/login",
            autoreload=True,
            debug=True,
        )
        super(Application, self).__init__(handler, **settings)

class BaseHandler(tornado.web.RequestHandler):
    async def query(self):
        return self.application.db['article'].find()

    async def query_one(self, myquery):
        result = self.application.db['article'].find_one(myquery)
        if not result:
            raise NoResultError()
        else:
            return result

    async def insert(self, mydict):
        return self.application.db['article'].insert_one(mydict)

class ComposeHandler(BaseHandler):
    async def get(self):
        self.render('compose.html', entry={})

    async def post(self):
        title = self.get_argument('title')
        text = self.get_argument("markdown")
        html = mistune.markdown(text)

        slug = unicodedata.normalize("NFKD", title)
        slug = re.sub(r"[^\w]+", " ", slug)
        slug = "-".join(slug.lower().strip().split())
        slug = slug.encode("ascii", "ignore").decode("ascii")
        if not slug:
            slug = "entry"

        await self.insert({'title': title, 'slug': slug, 'html': html})
        self.redirect("/entry/" + slug)

class HomeHandler(BaseHandler):
    async def get(self):
        items = await self.query()
        if not items or items.count() == 0:
            raise tornado.web.HTTPError(404)
        self.render('home.html', items=items)

class EntryHandler(BaseHandler):
    async def get(self, slug):
        query = await self.query_one({'slug': slug}) 
        self.render("entry.html", entry=query['html'])
   
class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)

async def create_db_connection():
    myclient = pymongo.MongoClient("mongodb://{}:{}/".format(options.db_host, options.db_port))
    if options.db_name in myclient.list_database_names():
        print("{} db exist".format(options.db_name))
    db = myclient[options.db_name]
    # 创建索引，保证 article 表中的 slug 唯一
    db['article'].create_index([('slug', pymongo.ASCENDING)], unique=True)
    return db

async def main():
    # 解析命令行
    tornado.options.parse_command_line()
    # 解析配置文件
    # tornado.options.parse_config_file()

    db = await create_db_connection()
    app = Application(db)
    app.listen(8888)

    # 程序会等待 Ctrl-C 事件，收到事件后退出
    # 也可以调用 shutdown_event.set() 暴力退出
    shutdown_event = tornado.locks.Event()
    await shutdown_event.wait()

if __name__ == "__main__":

    # app = Application()
    # app.listen(8888)
    # start 调用后，ioloop开始执行（ioloop会在后台执行），
    # 并且一直运行直到有其中一个callback（使用add_callback方法添加）调用 stop 方法
    # tornado.ioloop.IOLoop.current().start()

    # run_sync 会执行 main 方法，等待 main 返回后释放 ioloop
    # main 可以返回 await 对象或者none，如果返回 await 对象，则会等待 await 执行完毕才释放 ioloop
    tornado.ioloop.IOLoop.current().run_sync(main)
