# -*- coding: utf-8 -*-

import bcrypt
import pymongo
import tornado.escape
import tornado.options
from tornado.options import define, options
import sys

define("action",default='', help="action")
define("user",default='admin', help="account")
define("password", default='123456', help="password")

myclient = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = myclient.jj_blog

def create_user():
    print('user:', options.user, 'password: ', options.password)
    password = bcrypt.hashpw(tornado.escape.utf8(options.password), bcrypt.gensalt())
    password = tornado.escape.to_unicode(password)
    db.user.create_index([('user', pymongo.ASCENDING)], unique=True)
    result = db.user.insert_one({'user': options.user, 'password': password})
    print(result)

def drop_user():
    result = db.user.drop()
    print(result)

def drop_articles():
    result = db.article.drop()
    print(result)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    print('action: ', options.action)
    try: 
        if options.action == 'create_user':
            create_user()
        elif options.action == "drop_user":
            drop_user()
        elif options.action == 'drop_article':
            drop_articles()
    except Exception:
        pass


    