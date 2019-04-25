import os, time, tempfile
from owlready2 import *

"""

Random write: 12892.586777357414 objects/second
Random read: 19158.756753497568 objects/second

"""

tmp = "/home/jiba/tmp/tmp_bench.sqlite3" # Not in /tmp because in is stored in memory
NB = 10000

first_world = World(filename = tmp)
onto = first_world.get_ontology("http://test.org/onto.owl")

t = time.time()
with onto:
  class Node(Thing): pass
  class next(ObjectProperty): pass
  previous = None
  for i in range(NB):
    node = Node()
    node.label = "node number %s" % i
    if previous: previous.next = [node]
    previous = node
first_world.save()
dt = time.time() - t
print("Random write:", 1/dt*NB, "objects/second")

first_world.close()



second_world = World(filename = tmp) # Force reloading -- Owlready has aggressive caching behaviour!
onto = second_world.get_ontology("http://test.org/onto.owl").load()

t = time.time()
node = onto.node1
while node.next:
  label = node.label[0]
  node  = node.next [0]
dt = time.time() - t
print("Random read:", 1/dt*NB, "objects/second")

# import rdflib
# g = second_world.as_rdflib_graph()
# g.query("""SELECT ?b WHERE {
# ?b <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Class> . }""")
# second_world.close()


# t = time.time()
# third_world = World(filename = tmp)
# onto = third_world.get_ontology("http://test.org/onto.owl").load()
# g = third_world.as_rdflib_graph()
# r = g.query("""SELECT ?l ?y WHERE {
# ?x <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://test.org/onto.owl#Node> .
# ?x <http://www.w3.org/2000/01/rdf-schema#label> ?l .
# ?x <http://test.org/onto.owl#next> ?y .
#  }""")

# dt = time.time() - t
# print("Bulk read:", 1/dt*NB, "objects/second")


os.unlink(tmp)
