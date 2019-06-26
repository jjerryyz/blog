import bcrypt
import pymongo
import tornado.escape

myclient = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
password = bcrypt.hashpw(tornado.escape.utf8('123456'), bcrypt.gensalt())
password = tornado.escape.to_unicode(password)
myclient.jj_blog.user.create_index([('email', pymongo.ASCENDING)], unique=True)
result = myclient.jj_blog.user.insert_one({'email': 'admin', 'password': password})
print(result)