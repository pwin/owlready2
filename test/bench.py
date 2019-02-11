# python ./owlready2/test/bench.py > /dev/null

# python ./owlready2/test/bench.py -f > /dev/null

#Load time 8.222911834716797 s.
#List class time 13.101578950881958 s.

import sys, time#, cProfile

import owlready2
from owlready2 import *

t = time.time()

if "-f" in sys.argv:
  default_world.set_backend(filename = "/home/jiba/tmp/go.sqlite3", exclusive = True) #, profiling = True)
  #default_world.set_backend("postgresql", user = "jiba")
  #default_world.set_backend("mysql", user = "jiba")
  
onto_path.append(os.path.dirname(__file__))
onto_path.append("/home/jiba/telechargements/base_med/")

#dron_ndc = get_ontology("http://purl.obolibrary.org/obo/dron/dron-ndc.owl").load()
#dron = get_ontology("http://purl.obolibrary.org/obo/dron.owl").load()
#vto = get_ontology("http://purl.obolibrary.org/obo/vto.owl").load()
go = get_ontology("http://purl.obolibrary.org/obo/go.owl").load()
#go = get_ontology("/tmp/go.nt").load()
default_world.save()

t = time.time() - t
print("Load time %s s." % t, file = sys.stderr)


t = time.time()

obo = go.get_namespace("http://purl.obolibrary.org/obo/")

#nb = 0
#def render(entity):
#  global nb
#  nb += 1
#  label = entity.label.first()
#  if label: return "%s:'%s'" % (entity.name, label)
#  return entity.name
#set_render_func(render)

#for c in default_world.classes():
#  print(repr(c))
#  for parent in c.is_a:
#    print("    is a %s" % parent)

def recursive(e, depth = 0):
#  global nb
#  nb += 1
  label = e.label
  if label: print("%s%s:%s" % ("  " * depth, e.name, label[0]))
  else:     print("%s%s"    % ("  " * depth, e.name))
  for s in e.subclasses():
    recursive(s, depth + 1)

recursive(obo.GO_0005575)
recursive(obo.GO_0008150)
recursive(obo.GO_0003674)

#go.save("/tmp/t.ntriples", "ntriples")
#go.save("/tmp/t.owl", "rdfxml")

t = time.time() - t
print("List class time %s s." % t, file = sys.stderr)

#default_world.graph.show_profiling()

#print(nb, file = sys.stderr)

#print(obo.GO_0000001)



