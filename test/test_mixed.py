from owlready2 import *


onto = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_mixed.owl")


class Parent(Thing):
  namespace = onto
  def test(self): return "ok1"
  def test_inherited(self): return "ok"

class Child(Thing):
  namespace = onto
  def test(self): return "ok2"

