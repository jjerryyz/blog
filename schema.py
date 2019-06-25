import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["jj_blog"]
print(myclient.list_database_names())