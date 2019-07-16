# -*- coding: utf-8 -*-

import tornado.ioloop
import tornado.locks
import tornado.web
import tornado.options
import os.path
import mistune
import pymongo
from bson.objectid import ObjectId
from tornado.options import define, options
import unicodedata
import re
import bcrypt
import subprocess
from toc import TocMixin

define("server_port", default=8080, help="run on the given server port", type=int)
define("db_port", default=27017, help="run on the given port", type=int)
define("db_host", default="127.0.0.1", help="run on the given host")
define("db_name", default="jj_blog", help="blog database name")

class TocRenderer(TocMixin, mistune.Renderer):
    pass

class NoResultError(Exception):
    pass

class Application(tornado.web.Application):
    # 在 __new__之后调用，创建对象后，在这里初始化对象
    def __init__(self, db):
        self.db = db
        handler = [
            (r"/", HomeHandler),
            (r"/compose/([^/]+)", ComposeHandler),
            (r"/entry/([^/]+)", EntryHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/manage", ManageHandler),
        ]
        settings = dict(
            blog_title=u"Jerry Blog",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={"Entry": EntryModule},
            xsrf_cookies=True,
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            autoreload=True,
            debug=True,
        )
        super(Application, self).__init__(handler, **settings)

class BaseHandler(tornado.web.RequestHandler):

    def set_default_headers(self):
        print("setting headers!!!")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    
    def options(self):
            # no body
            self.set_status(204)
            self.finish()

    def raw_to_obj(self, dictdata):
        obj = tornado.util.ObjectDict()
        for k in dictdata.keys():
            obj[k] = dictdata[k]
        return obj

    async def query(self, collection):
        return [self.raw_to_obj(row) for row in self.application.db[collection].find()]

    async def query_one(self, collection, myquery):
        result = self.application.db[collection].find_one(myquery)
        if not result:
            raise NoResultError()
        else:
            return self.raw_to_obj(result)

    async def insert(self, collection, mydict):
        return self.application.db[collection].insert_one(mydict)

    async def update(self, collection, filter, mydict):
        # 使用新的mydict更新记录，如果找不到则插入一条新的记录
        return self.application.db[collection].find_one_and_update(filter,{'$set': mydict},upsert=True)
    
    async def delete(self, collection, filter):
        return self.application.db[collection].delete_one(filter)

    # get_current_user 方法不支持异步请求，故而在prepare实现校验cookie的逻辑
    async def prepare(self):
        user_id = self.get_secure_cookie('blog_user')
        if user_id:
            user_id = str(tornado.escape.to_unicode(user_id))
            # mongodb 查询时的id不是一个普通的字符串，使用的是 bson.objectid
            user_id = ObjectId(user_id)
            try: self.current_user = await self.query_one('user', {'_id': user_id})
            except NoResultError: pass

class ManageHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self):
        try:
            articles = await self.query('article')
        except Exception:
            raise tornado.web.HTTPError(404)

        self.render('manage.html', articles=articles)
    
    @tornado.web.authenticated
    async def post(self):
        action = self.get_argument('action')
       
        if action == 'delete':
            slug = self.get_argument('slug')
            if not slug:  
                return tornado.web.HTTPError(500)

            result = await self.delete('article', {'slug': slug})
            if result is not None:
                self.write('ok')
            else:
                self.write('error')
        elif action == 'sync_with_git':
            # 创建子进程执行 git status命令，并且重定向到标准输出
            p = subprocess.Popen('git pull', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.write('ok')
            # while p.poll() is None:
            #     line = p.stdout.readline()
            #     line = line.strip()
            #     if line:
            #         print('subprocess: ' + str(line))
            # if p.returncode == 0:
            #     self.write('ok')
            # else:
            #     self.write('not_sync')
        else:
            await tornado.web.HTTPError(404)

class AuthLoginHandler(BaseHandler):
    async def get(self):
        self.render('login.html', error=False)
    
    async def post(self):
        user = self.get_argument('user')
        password = self.get_argument('password')

        try:
            user = await self.query_one('user', {'user': user})
        except NoResultError:
            self.render('login.html', error='user not exists')
            return

        try:
            hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
                None,
                bcrypt.hashpw,
                tornado.escape.utf8(password),
                tornado.escape.utf8(user['password'])
            )
        except ValueError:
            self.render('login.html', error='incorrect password')
            return
        hashed_password = tornado.escape.to_unicode(hashed_password)
        if user.password == hashed_password:
            id = str(user._id)
            self.set_secure_cookie('blog_user', id)
            self.redirect(self.get_argument('next', '/'))
        else:
            self.render('login.html', error='incorrect password')

class ComposeHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, slug):
        if slug == 'new':
            self.render('compose.html', entry={})
            return
        try:
            entry = await self.query_one('article', {'slug': slug})
            self.render('compose.html', entry=entry)
        except Exception:
            pass

    @tornado.web.authenticated
    async def post(self, slug):
        title = self.get_argument('title')
        slug = self.get_argument('slug')
        markdown = self.get_argument("markdown")

        # slug = unicodedata.normalize("NFKD", title)
        # slug = re.sub(r"[^\w]+", " ", slug)
        # slug = "-".join(slug.lower().strip().split())
        # slug = slug.encode("ascii", "ignore").decode("ascii")
        # if not slug:
        #     slug = "entry"
        await self.update('article',{'slug': slug}, {'title': title, 'slug': slug, 'markdown': markdown})
        self.redirect("/entry/" + slug)

class HomeHandler(BaseHandler):
    async def get(self):
        items = await self.query('article')
        if not items or len(items) == 0:
            raise tornado.web.HTTPError(404)
        self.render('home.html', items=items)

class EntryHandler(BaseHandler):
    async def get(self, slug):
        query = await self.query_one('article', {'slug': slug}) 

        toc = TocRenderer()
        md = mistune.Markdown(renderer=toc)
        toc.reset_toc()
        html = md.parse(query.markdown)
        # level 是展开的级数
        rv = toc.render_toc(level=3)

        self.render("entry.html", entry=html, toc=rv)
   
class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)

async def create_db_connection():
    myclient = pymongo.MongoClient("mongodb://{}:{}/".format(options.db_host, options.db_port))
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
    app.listen(options.server_port)

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
