import os, time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import *
from sqlalchemy.orm import *

"""

Random write: 156.8178246156252 objects/second
Random read: 5345.280200970007 objects/second

"""

NB = 10000

db_filename = "/home/jiba/tmp/bench_sqlalchemy.sqlite3"
if os.path.exists(db_filename): os.unlink(db_filename)
engine = create_engine("sqlite:///%s" % db_filename)
SQLObject = declarative_base()

class Node(SQLObject):
  __tablename__ = "Node"
  id        = Column(Integer, primary_key = True)
  label     = Column(String, index = True)
  next_id   = Column(Integer, ForeignKey('Node.id'), index = True)
  next      = relationship("Node")

SQLObject.metadata.create_all(engine)
Session = sessionmaker(bind = engine)
session = Session()


t = time.time()
previous = None
for i in range(NB):
  node = Node(label = "node number %s" % i)
  session.add(node)
  if previous:
    previous.next.append(node)
  previous = node
session.commit()
dt = time.time() - t
print("Random write:", 1/dt*NB, "objects/second")



t = time.time()
node = list(session.query(Node).filter(Node.label == "node number 0"))[0]
while True:
  label = node.label
  if node.next:
    node = node.next[0]
  else:
    break
dt = time.time() - t
print("Random read:", 1/dt*NB, "objects/second")

if os.path.exists(db_filename): os.unlink(db_filename)
