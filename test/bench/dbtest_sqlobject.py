import os, time
import sqlobject

"""

Random write: 51.22364591545335 objects/second
Random read: 11727.926239654573 objects/second

"""

NB = 10000

db_filename = "/home/jiba/tmp/bench_sqlobject.sqlite3"
if os.path.exists(db_filename): os.unlink(db_filename)
connection = sqlobject.connectionForURI("sqlite://%s" % db_filename)
sqlobject.sqlhub.processConnection = connection

class Node(sqlobject.SQLObject):
  label      = sqlobject.StringCol()
  next       = sqlobject.ForeignKey("Node")
  next_index = sqlobject.DatabaseIndex("next")
Node.createTable()

t = time.time()
previous = None
for i in range(NB):
  node = Node(label = "node number %s" % i, next = None)
  if previous:
    previous.next = node
  previous = node
dt = time.time() - t
print("Random write:", 1/dt*NB, "objects/second")



t = time.time()
node = list(Node.select(Node.q.label == "node number 0"))[0]
while True:
  label = node.label
  if node.next:
    node = node.next
  else:
    break
dt = time.time() - t
print("Random read:", 1/dt*NB, "objects/second")

if os.path.exists(db_filename): os.unlink(db_filename)
