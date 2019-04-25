import time
import pymongo
from bson.objectid import *

"""

Random write: 2289.2182089579446 objects/second
Bulk read: 291903.5688436056 objects/second
Random read: 4723.250955702068 objects/second

"""

NB = 10000


client = pymongo.MongoClient()
client.drop_database("test_bench")
db = client.test_bench
db_nodes = db.nodes

t = time.time()
previous = None
for i in range(NB):
  doc  = { "label" : "node number %s" % i }
  node = db_nodes.insert_one(doc).inserted_id
  if previous:
    db_nodes.update_one({"_id": previous}, { "$set" : {"next": [node]} })
  previous = node
dt = time.time() - t
print("Random write:", 1/dt*NB, "objects/second")


t = time.time()
for doc in db_nodes.find():
  next   = doc.get("next")  or []
  label  = doc.get("label") or ""
dt = time.time() - t
print("Bulk read:", 1/dt*NB, "objects/second")


t = time.time()
node = db_nodes.find_one({ "label" : "node number 0" })
while True:
  label = node["label"]
  if not "next" in node: break
  next = node["next"][0]
  node = db_nodes.find_one({ "_id" : next })
dt = time.time() - t
print("Random read:", 1/dt*NB, "objects/second")

client.drop_database("test_bench")
