import tornado.ioloop
import tornado.web
import os.path
import mistune

class Application(tornado.web.Application):
    # 在 __new__之后调用，创建对象后，在这里初始化对象
    def __init__(self):
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
    pass
html = ""
class ComposeHandler(BaseHandler):
    def get(self):
        self.render('compose.html', entry={})

    def post(self):
        global html
        text = self.get_argument("markdown")
        html = mistune.markdown(text)
        self.redirect("/entry/1")

class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        items = [{'title': 'Java内存泄漏分析', 'link': '#'}, {'title': 'Flusttr入门', 'link': '#'}]
        self.render('home.html', items=items, entry="entry")

class EntryHandler(tornado.web.RequestHandler):
    def get(self, slug):
        global html
        self.render("entry.html", entry=html)

class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)

if __name__ == "__main__":
    app = Application()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()