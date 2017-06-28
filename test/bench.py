#python ./owlready2/test/bench.py > /dev/null

import sys, time#, cProfile

import owlready2
from owlready2 import *

t = time.time()

default_world.set_backend(filename = "/home/jiba/tmp/go.sqlite")

onto_path.append(os.path.dirname(__file__))
onto_path.append("/home/jiba/telechargements/base_med/")

go = get_ontology("http://purl.obolibrary.org/obo/dron.owl").load()
default_world.save()

t = time.time() - t
print("Load time %s s." % t, file = sys.stderr)


t = time.time()

obo = go.get_namespace("http://purl.obolibrary.org/obo/")

def render(entity):
  label = entity.label.first()
  if label: return "%s:'%s'" % (entity.name, label)
  return entity.name
set_render_func(render)

s = ""
for c in default_world.classes():
  s += repr(c)
  for parent in c.is_a:
    print("    is a %s" % parent)

#go.save("/tmp/t.ntriples", "ntriples")
#go.save("/tmp/t.owl", "rdfxml")

t = time.time() - t
print("List class time %s s." % t, file = sys.stderr)

#print(obo.GO_0000001)



