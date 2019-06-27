import bcrypt
import pymongo
import tornado.escape
import sys

myclient = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = myclient.jj_blog

def create_admin():
    password = bcrypt.hashpw(tornado.escape.utf8('123456'), bcrypt.gensalt())
    password = tornado.escape.to_unicode(password)
    db.user.create_index([('email', pymongo.ASCENDING)], unique=True)
    result = db.user.insert_one({'email': 'admin', 'password': password})
    print(result)

def drop_articles():
    result = db.article.drop()
    print(result)

if __name__ == "__main__":
    try: 
        action = sys.argv[1]   
        print('action: ', action)
        if action == 'create':
            create_admin()
        elif action == 'drop':
            drop_articles()
    except Exception:
        pass


    