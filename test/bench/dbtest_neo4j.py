import time
from neo4j import GraphDatabase

"""

Random write: 245.33559386034676 objects/second
Bulk read: 52825.918844916654 objects/second
Random read: 223.60659061924466 objects/second

"""

db = GraphDatabase.driver("bolt://localhost", auth = ("", ""))
session = db.session()

NB = 10000

"""
Supprime toute la base :

MATCH (n)  OPTIONAL MATCH (n)-[r]-()  DELETE n,r

"""
    
t = time.time()
#tx = session.begin_transaction()
#tx.run("""CREATE INDEX ON :Node(label)""")
#tx.commit()
tx = session.begin_transaction()
previous = None
for i in range(NB):
  label = "node number %s" % i
  node = tx.run("""CREATE (x:Node {label:"%s"}) RETURN id(x)""" % label).value()[0]
  if previous:
    tx.run("""MATCH (x:Node) WHERE id(x)=%s MATCH (y:Node) WHERE id(y)=%s CREATE (x)-[:NEXT]->(y)""" % (previous, node))
  previous = node
tx.commit()
dt = time.time() - t
print("Random write:", 1/dt*NB, "objects/second")


t = time.time()
tx = session.begin_transaction()
labels = tx.run("""MATCH (x:Node) RETURN x.label""").value()
nexts  = tx.run("""MATCH (x:Node)-[:NEXT]->(y:Node) RETURN id(x), id(y)""").values()
tx.commit()
dt = time.time() - t
print("Bulk read:", 1/dt*NB, "objects/second")

t = time.time()
tx = session.begin_transaction()
node = tx.run("""MATCH (x:Node) WHERE x.label="node number 0" RETURN id(x)""").value()[0]
while True:
  label = tx.run("""MATCH (x:Node) WHERE id(x)=%s RETURN x.label""" % node).value()[0]
  nexts = tx.run("""MATCH (x:Node)-[:NEXT]->(y:Node) WHERE id(x)=%s RETURN id(y)""" % node).value()
  if nexts:
    node = nexts[0]
  else:
    break
dt = time.time() - t
print("Random read:", 1/dt*NB, "objects/second")
