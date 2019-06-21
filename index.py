import tornado.ioloop
import tornado.web
import os.path

class Application(tornado.web.Application):
    # 在 __new__之后调用，创建对象后，在这里初始化对象
    def __init__(self):
        handler = [
            (r"/", HomeHandler)
        ]
        settings = dict(
            blog_title=u"Tornado Blog",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            # ui_modules={"Entry": EntryModule},
            # xsrf_cookies=True,
            # cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            # login_url="/auth/login",
            autoreload=True,
            debug=True,
        )
        super(Application, self).__init__(handler, **settings)

class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        items = [{'title': "title1", 'link': '#'}, {'title': "title2", 'link': '#'}]
        self.render('home.html', items=items)

if __name__ == "__main__":
    app = Application()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()