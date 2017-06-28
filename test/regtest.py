
import sys, os, unittest, tempfile, atexit, datetime, rdflib
from io import StringIO, BytesIO
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import owlready2, owlready2.util
from owlready2 import *
from owlready2.base import _universal_abbrev_2_datatype, _universal_datatype_2_abbrev

from owlready2.ntriples_diff import *

set_log_level(0)

next_id = 0

TMPFILES = []
def remove_tmps():
  for f in TMPFILES: os.unlink(f)
atexit.register(remove_tmps)

fileno, filename = tempfile.mkstemp()
TMPFILES.append(filename)
default_world.set_backend(filename = filename)

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
onto_path.append(HERE)
get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()


class BaseTest(object):
  def setUp(self):
    self.nb_triple = len(default_world.graph)
    
  def assert_nb_created_triples(self, x):
    assert (len(default_world.graph) - self.nb_triple) == x
    
  def assert_triple(self, s, p, o, world = default_world):
    if not world.has_triple(s, p, o):
      if not s.startswith("_"): s = world.unabbreviate(s)
      p = world.unabbreviate(p)
      if not (o.startswith("_") or o.startswith('"')): o = world.unabbreviate(o)
      print("MISSING TRIPLE", s, p, o)
      raise AssertionError
    
  def assert_not_triple(self, s, p, o, world = default_world):
    if world.has_triple(s, p, o):
      if not s.startswith("_"): s = world.unabbreviate(s)
      p = world.unabbreviate(p)
      if not (o.startswith("_") or o.startswith('"')): o = world.unabbreviate(o)
      print("UNEXPECTED TRIPLE", s, p, o)
      raise AssertionError

  def assert_ntriples_equivalent(self, nt2, nt1):
    removed, added = diff(nt1, nt2)
    
    for s,p,o, l in removed:
      if l: print("-", s, p, o, ". # line", l)
    for s,p,o, l in added:
      if l: print("+", s, p, o, ". # line", l)
      
    assert not removed
    assert not added

  def new_tmp_file(self):
    fileno, filename = tempfile.mkstemp()
    TMPFILES.append(filename)
    return filename
    
  def new_world(self):
    filename = self.new_tmp_file()
    world = World(filename = filename)
    return world

  def new_ontology(self):
    global next_id
    next_id += 1
    return get_ontology("http://t/o%s#" % next_id)
  
  


class Test(BaseTest, unittest.TestCase):
  def test_environment_1(self):
    e = owlready2.util.Environment()
    assert not e
    with e:
      assert e
      with e:
        assert e
      assert e
    assert not e
    
  def test_namespace_1(self):
    onto = self.new_ontology()
    n1 = onto.get_namespace("http://test/namespace/")
    n2 = onto.get_namespace("http://test/namespace/")
    assert n1 is n2
    
    onto2 = get_ontology(onto.base_iri)
    assert onto is onto2
    
  def test_namespace_2(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert not n.Pizza is None
    assert n.Pizza is n.Pizza
    assert IRIS["http://www.semanticweb.org/jiba/ontologies/2017/0/test#Pizza"] is n.Pizza
    
  def test_namespace_3(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    Pizza = n.Pizza
    iri   = Pizza.storid
    assert Pizza is n.Pizza
    Pizza = None
    import gc
    gc.collect(); gc.collect()
    assert str(iri) in default_world._entities
    assert n.Pizza
    
  def test_namespace_4(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    x = n.Vegetable
    iri = x.storid
    assert x is n.Vegetable
    x = None
    import owlready2.namespace
    owlready2.namespace._cache = [None] * 1000
    import gc
    gc.collect(); gc.collect(); gc.collect()
    #print(gc.get_referrers())
    assert not str(iri) in default_world._entities
    assert not n.Vegetable is None
    
  def test_namespace_5(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza = n.Pizza(name = "pizza_namespace_3")
    assert pizza == n.pizza_namespace_3
    
  def test_namespace_6(self):
    n = self.new_ontology()
    class C(Thing): namespace = n
    assert C == n.C
    
  def test_namespace_7(self):
    o = self.new_ontology()
    n = o.get_namespace("http://test/test_namespace_5.owl")
    class C(Thing): namespace = n
    
    assert C is IRIS["http://test/test_namespace_5.owl#C"]
    
  def test_world_1(self):
    w1 = self.new_world()
    w2 = self.new_world()
    o1 = w1.get_ontology("http://test/test_world_1.owl")
    o2 = w2.get_ontology("http://test/test_world_1.owl")
    assert not w1 is w2
    assert not o1 is o2
    class C(Thing): namespace = o1
    C1 = C
    class C(Thing): namespace = o2
    C2 = C
    assert not C1 is C2
    assert o1.C is C1
    assert o2.C is C2
    
  def test_world_2(self):
    w1 = self.new_world()
    w2 = self.new_world()
    o1 = w1.get_ontology("http://test/test_world_2.owl")
    o2 = w2.get_ontology("http://test/test_world_2.owl")
    with o1:
      class C(Thing): pass
    
    assert C.namespace is o1
    assert C is o1.C
    assert len(w1.graph) > 0
    assert len(o1.graph) > 0
    
  def test_world_3(self):
    w1 = self.new_world()
    w2 = self.new_world()
    o1 = w1.get_ontology("http://test/test_world_3.owl")
    o2 = w2.get_ontology("http://test/test_world_3.owl")
    class C(Thing): namespace = o1
    c1 = C(name = "c1")
    with o2:
      c2 = C(name = "c2")
      
    assert c1.namespace is o1
    assert c1 is o1.c1
    assert c2.namespace is o2
    assert c2 is o2.c2
    assert len(w2.graph) > 0
    assert len(o2.graph) > 0
    
  def test_world_4(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    assert set(world.classes()) == { n.Meat, n.Tomato, n.Eggplant, n.Olive, n.Vegetable, n.NonPizza, n.Pizza, n.Cheese, n.VegetarianPizza, n.Topping }
    assert set(world.data_properties()) == { n.price }
    assert set(world.object_properties()) == { n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of }
    assert set(world.annotation_properties()) == { n.annot }
    assert set(world.properties()) == { n.price, n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of, n.annot }
    assert set(world.individuals()) == { n.mon_frometon, n.ma_tomate, n.ma_pizza }
    
  def test_world_5(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    world.set_backend(filename = ":memory:")
    assert set(world.classes()) == { n.Meat, n.Tomato, n.Eggplant, n.Olive, n.Vegetable, n.NonPizza, n.Pizza, n.Cheese, n.VegetarianPizza, n.Topping }
    assert set(world.data_properties()) == { n.price }
    assert set(world.object_properties()) == { n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of }
    assert set(world.annotation_properties()) == { n.annot }
    assert set(world.properties()) == { n.price, n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of, n.annot }
    assert set(world.individuals()) == { n.mon_frometon, n.ma_tomate, n.ma_pizza }
    
  def test_world_6(self):
    world = self.new_world()
    o1 = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    o2 = get_ontology("http://test/test_ontology_1_1.owl")
    o3 = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_reasoning.owl").load()
    
  def test_world_7(self):
    world = self.new_world()
    o = world.get_ontology("http://test.org/t.owl")
    A = world.abbreviate("http://test.org/t.owl#A")
    B = world.abbreviate("http://test.org/t.owl#B")
    o.add_triple(A, rdf_type, owl_class)
    #missing triple (B, rdf_type, owl_class)
    o.add_triple(A, rdfs_subclassof, B)
    
    assert isinstance(o.A, ThingClass)
    assert o.B in o.A.is_a
    
    
  def test_ontology_1(self):
    o1 = get_ontology("http://test/test_ontology_1_1.owl")
    o2 = get_ontology("http://test/test_ontology_1_2.owl")
    class C(Thing): namespace = o1
    c1 = C(name = "c1")
    with o2:
      c2 = C(name = "c2")
      
    assert c1.namespace is o1
    assert c1 is o1.c1
    assert c2.namespace is o2
    assert c2 is o2.c2
    assert len(o2.graph) > 0
    
  def test_ontology_2(self):
    w  = self.new_world()
    o1 = w.get_ontology("http://test/test_ontology_2_1.owl")
    o2 = w.get_ontology("http://test/test_ontology_2_2.owl")
    with o1:
      class prop(DataProperty, FunctionalProperty): pass
      class C(Thing): pass
      c1 = C(name = "c1")
    with o2:
      c1.prop = 1
      
    assert len(o2.graph) == 2
    self.assert_triple(c1.storid, prop.storid, to_literal(1), o2)
    
  def test_ontology_3(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    assert set(n.classes()) == { n.Meat, n.Tomato, n.Eggplant, n.Olive, n.Vegetable, n.NonPizza, n.Pizza, n.Cheese, n.VegetarianPizza, n.Topping }
    assert set(n.data_properties()) == { n.price }
    assert set(n.object_properties()) == { n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of }
    assert set(n.annotation_properties()) == { n.annot }
    assert set(n.properties()) == { n.price, n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of, n.annot }
    assert set(n.individuals()) == { n.mon_frometon, n.ma_tomate, n.ma_pizza }
    
  def test_ontology_4(self):
    world = self.new_world()
    n = world.get_ontology("test").load()
    
    assert n.base_iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#"
    assert set(n.classes()) == { n.Meat, n.Tomato, n.Eggplant, n.Olive, n.Vegetable, n.NonPizza, n.Pizza, n.Cheese, n.VegetarianPizza, n.Topping }
    assert n.Tomato.iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#Tomato"
    
  def test_ontology_5(self):
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "test.owl"))
    
    onto_path_save = onto_path[:]
    for i in onto_path: onto_path.remove(i)
    
    try:
      world = self.new_world()
      n = world.get_ontology("file://" + filename).load()
      
      assert n.base_iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#"
      assert set(n.classes()) == { n.Meat, n.Tomato, n.Eggplant, n.Olive, n.Vegetable, n.NonPizza, n.Pizza, n.Cheese, n.VegetarianPizza, n.Topping }
      assert n.Tomato.iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#Tomato"
      
    finally:
      onto_path.extend(onto_path_save)
      
  def test_ontology_6(self):
    world = self.new_world()
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "test.owl"))
    n1 = world.get_ontology("file://" + filename).load()
    nb_triple = len(world.graph)
    
    n2 = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    assert n2 is n1
    assert len(world.graph) == nb_triple
    
  def test_ontology_7(self):
    w = self.new_world()
    o = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    assert o._parse_bnode(o.NonPizza.is_a[-1].storid) is o.NonPizza.is_a[-1]
    
      
  def test_class_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert issubclass(n.Tomato, n.Vegetable)
    assert issubclass(n.Vegetable, n.Topping)
    assert issubclass(n.Tomato, n.Topping)
    assert issubclass(n.Topping, Thing)
    
  def test_class_2(self):
    n = self.new_ontology()
    class C(Thing): namespace = n
    
    self.assert_nb_created_triples(3)
    self.assert_triple(C.storid, rdf_type, owl_class)
    self.assert_triple(C.storid, rdfs_subclassof, Thing.storid)
    
  def test_class_3(self):
    n = self.new_ontology()
    class C1(Thing):  namespace = n
    class C2(Thing):  namespace = n
    class C3(C1, C2): namespace = n
    
    #for p, o in g.predicate_objects(C3.storid): print(p, o)
    
    self.assert_nb_created_triples(1 + 2 + 2 + 3)
    self.assert_triple(C3.storid, rdf_type, owl_class)
    self.assert_triple(C3.storid, rdfs_subclassof, C1.storid)
    self.assert_triple(C3.storid, rdfs_subclassof, C2.storid)
    
  def test_class_4(self):
    n = self.new_ontology()
    class C1(Thing):  namespace = n
    class C2(Thing):  namespace = n
    class C3(C1): namespace = n
    
    C3.is_a.append(C2)
    
    self.assert_triple(C3.storid, rdfs_subclassof, C1.storid)
    self.assert_triple(C3.storid, rdfs_subclassof, C2.storid)
    assert issubclass(C3, C1)
    assert issubclass(C3, C2)
    
  def test_class_5(self):
    n = self.new_ontology()
    class C1(Thing):  namespace = n
    class C2(Thing):  namespace = n
    class C3(C1, C2): namespace = n
    
    C3.is_a.remove(C1)
    
    self.assert_not_triple(C3.storid, rdfs_subclassof, C1.storid)
    self.assert_triple    (C3.storid, rdfs_subclassof, C2.storid)
    assert not issubclass(C3, C1)
    assert issubclass(C3, C2)
    
  def test_class_6(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing):
      namespace = n
      is_a = [C1]
      
    assert issubclass(C2, C1)
    self.assert_triple(C2.storid, rdfs_subclassof, C1.storid)
    
  def test_class_7(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(C1): pass
    
    assert issubclass(C2, C1)
    self.assert_triple(C2.storid, rdfs_subclassof, C1.storid)
    
  def test_class_8(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert set(n.Pizza.instances()) == { n.ma_pizza }
    assert set(n.Topping.descendants(include_self = False)) == { n.Cheese, n.Meat, n.Vegetable, n.Olive, n.Tomato, n.Eggplant }
    assert set(n.Topping.descendants()) == { n.Topping, n.Cheese, n.Meat, n.Vegetable, n.Olive, n.Tomato, n.Eggplant }
    assert set(n.Tomato.ancestors(include_self = False)) == { n.Vegetable, n.Topping, Thing }
    assert set(n.Tomato.ancestors()) == { n.Tomato, n.Vegetable, n.Topping, Thing }
    
  def test_class_9(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class D(Thing): pass
      class D2(D): pass
      
      C.equivalent_to.append(D)
      
    assert set(C .descendants()) == { C, C2, D, D2 }
    assert set(C2.descendants()) == { C2 }
    assert set(D .descendants()) == { C, C2, D, D2 }
    assert set(D2.descendants()) == { D2 }
    
  def test_class_10(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class D(Thing): pass
      class D2(D): pass
      
      D.equivalent_to # Read and define it
      C.equivalent_to.append(D)
      
    assert set(C .descendants()) == { C, C2, D, D2 }
    assert set(C2.descendants()) == { C2 }
    assert set(D .descendants()) == { C, C2, D, D2 }
    assert set(D2.descendants()) == { D2 }
    
  def test_class_11(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class D(Thing):
        equivalent_to = [C2]
        
    assert set(C .descendants()) == { C, C2, D }
    assert set(C2.descendants()) == { C2, D }
    assert set(D .descendants()) == { C2, D }
    
  def test_class_12(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class D(Thing):
        equivalent_to = [C]
      class D2(D): pass
      
    assert set(D2.ancestors()) == { D2, D, C, Thing }
    assert set(C2.ancestors()) == { C2, D, C, Thing }
    
  def test_class_13(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing):
        equivalent_to = [C]
      class E(Thing):
        equivalent_to = [D]
        
    assert set(C.equivalent_to) == { D, E }
    assert set(D.equivalent_to) == { C, E }
    assert set(E.equivalent_to) == { C, D }
    assert set(C.descendants()) == { C, D, E }
    assert set(C.ancestors()) == { C, D, E, Thing }
    
  def test_class_14(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing):
        equivalent_to = [C]
      class C2(C): pass
      class D2(D): pass
      
    assert issubclass(C2, C)
    assert issubclass(D2, D)
    assert issubclass(C2, D)
    assert issubclass(D2, C)
    assert issubclass(C, D)
    assert issubclass(D, C)
    assert not issubclass(C2, D2)
    assert not issubclass(D2, C2)
    
  def test_class_15(self): # Test MRO errors
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class D(Thing): pass
      
      class T(D, C2, C, Thing): pass
      class T(D, C, C2, Thing): pass
    
  def test_class_16(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class E(Thing): pass
      
      C.equivalent_to.append(D)
      E.equivalent_to.append(D)
      
    assert set(C.equivalent_to) == { D, E }
    assert set(D.equivalent_to) == { C, E }
    assert set(E.equivalent_to) == { C, D }
    
  def test_class_17(self): # test MRO
    n = self.new_ontology()
    with n:
      class GO_0044464(Thing): pass
      class GO_0044422(Thing): pass
      class GO_0044424(GO_0044464): pass
      class GO_0044446(GO_0044422, GO_0044424): pass
      class GO_0016020(GO_0044464): pass
      class GO_0031090(GO_0016020, GO_0044422): pass
      class X(GO_0044446, GO_0031090): pass
      class X(GO_0031090, GO_0044446): pass
      
  def test_class_18(self):
    world = self.new_world()
    n     = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    a     = n.Topping
    b     = n.Tomato
    
    assert set(n.Topping.descendants(only_loaded = True)) == { n.Topping, n.Vegetable, n.Tomato }
    
  def test_class_19(self):
    world = self.new_world()
    n     = world.get_ontology("http://test.org/test")
    
    with n:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class M(Thing):
        is_a = [
          p.some(A),
          B & C
          ]

    assert set(A.constructs()) == { M.is_a[-2] }
    assert set(B.constructs()) == { M.is_a[-1] }
    assert set(C.constructs()) == { M.is_a[-1] }
    
  def test_class_20(self):
    world = self.new_world()
    n     = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()

    n.Pizza # Loads Pizza
    nb = len(world._entities)
    
    with n:
      class Pizza(Thing):
        def f(self): pass
        
    assert len(world._entities) == nb # Check that the redefinition did not load additional classes
    
    
  def test_individual_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert isinstance(n.ma_tomate, n.Tomato)
    assert isinstance(n.ma_tomate, n.Vegetable)
    assert isinstance(n.ma_tomate, n.Topping)
    assert isinstance(n.ma_tomate, Thing)
    assert not isinstance(n.ma_tomate, n.Pizza)
    assert not isinstance(None, n.Pizza)
    assert not isinstance(1, n.Pizza)
    
  def test_individual_2(self):
    n = self.new_ontology()
    class C(Thing): namespace = n
    i = C()
    
    self.assert_nb_created_triples(5)
    self.assert_triple(i.storid, rdf_type, owl_named_individual)
    self.assert_triple(i.storid, rdf_type, C.storid)
    
  def test_individual_3(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing): namespace = n
    i = C1()
    
    i.is_a = [C2]
    
    self.assert_not_triple(i.storid, rdf_type, C1.storid)
    self.assert_triple    (i.storid, rdf_type, C2.storid)
    
  def test_individual_4(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing): namespace = n
    i = C1()
    
    i.is_a.append(C2)
    
    self.assert_triple(i.storid, rdf_type, C1.storid)
    self.assert_triple(i.storid, rdf_type, C2.storid)
    assert "_AND_" in i.__class__.__name__
    
  def test_individual_5(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing): namespace = n
    i = C1()
    
    i.is_a.remove(C1)
    
    self.assert_not_triple(i.storid, rdf_type, C1.storid)
    self.assert_not_triple(i.storid, rdf_type, C2.storid)
    assert i.__class__ is Thing
    
  def test_individual_6(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      
    i1 = C()
    i2 = C()
    
    assert i1.storid != i2.storid
    
    i1.equivalent_to.append(i2)
    
    assert set(i2.equivalent_to) == { i1 }
    
    i2.equivalent_to.remove(i1)
    assert set(i2.equivalent_to) == set()
    assert set(i1.equivalent_to) == set()
    
  def test_individual_7(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
    i1 = C()
    i2 = C()
    i3 = C()
    i4 = C()
    
    i1.equivalent_to.append(i2)
    i2.equivalent_to.append(i3)
    i3.equivalent_to.append(i4)
    
    assert set(i1.equivalent_to) == { i2, i3, i4 }
    assert set(i2.equivalent_to) == { i1, i3, i4 }
    assert set(i3.equivalent_to) == { i1, i2, i4 }
    assert set(i4.equivalent_to) == { i1, i2, i3 }
    
  def test_individual_8(self):
    n = self.new_ontology()
    with n:
      class C (Thing): pass
      class C1(C): pass
      class D (Thing):
        equivalent_to = [C]
      class D1(D): pass
      class E (Thing): pass
    i = C()
    
    assert isinstance(i, C)
    assert isinstance(i, D)
    assert not isinstance(i, C1)
    assert not isinstance(i, D1)
    assert not isinstance(i, E)
    
  def test_individual_9(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class prop(ObjectProperty): pass
      class propf(ObjectProperty, FunctionalProperty): pass
      class propi(DataProperty): range = [int]
      class propif(DataProperty, FunctionalProperty): range = [int]
    d1 = D()
    d2 = D()
    d3 = D()
    c = C("mon_c", prop = [d1, d2], propf = d3, propi = [1, 2], propif = 3)
    
    assert c.name == "mon_c"
    self.assert_triple(d1.storid, rdf_type, D.storid)
    self.assert_triple(c.storid, rdf_type, C.storid)
    self.assert_triple(c.storid, prop.storid, d1.storid)
    self.assert_triple(c.storid, propf.storid, d3.storid)
    self.assert_triple(c.storid, propi.storid, to_literal(1))
    self.assert_triple(c.storid, propi.storid, to_literal(2))
    self.assert_triple(c.storid, propif.storid, to_literal(3))
    
  def test_individual_10(self):
    world   = self.new_world()
    onto    = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_reasoning.owl").load()
    
    assert len(onto.pizza_tomato.is_a) == 2
    
  def test_prop_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert "has_topping" in default_world._props
    assert "price" in default_world._props
    assert default_world._props["has_topping"] is n.has_topping
    assert default_world._props["price"] is n.price
    assert n.has_topping.__class__ is ObjectPropertyClass
    assert n.price.__class__ is DataPropertyClass
    assert n.has_topping.__bases__ == (ObjectProperty,)
    assert set(n.price.__bases__) == { DataProperty, FunctionalProperty }
    
  def test_prop_2(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert set(n.ma_pizza.has_topping) == { n.ma_tomate, n.mon_frometon }
    
  def test_prop_3(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert n.ma_pizza.price == 9.9

  def test_prop_4(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza = n.Pizza()
    assert pizza.has_topping == []
    assert pizza.price is None
    
  def test_prop_5(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza = n.Pizza()
    assert default_world.get_triple_sp(pizza.storid, n.price.storid) is None
    pizza.price = 8.0

    assert from_literal(default_world.get_triple_sp(pizza.storid, n.price.storid)) == 8.0
    pizza.price = 9.0
    assert from_literal(default_world.get_triple_sp(pizza.storid, n.price.storid)) == 9.0
    pizza.price = None
    assert default_world.get_triple_sp(pizza.storid, n.price.storid) is None
    
  def test_prop_6(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza = n.Pizza()
    assert pizza.has_topping == []
    tomato = n.Tomato()
    cheese = n.Cheese()
    pizza.has_topping = [tomato]
    assert default_world.get_triple_sp(pizza.storid, n.has_topping.storid) == tomato.storid
    pizza.has_topping.append(cheese)
    self.assert_triple(pizza.storid, n.has_topping.storid, tomato.storid)
    self.assert_triple(pizza.storid, n.has_topping.storid, cheese.storid)
    pizza.has_topping.remove(tomato)
    assert default_world.get_triple_sp(pizza.storid, n.has_topping.storid) == cheese.storid
    
  def test_prop_7(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class prop (DataProperty): pass
      class propf(DataProperty, FunctionalProperty): pass
    c = C()
    c.prop  = [0, 1]
    c.propf = 2
    
    self.assert_triple(c.storid, prop .storid, to_literal(0))
    self.assert_triple(c.storid, prop .storid, to_literal(1))
    self.assert_triple(c.storid, propf.storid, to_literal(2))
    
  def test_prop_8(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    
    assert n.has_topping.domain == [n.Pizza]
    assert n.has_topping.range  == [n.Topping]
    
    assert n.price.domain == [n.Pizza]
    assert n.price.range  == [float]
    
  def test_prop_9(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class prop(DataProperty):
        range = [int]
        
    self.assert_triple(prop.storid, rdf_range, n.abbreviate("http://www.w3.org/2001/XMLSchema#integer"))
    assert isinstance(prop.range, util.CallbackList)
    
    prop.range.append(float)
    self.assert_triple(prop.storid, rdf_range, n.abbreviate("http://www.w3.org/2001/XMLSchema#decimal"))
    
    prop.range.remove(int)
    self.assert_not_triple(prop.storid, rdf_range, n.abbreviate("http://www.w3.org/2001/XMLSchema#integer"))
    
  def test_prop_10(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(Thing): pass
      class prop(ObjectProperty):
        domain = [C1]
        
    self.assert_triple(prop.storid, rdf_domain, C1.storid)
    assert isinstance(prop.domain, util.CallbackList)
    
    prop.domain = [C2]
    self.assert_triple    (prop.storid, rdf_domain, C2.storid)
    self.assert_not_triple(prop.storid, rdf_domain, C1.storid)
    
  def test_prop_11(self):
    n = self.new_ontology()
    with n:
      class D (Thing): pass
      class R (Thing): pass
      class prop(ObjectProperty):
        domain = [D]
        range  = [R]
      class D2(Thing):
        is_a = [prop.max(1, R)]
        
    d  = D()
    d2 = D2()

    assert d .prop == []
    assert d2.prop == None
    
  def test_prop_12(self):
    n = self.new_ontology()
    with n:
      class prop1(ObjectProperty): pass
      class prop2(prop1): pass
      
    self.assert_triple(prop2.storid, rdfs_subpropertyof, prop1.storid)
    
  def test_prop_13(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class prop(DataProperty):
        range = [str]
        
    c1 = C()
    c1.prop = [locstr("English", "en"), locstr("Français", "fr")]
    assert c1.prop.fr == ["Français"]
    
    c1.prop.fr.append("French")
    c1.prop.en = "Anglais"
    
    values = set()
    for s,p,o in n.get_triples(c1.storid, prop.storid, None): values.add(o)
    assert values == { to_literal(locstr("Anglais", "en")), to_literal(locstr("French", "fr")), to_literal(locstr("Français", "fr")) }
    
  def test_prop_14(self):
    w = self.new_world()
    n = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    assert set(n.ma_pizza ._get_instance_possible_relations()) == { n.has_main_topping, n.has_topping, n.price }
    assert set(n.Topping()._get_instance_possible_relations()) == { n.main_topping_of, n.topping_of }
    
  def test_prop_15(self):
    n = self.new_ontology()
    with n:
      class prop1(DataProperty): pass
      class prop2(ObjectProperty): pass
      class prop3(ObjectProperty, FunctionalProperty): pass
      class prop4(AnnotationProperty): pass
      class prop5(prop2): pass
      
    def get_types(prop):
      for s,p,o in n.get_triples(prop.storid, rdf_type, None): yield o
      
    assert set(get_types(prop1)) == { owl_data_property }
    assert set(get_types(prop2)) == { owl_object_property }
    assert set(get_types(prop3)) == { owl_object_property, n.abbreviate("http://www.w3.org/2002/07/owl#FunctionalProperty") }
    assert set(get_types(prop4)) == { owl_annotation_property }
    assert set(get_types(prop5)) == { owl_object_property }
    
    def get_subclasses(prop):
      for s,p,o in n.get_triples(prop.storid, rdfs_subpropertyof, None): yield o
      
    assert set(get_subclasses(prop1)) == set()
    assert set(get_subclasses(prop2)) == set()
    assert set(get_subclasses(prop3)) == set()
    assert set(get_subclasses(prop4)) == set()
    assert set(get_subclasses(prop5)) == { prop2.storid }
    
  def test_prop_16(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class prop1(C >> D): pass
      class prop2(C >> D, FunctionalProperty): pass
      class prop3(C >> int): pass
      class prop4(ObjectProperty): pass
      
    assert (prop1.domain, prop1.range) == ([C], [D])
    assert (prop2.domain, prop2.range) == ([C], [D])
    assert (prop3.domain, prop3.range) == ([C], [int])
    assert (prop4.domain, prop4.range) == ([ ], [ ])
    assert issubclass(prop2, FunctionalProperty)
    
  def test_prop_17(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class prop1(C >> D): pass
      class prop2(prop1): pass
      
    assert prop1.domain == [C]
    assert prop1.range  == [D]
    assert prop2.domain == []
    assert prop2.range  == []
    
  def test_prop_18(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/t")
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class has_prop(C >> D): pass
      
    c = C()
    assert c.has_prop == []
    assert not hasattr(c, "props")
    
    has_prop.python_name = "props"
    self.assert_triple(has_prop.storid, owlready_python_name, to_literal("props"), w)
    
    c = C()
    assert c.props == []
    assert not hasattr(c, "has_prop")
    
  def test_prop_19(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/t")
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class has_prop(C >> D):
        python_name = "props"
        
    c = C()
    assert c.props == []
    assert not hasattr(c, "has_prop")
    
    self.assert_triple(has_prop.storid, owlready_python_name, to_literal("props"), w)
    
  def test_prop_20(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class p(C >> D): pass
      
      C.is_a.append(p.exactly(1))
      
    assert p.is_functional_for(C)
    
  def test_prop_21(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class p(C >> C): pass
      
      C.is_a.append(p.exactly(1, C))
      
    assert p.is_functional_for(C)
    assert p.is_functional_for(C2)
    
  def test_prop_22(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class p(C >> C): pass
      
      C.is_a.append(p.max(1, C2))
      
    assert not p.is_functional_for(C)
    assert not p.is_functional_for(C2)
    
  def test_prop_23(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class C2(C): pass
      class p(C >> C): pass
      
    assert not p.is_functional_for(C)
    assert not p.is_functional_for(C2)
    assert C().p == []
    
    C.is_a.append(p.max(1, C))
    
    assert p.is_functional_for(C)
    assert p.is_functional_for(C2)
    assert C().p == None
    
    del C.is_a[-1]
    
    assert not p.is_functional_for(C)
    assert not p.is_functional_for(C2)
    assert C().p == []
    
    C2.is_a.append(p.max(1, C))
    
    assert not p.is_functional_for(C)
    assert p.is_functional_for(C2)
    assert C ().p == []
    assert C2().p == None
    
  def test_prop_24(self):
    n = self.new_ontology()
    with n:
      class p(ObjectProperty): pass
      class p2(p): pass
      class d(DataProperty): pass
      class d2(d): pass
      
    p2.is_a.remove(p)
    d2.is_a.remove(d)
    
    assert p2.is_a == [ObjectProperty]
    assert d2.is_a == [DataProperty]
    
  def test_prop_24(self):
    ok = False
    try:
      o = get_ontology("test_multiple_base_prop.owl").load()
      o.bug_database
    except TypeError:
      ok = True
    assert ok
    
    
  def test_prop_inverse_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert n.price.inverse_property is None
    assert n.has_topping.inverse_property is n.topping_of
    assert n.topping_of.inverse_property is n.has_topping
    
  def test_prop_inverse_2(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert n.ma_tomate.topping_of      == [n.ma_pizza]
    assert n.ma_tomate.main_topping_of == [n.ma_pizza]
    
  def test_prop_inverse_3(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza  = n.Pizza()
    pizza2 = n.Pizza()
    tomato = n.Tomato()
    pizza.has_topping = [tomato]
    assert tomato.topping_of == [pizza]
    pizza2.has_topping.append(tomato)
    assert set(tomato.topping_of) == { pizza, pizza2 }
    tomato.topping_of.remove(pizza)
    assert pizza.has_topping == []
    
  def test_prop_inverse_4(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza  = n.Pizza()
    pizza2 = n.Pizza()
    tomato = n.Tomato()
    pizza.has_main_topping = tomato
    assert tomato.main_topping_of == [pizza]
    tomato.main_topping_of.append(pizza2)
    assert pizza2.has_main_topping is tomato
    tomato.main_topping_of.remove(pizza)
    assert pizza.has_main_topping is None
    
  def test_prop_inverse_5(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza  = n.Pizza()
    pizza2 = n.Pizza()
    tomato = n.Tomato()
    pizza.has_main_topping = tomato
    assert tomato.main_topping_of == [pizza]
    pizza.has_main_topping = None
    assert tomato.main_topping_of == []
    
  def test_prop_inverse_6(self):
    n = self.new_ontology()
    class C(Thing): namespace = n
    class prop (ObjectProperty): namespace = n
    class iprop(ObjectProperty): namespace = n
    iprop.inverse_property # Load it
    prop.inverse_property = iprop
    self.assert_triple(prop.storid, owl_inverse_property, iprop.storid)
    
    c1 = C()
    c2 = C()
    c1.prop = [c2]
    assert iprop.inverse_property == prop
    assert c2.iprop == [c1]
    
  def test_prop_inverse_7(self):
    n = self.new_ontology()
    class C(Thing): namespace = n
    class prop (ObjectProperty): namespace = n
    class iprop(ObjectProperty):
      namespace = n
      inverse_property = prop
    self.assert_triple(iprop.storid, owl_inverse_property, prop.storid)
    
    c1 = C()
    c2 = C()
    c1.prop = [c2]
    assert iprop.inverse_property == prop
    assert c2.iprop == [c1]
    
  def test_construct_not_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert n.NonPizza.__bases__ == (Thing,)
    for p in n.NonPizza.is_a:
      if isinstance(p, ClassConstruct):
        assert p.__class__ is Not
        assert p.Class is n.Pizza
        break
    else: assert False
    self.assert_nb_created_triples(0)
    
  def test_construct_not_2(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing):
      namespace = n
      is_a      = [Not(C1)]
      
    for p in C2.is_a:
      if isinstance(p, ClassConstruct): bnode = p.storid; break
      
    self.assert_triple(bnode, rdf_type, owl_class)
    self.assert_triple(bnode, owl_complementof, C1.storid)
    
  def test_construct_not_3(self):
    n = self.new_ontology()
    class C1 (Thing): namespace = n
    class C1b(Thing): namespace = n
    class C2 (Thing):
      namespace = n
      is_a      = [Not(C1)]
      
    for p in C2.is_a:
      if isinstance(p, ClassConstruct): bnode = p.storid; break
      
    p.Class = C1b
    
    self.assert_triple    (bnode, rdf_type, owl_class)
    self.assert_triple    (bnode, owl_complementof, C1b.storid)
    self.assert_not_triple(bnode, owl_complementof, C1.storid)

  def test_construct_not_4(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing): namespace = n
    class C3(Thing): namespace = n
    
    NOT = Not(C1)
    C2.is_a.append(NOT)
    self.assert_triple(NOT.storid, rdf_type, owl_class)
    self.assert_triple(NOT.storid, owl_complementof, C1.storid)
    self.assert_triple(C2.storid, rdfs_subclassof, NOT.storid)
    
    ok = 0
    try: C3.is_a.append(NOT)
    except OwlReadySharedBlankNodeError: ok = 1
    assert ok
    
  def test_construct_restriction_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    assert len(n.VegetarianPizza.is_a) == 2
    for p in n.VegetarianPizza.is_a:
      if isinstance(p, Not): r = p.Class; break
    assert isinstance(r, Restriction)
    assert r.type  == SOME
    assert r.property == n.has_topping
    assert r.value == n.Meat
    assert r.cardinality is None
    assert len(list(default_world.get_triples(r.storid, None, None))) == 3
    
  def test_construct_restriction_2(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing): namespace = n
    class C3(Thing): namespace = n
    class P1(ObjectProperty): namespace = n
    class P2(ObjectProperty): namespace = n
    
    C1.is_a.append(P1.only(C2))
    
    r     = C1.is_a[-1]
    bnode = r.storid
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P1.storid)
    self.assert_triple(bnode, ONLY, C2.storid)
    assert len(list(default_world.get_triples(bnode, None, None))) == 3
    
    r.value = C3
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P1.storid)
    self.assert_triple(bnode, ONLY, C3.storid)
    assert len(list(default_world.get_triples(bnode, None, None))) == 3
    
    r.property = P2
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, ONLY, C3.storid)
    assert len(list(default_world.get_triples(bnode, None, None))) == 3
    
    r.type        = EXACTLY
    r.cardinality = 2
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C3.storid)
    self.assert_triple(bnode, EXACTLY, '"2"^%s' % n.abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 4
    
    r.type        = MIN
    r.cardinality = 3
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C3.storid)
    self.assert_triple(bnode, MIN, '"3"^%s' % n.abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 4
    
    r.value = None
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_min_cardinality, '"3"^%s' % n.abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 3
    
    r.type = MAX
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_max_cardinality, '"3"^%s' % n.abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 3
    
    r.value = C2
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C2.storid)
    self.assert_triple(bnode, MAX, '"3"^%s' % n.abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 4
    
    r.type = EXACTLY
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C2.storid)
    self.assert_triple(bnode, EXACTLY, '"3"^%s' % n.abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 4
    
    #for i in g.predicate_objects(bnode): print(i)
    
  def test_construct_restriction_3(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing): namespace = n
    class P(ObjectProperty): namespace = n
    
    c1 = C1()
    c1.is_a.append(P.some(C2))
    
    r     = c1.is_a[-1]
    bnode = r.storid
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P.storid)
    self.assert_triple(bnode, SOME, C2.storid)
    
  def test_construct_restriction_4(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class P1(DataProperty): namespace = n
    
    C1.is_a.append(P1.only(int))
    
    r     = C1.is_a[-1]
    bnode = r.storid
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P1.storid)
    self.assert_triple(bnode, ONLY, n.abbreviate("http://www.w3.org/2001/XMLSchema#integer"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 3
    
    r.value       = float
    r.type        = EXACTLY
    r.cardinality = 5
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P1.storid)
    self.assert_triple(bnode, EXACTLY, '"5"^%s' % n.abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    self.assert_triple(bnode, owl_ondatarange, n.abbreviate("http://www.w3.org/2001/XMLSchema#decimal"))
    assert len(list(default_world.get_triples(bnode, None, None))) == 4

    
  def test_and_or_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    
    assert len(n.Vegetable.is_a) == 2
    assert isinstance(n.Vegetable.is_a[-1], Or)
    assert set(n.Vegetable.is_a[-1].Classes) == { n.Tomato, n.Eggplant, n.Olive }
    
  def test_and_or_2(self):
    n = self.new_ontology()
    class C1(Thing): namespace = n
    class C2(Thing): namespace = n
    class C3(Thing): namespace = n
    class C4(Thing): namespace = n
    
    C1.is_a.append(C2 | C3)
    c = C1.is_a[-1]
    assert isinstance(c, Or)
    assert len(c.Classes) == 2
    assert set(c.Classes) == { C2, C3 }
    self.assert_triple(c.storid, rdf_type, owl_class)
    self.assert_triple(c.storid, owl_unionof, c._list_bnode)
    assert set(n._parse_list(c._list_bnode)) == { C2, C3 }
    
    c.Classes.append(C4)
    assert len(c.Classes) == 3
    assert set(c.Classes) == { C2, C3, C4 }
    self.assert_triple(c.storid, rdf_type, owl_class)
    self.assert_triple(c.storid, owl_unionof, c._list_bnode)
    assert set(n._parse_list(c._list_bnode)) == { C2, C3, C4 }
    
    c.Classes.remove(C3)
    assert len(c.Classes) == 2
    assert set(c.Classes) == { C2, C4 }
    self.assert_triple(c.storid, rdf_type, owl_class)
    self.assert_triple(c.storid, owl_unionof, c._list_bnode)
    assert set(n._parse_list(c._list_bnode)) == { C2, C4 }
    
  def test_and_or_3(self):
    n = self.new_ontology()
    with n:
      class p(DataProperty): pass
      class C(Thing):
        is_a = [p.some(Or([int, float]))]
        
    bnode = C.is_a[-1].value.storid
    self.assert_triple(bnode, rdf_type, rdfs_datatype)
    
  def test_and_or_4(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C1(Thing): pass
      class C2(Thing): pass
      class C3(Thing): pass
      
    assert repr(C1 | C2 | C3) == "test.C1 | test.C2 | test.C3"
    assert repr(C1 & C2 & C3) == "test.C1 & test.C2 & test.C3"
    
    
  def test_one_of_1(self):
    n = self.new_ontology()
    class C(Thing): namespace = n
    c1 = C()
    c2 = C()
    c3 = C()
    oneof = OneOf([c1, c2, c3])
    C.is_a.append(oneof)
    self.assert_triple(C.storid, rdfs_subclassof, oneof.storid)
    self.assert_triple(oneof.storid, owl_oneof, oneof._list_bnode)
    assert n._parse_list(oneof._list_bnode) == [c1, c2, c3]
    
  def test_method_1(self):
    n = self.new_ontology()
    ok = []
    class C1(Thing):
      namespace = n
      def test(self): ok.append(1)

    C1().test()
    assert ok
    
  def test_method_2(self):
    n = self.new_ontology()
    ok = []
    class C1(Thing):
      namespace = n
      def test(self): pass
    class C2(C1):
      namespace = n
      def test(self): ok.append(1)
      
    C2().test()
    assert ok
    
  def test_reasoning_1(self):
    world   = self.new_world()
    onto    = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_reasoning.owl").load()
    results = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_reasoning_reasoning.owl")
    with results:
      sync_reasoner(world, debug = 0)
      
    assert len(results.graph) == 4

    self.assert_triple(onto.VegetalianPizza.storid, rdfs_subclassof, onto.VegetarianPizza.storid, world)
    self.assert_triple(onto.pizza_tomato.storid, rdf_type, onto.VegetalianPizza.storid, world)
    self.assert_triple(onto.pizza_tomato_cheese.storid, rdf_type, onto.VegetarianPizza.storid, world)
    
    assert onto.VegetarianPizza in onto.VegetalianPizza.__bases__
    assert onto.pizza_tomato.__class__ is onto.VegetalianPizza
    assert onto.pizza_tomato_cheese.__class__ is onto.VegetarianPizza
    
  def test_reasoning_2(self):
    world = self.new_world()
    onto  = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_reasoning.owl").load()
    
    # Store them in memory
    entities = [onto.VegetalianPizza, onto.VegetarianPizza, onto.pizza_tomato, onto.pizza_tomato_cheese, onto.pizza_tomato_meat] 
    sync_reasoner(world, debug = 0)
    
    assert entities == [onto.VegetalianPizza, onto.VegetarianPizza, onto.pizza_tomato, onto.pizza_tomato_cheese, onto.pizza_tomato_meat] 
    assert onto.VegetarianPizza in onto.VegetalianPizza.__bases__
    assert onto.pizza_tomato.__class__ is onto.VegetalianPizza
    assert onto.pizza_tomato_cheese.__class__ is onto.VegetarianPizza
    
    
  def test_disjoint_1(self):
    world = self.new_world()
    n     = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_reasoning.owl").load()
    assert len(list(n.disjoints())) == 1
    assert set(list(n.disjoints())[0].entities) == { n.Cheese, n.Meat, n.Vegetable }
    
  def test_disjoint_2(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(Thing): pass
      class C3(Thing): pass
      d = AllDisjoint([C1, C2])
      
    assert not d._list_bnode
    self.assert_triple(C1.storid, owl_disjointwith, C2.storid)
    
    d.entities.append(C3)
    
    self.assert_not_triple(C1.storid, owl_disjointwith, C2.storid)
    assert set(n._parse_list(d._list_bnode)) == { C1, C2, C3 }
    
  def test_disjoint_3(self):
    n = self.new_ontology()
    with n:
      class P1(ObjectProperty): pass
      class P2(ObjectProperty): pass
      class P3(ObjectProperty): pass
      d = AllDisjoint([P1, P2])
      
    assert not d._list_bnode
    self.assert_triple(P1.storid, owl_propdisjointwith, P2.storid)
    
    d.entities.append(P3)
    
    self.assert_not_triple(P1.storid, owl_disjointwith, P2.storid)
    assert set(n._parse_list(d._list_bnode)) == { P1, P2, P3 }
    
  def test_disjoint_4(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      c1 = C()
      c2 = C()
      c3 = C()
      d = AllDisjoint([c1, c2])
      
    assert set(n._parse_list(d._list_bnode)) == { c1, c2 }
    
    d.entities.append(c3)
    
    assert set(n._parse_list(d._list_bnode)) == { c1, c2, c3 }
    
  def test_disjoint_5(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class E(Thing): pass
      class F(Thing): pass
      class G(Thing): pass
      AllDisjoint([C, D])
      AllDisjoint([C, E, F])
      AllDisjoint([G, F])
      AllDisjoint([E, F, G])
      
    s = set(frozenset(d.entities) for d in C.disjoints())
    assert s == { frozenset([C, D]), frozenset([C, E, F]) }
    
  def test_disjoint_6(self):
    n = self.new_ontology()
    with n:
      class O(Thing): pass
      c = O()
      d = O()
      e = O()
      f = O()
      g = O()
      AllDisjoint([c, d])
      AllDisjoint([c, e, f])
      AllDisjoint([g, f])
      AllDisjoint([e, f, g])
      
    s = set(frozenset(d.entities) for d in c.differents())
    assert s == { frozenset([c, d]), frozenset([c, e, f]) }
    
  def test_disjoint_7(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class D(Thing): pass
      class E(Thing): pass
      class F(Thing): pass
      AllDisjoint([C, D])
      AllDisjoint([C, E, F])
      
      class P1(ObjectProperty): pass
      class P2(ObjectProperty): pass
      class P3(ObjectProperty): pass
      class P4(ObjectProperty): pass
      AllDisjoint([P1, P2])
      AllDisjoint([P1, P3, P4])
      
      class O(Thing): pass
      c = O()
      d = O()
      e = O()
      f = O()
      AllDisjoint([c, d])
      AllDisjoint([c, e, f])
      
    s = set(frozenset(d.entities) for d in n.disjoint_classes())
    assert s == { frozenset([C, D]), frozenset([C, E, F]) }
    
    s = set(frozenset(d.entities) for d in n.disjoint_properties())
    assert s == { frozenset([P1, P2]), frozenset([P1, P3, P4]) }
    
    s = set(frozenset(d.entities) for d in n.different_individuals())
    assert s == { frozenset([c, d]), frozenset([c, e, f]) }
    
    s = set(frozenset(d.entities) for d in n.disjoints())
    assert s == { frozenset([C, D]),   frozenset([C, E, F]),
                  frozenset([P1, P2]), frozenset([P1, P3, P4]),
                  frozenset([c, d]),   frozenset([c, e, f]) }
    
    
  def test_annotation_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    
    assert issubclass(n.annot, AnnotationProperty)
    assert isinstance(n.annot, AnnotationPropertyClass)
    assert n.ma_pizza.annot == ["Test annot"]
    assert set(n.ma_pizza.comment) == { locstr("Commentaire", "fr"), locstr("Comment", "en") }
    assert n.Pizza.comment == [locstr("Comment on Pizza", "en")]
    
  def test_annotation_2(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    
    assert set(comment[n.ma_pizza, rdf_type, n.Pizza]) == { locstr('Comment on a triple', 'en'), locstr('Commentaire sur un triplet', 'fr') }
    assert comment[n.ma_pizza, rdf_type, n.Pizza].fr == ["Commentaire sur un triplet"]
    
  def test_annotation_3(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(Thing): pass
      class prop(ObjectProperty): pass
      class annot(AnnotationProperty): pass
      class annot2(AnnotationProperty): pass

    c1 = C1()
    c2 = C2()
    c1.prop.append(c2)
    assert annot[c1, prop, c2] == []
    
    annot[c1, prop, c2].append("Test")
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test") }
      
    annot[c1, prop, c2].append("Test1")
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test"), (annot.storid, "Test1") }
      
    annot2[c1, prop, c2].append("Test2")
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test"), (annot.storid, "Test1"), (annot2.storid, "Test2") }
    
    annot[c1, prop, c2].remove("Test")
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test1"), (annot2.storid, "Test2") }
    
  def test_annotation_4(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(Thing): pass
      class prop(ObjectProperty): pass
      class annot(AnnotationProperty): pass
      
    c1 = C1()
    c2 = C2()
    c1.prop.append(c2)
    
    annot[c1, prop, c2].append(locstr("Un test", "fr"))
    annot[c1, prop, c2].append(locstr("A test", "en"))
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test", "fr")), (annot.storid, locstr("A test", "en")) }
    
    assert set(annot[c1, prop, c2])  == { locstr("Un test", "fr"), locstr("A test", "en") }
    assert annot[c1, prop, c2].fr == ["Un test"]
    assert annot[c1, prop, c2].en == ["A test"]
    
    annot[c1, prop, c2].fr.append("Un second test")
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test", "fr")), (annot.storid, locstr("Un second test", "fr")), (annot.storid, locstr("A test", "en")) }
    
    annot[c1, prop, c2].fr.remove("Un test")
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un second test", "fr")), (annot.storid, locstr("A test", "en")) }
    
    annot[c1, prop, c2].fr = "Un test 2"
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test 2", "fr")), (annot.storid, locstr("A test", "en")) }
    
    annot[c1, prop, c2].fr = ["Un test 3", "Un test 4"]
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test 3", "fr")), (annot.storid, locstr("Un test 4", "fr")), (annot.storid, locstr("A test", "en")) }
    
  def test_annotation_5(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(Thing): pass
      class prop(ObjectProperty): pass
      class annot(AnnotationProperty): pass
      
    c1 = C1()
    c2 = C2()
    c1.prop.append(c2)
    
    annot[c1, prop, c2].append(locstr("Un test", "fr"))
    annot[c1, prop, c2].append(locstr("A test", "en"))
    
    annot[c1, prop, c2] = ["Test"]
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test") }
    
    annot[c1, prop, c2] = []
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots is None
    
  def test_annotation_6(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(Thing): pass
      class prop(ObjectProperty): pass
      class annot(AnnotationProperty): pass
      
    c1 = C1()
    c2 = C2()
    c1.prop.append(c2)
    
    annot[c1, prop, c2].en.append("A test")
    annot[c1, prop, c2].fr = "Un test"
    annots = None
    for bnode, p, o in n.get_triples(None, rdf_type, owl_axiom):
      if ((n.get_triple_sp(bnode, owl_annotatedsource  ) == c1.storid) and
          (n.get_triple_sp(bnode, owl_annotatedproperty) == prop.storid) and
          (n.get_triple_sp(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o)) for s,p,o in n.get_triples(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test", "fr")), (annot.storid, locstr("A test", "en")) }
    
  def test_annotation_7(self):
    n = self.new_ontology()
    with n:
      class prop(ObjectProperty): pass
      
    assert prop.comment == []
    assert prop.comment.fr == []
    
    prop.comment.append(locstr("EN", "en"))
    prop.comment.fr.append("FR")
    
    values = set()
    for s,p,o in n.get_triples(prop.storid, comment.storid, None): values.add(o)
    assert values == { to_literal(locstr("EN", "en")), to_literal(locstr("FR", "fr")) }
    
  def test_annotation_8(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class annot(AnnotationProperty): pass
      
    C.annot.fr = "FR"
    C.annot.en = "EN"
    
    values = set()
    for s,p,o in n.get_triples(C.storid, annot.storid, None): values.add(o)
    assert values == { to_literal(locstr("EN", "en")), to_literal(locstr("FR", "fr")) }
    
  def test_annotation_9(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(C1): pass
      class annot(AnnotationProperty): pass
      
    C1.annot.fr = "FR"
    C1.annot.en = "EN"
    
    assert C2.annot == []
    assert C1().annot == []
    assert C2().annot == []
    
  def test_annotation_10(self):
    n = self.new_ontology()
    with n:
      class P1(ObjectProperty): pass
      class P2(P1): pass
      class annot(AnnotationProperty): pass
      
    P1.annot.fr = "FR"
    P1.annot.en = "EN"
    
    assert P2.annot == []
    
    
  def test_import_1(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_mixed.owl").load()
    
    assert n.Parent in n.Child.is_a
    assert n.Parent in n.Child.__bases__
    
    assert n.Parent().test() == "ok1"
    assert n.Child ().test() == "ok2"
    
    o = n.Parent()
    o.is_a.append(n.Child)
    assert o.test() == "ok2"
    
    assert n.Parent().test_inherited() == "ok"
    assert n.Child ().test_inherited() == "ok"
    
    
  def test_close_1(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/test.owl")
    class O(Thing): namespace = n
    class P(Thing): namespace = n
    class has_for_p(ObjectProperty):
      namespace = n
      domain    = [O]
      range     = [P]
    o  = O()
    p1 = P()
    p2 = P()
    o.has_for_p = [p1, p2]
    
    close_world(o)
    
    restr = [c for c in o.is_a if not c is O][0]
    assert restr.property is has_for_p
    assert restr.type == ONLY
    assert isinstance(restr.value, OneOf) and set(restr.value.instances) == {p1, p2}
    
  def test_close_2(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/test.owl")
    class O(Thing): namespace = n
    class P(Thing): namespace = n
    class has_for_p(ObjectProperty):
      namespace = n
      domain    = [O]
      range     = [P]
    o  = O()
    p1 = P()
    p2 = P()
    o.is_a.append(has_for_p.some(P))
    close_world(o)
    
    assert o.is_a[-1].property is has_for_p
    assert o.is_a[-1].type == ONLY
    assert o.is_a[-1].value is P
    
  def test_close_3(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/test.owl")
    class O(Thing): namespace = n
    class P(Thing): namespace = n
    class has_for_p(ObjectProperty):
      namespace = n
      domain    = [O]
      range     = [P]
    O.is_a.append(has_for_p.some(P))
    o = O()
    close_world(o)
    
    assert o.is_a[-1].property is has_for_p
    assert o.is_a[-1].type == ONLY
    assert o.is_a[-1].value is P
    
  def test_close_4(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/test.owl")
    class O(Thing): namespace = n
    class P(Thing): namespace = n
    class has_for_p(ObjectProperty):
      namespace = n
      domain    = [O]
      range     = [P]
    o1 = O()
    o2 = O()
    close_world(O)
    
    restr = [c for c in O.is_a if isinstance(c, OneOf)][0]
    assert set(restr.instances) == { o1, o2 }
    restr = [c for c in O.is_a if isinstance(c, Restriction)][0]
    assert restr.property is has_for_p
    assert restr.type == ONLY
    assert restr.value is Nothing
    
  def test_close_5(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/test.owl")
    class O(Thing): namespace = n
    class P(Thing): namespace = n
    class Q(Thing): namespace = n
    class rel(ObjectProperty):
      namespace = n
      domain    = [O]
    p1 = P()
    p2 = P()
    q1 = Q()
    O.is_a.append(rel.value(p1))
    O.is_a.append(rel.value(p2))
    O.is_a.append(rel.some(Q))
    close_world(O)
    
    restr = O.is_a[-1]
    assert restr.property is rel
    assert restr.type == ONLY
    assert Q in restr.value.Classes
    x = list(restr.value.Classes)
    x.remove(Q)
    x = x[0]
    assert isinstance(x, OneOf) and (set(x.instances) == { p1, p2 })

  def test_close_6(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/test.owl")
    class O(Thing): namespace = n
    class O2(O):    namespace = n
    class P(Thing): namespace = n
    class has_for_p(ObjectProperty):
      namespace = n
      domain    = [O]
      range     = [P]
    O.is_a.append(has_for_p.some(P))
    close_world(O2)
    
    assert O2.is_a[-1].property is has_for_p
    assert O2.is_a[-1].type == ONLY
    assert O2.is_a[-1].value is P
    
  def test_close_7(self):
    w = self.new_world()
    n = w.get_ontology("http://test.org/test.owl")
    class O(Thing): namespace = n
    class O2(O):    namespace = n
    class P(Thing): namespace = n
    class has_for_p(ObjectProperty):
      namespace = n
      domain    = [O]
      range     = [P]
    o = O()
    p = P()
    O2.is_a.append(has_for_p.some(P))
    o .has_for_p = [p]
    close_world(O)
    
    assert repr(O.is_a) == repr([Thing, OneOf([o]), has_for_p.only((P | OneOf([p])))])

    
  def test_class_prop_1(self):
    onto = self.new_ontology()
    with onto:
      class O(Thing): pass
      class rel(DataProperty):
        domain   = [O]
        range    = [str]
    O.is_a.append(rel.value("test"))
    assert O.rel == ["test"]
    
    bnode = O.is_a[-1].storid
    self.assert_triple(O.storid, rdfs_subclassof, bnode)
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, rel.storid)
    self.assert_triple(bnode, VALUE, to_literal("test"))
    
  def test_class_prop_2(self):
    onto = self.new_ontology()
    with onto:
      class O(Thing): pass
      class rel(DataProperty, FunctionalProperty):
        domain   = [O]
        range    = [str]
    O.is_a.append(rel.value("test"))
    assert O.rel == "test"

    bnode = O.is_a[-1].storid
    self.assert_triple(O.storid, rdfs_subclassof, bnode)
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, rel.storid)
    self.assert_triple(bnode, VALUE, to_literal("test"))
    
  def test_class_prop_3(self):
    onto = self.new_ontology()
    with onto:
      class O(Thing): pass
      class rel(DataProperty, FunctionalProperty):
        domain   = [O]
        range    = [str]
    O.rel = "test"
    
    assert O.is_a[-1].property is rel
    assert O.is_a[-1].type == VALUE
    assert O.is_a[-1].value == "test"

    bnode = O.is_a[-1].storid
    self.assert_triple(O.storid, rdfs_subclassof, bnode)
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, rel.storid)
    self.assert_triple(bnode, VALUE, to_literal("test"))
    
    O.rel = None
    assert O.is_a == [Thing]

    self.assert_not_triple(O.storid, rdfs_subclassof, bnode)
    self.assert_not_triple(bnode, rdf_type, owl_restriction)
    self.assert_not_triple(bnode, owl_onproperty, rel.storid)
    self.assert_not_triple(bnode, VALUE, to_literal("test"))
    
  def test_class_prop_4(self):
    onto = self.new_ontology()
    with onto:
      class O(Thing): pass
      class rel(DataProperty):
        domain   = [O]
        range    = [str]
        
    O.rel = ["a", "b"]
    
    assert len(O.is_a) == 3
    assert O.is_a[-2].property is rel
    assert O.is_a[-2].type == VALUE
    assert O.is_a[-1].property is rel
    assert O.is_a[-1].type == VALUE
    assert { O.is_a[-2].value, O.is_a[-1].value } == { "a", "b" }
    
    O.rel = ["a", "c"]
    
    assert len(O.is_a) == 3
    assert O.is_a[-2].property is rel
    assert O.is_a[-2].type == VALUE
    assert O.is_a[-1].property is rel
    assert O.is_a[-1].type == VALUE
    assert { O.is_a[-2].value, O.is_a[-1].value } == { "a", "c" }
    
  def test_class_prop_5(self):
    onto = self.new_ontology()
    with onto:
      class O(Thing): pass
      class rel(DataProperty):
        domain   = [O]
        range    = [str]
        
    O.rel.append("a")
    O.rel.append("b")
    O.rel.append("c")
    O.rel.remove("b")
    
    assert len(O.is_a) == 3
    assert O.is_a[-2].property is rel
    assert O.is_a[-2].type == VALUE
    assert O.is_a[-1].property is rel
    assert O.is_a[-1].type == VALUE
    assert { O.is_a[-2].value, O.is_a[-1].value } == { "a", "c" }
    
  def test_class_prop_6(self):
    onto = self.new_ontology()
    with onto:
      class O(Thing): pass
      class P(Thing): pass
      class rel(ObjectProperty, FunctionalProperty):
        domain   = [O]
        range    = [P]
      class inv(ObjectProperty, InverseFunctionalProperty):
        domain   = [P]
        range    = [O]
        inverse_property = rel
    p = P()
    O.rel = p
    
    assert O.is_a[-1].property is rel
    assert O.is_a[-1].type == VALUE
    assert O.is_a[-1].value == p
    
    assert len(p.is_a) == 2
    assert p.is_a[-1].property is inv
    assert p.is_a[-1].type == SOME
    assert p.is_a[-1].value is O
    
    
  def test_class_prop_7(self):
    onto = self.new_ontology()
    with onto:
      class O(Thing): pass
      class P(Thing): pass
      class rel(ObjectProperty):
        domain   = [O]
        range    = [P]
      class inv(ObjectProperty):
        domain   = [P]
        range    = [O]
        inverse_property = rel
    p = P()
    O.rel.append(p)
    
    assert O.is_a[-1].property is rel
    assert O.is_a[-1].type == VALUE
    assert O.is_a[-1].value == p

    assert len(p.is_a) == 2
    assert p.is_a[-1].property is inv
    assert p.is_a[-1].type == SOME
    assert p.is_a[-1].value is O
    
    O.rel.remove(p)
    assert len(O.is_a) == 1
    assert len(p.is_a) == 1
      
  def test_class_prop_8(self):
    n = self.new_ontology()
    with n:
      class p(Thing >> int): pass
      class C(Thing):
        p = [1, 2]
    assert len(C.is_a) == 3
    assert C.is_a[-1].property is p
    assert C.is_a[-1].type == VALUE
    assert C.is_a[-2].property is p
    assert C.is_a[-2].type == VALUE
    assert { C.is_a[-1].value, C.is_a[-2].value } == { 1, 2 }
    
  def test_class_prop_9(self):
    n = self.new_ontology()
    with n:
      class p(Thing >> Thing): pass
      class D(Thing): pass
      d = D()
      class C(Thing):
        p = [d]
        
    assert len(C.is_a) == 2
    assert C.is_a[-1].property is p
    assert C.is_a[-1].type == VALUE
    assert C.is_a[-1].value is d
    
    assert len(d.is_a) == 2
    assert isinstance(d.is_a[-1].property, Inverse)
    assert d.is_a[-1].property.property is p
    assert d.is_a[-1].type == SOME
    assert d.is_a[-1].value is C
    
    C.p = []
    assert len(C.is_a) == 1
    assert len(d.is_a) == 1
    
    
  def test_format_1(self):
    from owlready2.triplelite import _guess_format
    
    f = open(os.path.join(HERE, "test_owlxml.ntriples"), "r")
    assert _guess_format(f) == "ntriples"
    f.close()
    
    f = open(os.path.join(HERE, "test.owl"), "r")
    assert _guess_format(f) == "rdfxml"
    f.close()
    
    f = open(os.path.join(HERE, "test_owlxml.owl"), "r")
    assert _guess_format(f) == "owlxml"
    f.close()
    
  def test_format_2(self):
    import re, owlready2.owlxml_2_ntriples
    
    triples1 = ""
    def on_triple(s,p,o):
      nonlocal triples1
      triples1 += "%s %s %s .\n" % (s,p,o)
    owlready2.owlxml_2_ntriples.parse(os.path.join(HERE, "test_owlxml.owl"), on_triple)
    
    f = open(os.path.join(HERE, "test_owlxml.ntriples"), "rb")
    triples2 = f.read().decode("unicode-escape")
    f.close()
    
    self.assert_ntriples_equivalent(triples1, triples2)
    
    #triples1 = re.sub(r"\_\:[a-zA_Z0-9]+", "_", triples1)
    #triples2 = re.sub(r"\_\:[a-zA_Z0-9]+", "_", triples2)
    
    #triples1 = triples1.split("\n")
    #triples2 = triples2.split("\n")
    
    #missing = set(triples2) - set(triples1)
    #exceed  = set(triples1) - set(triples2)
    
    #assert not missing
    #assert not exceed
    
  def test_format_3(self):
    world = self.new_world()
    onto = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/3/test_owlxml.owl").load()
    
    assert issubclass(onto.C2, onto.C)
    assert onto.p3.range == [onto.D]
    assert issubclass(onto.d, FunctionalProperty)
    
  def test_format_4(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    assert set(world.data_properties()) == { n.price }
    assert set(world.classes()) == { n.Meat, n.Tomato, n.Eggplant, n.Olive, n.Vegetable, n.NonPizza, n.Pizza, n.Cheese, n.VegetarianPizza, n.Topping }
    assert set(world.object_properties()) == { n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of }
    assert set(world.annotation_properties()) == { n.annot }
    assert set(world.properties()) == { n.price, n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of, n.annot }
    assert set(world.individuals()) == { n.mon_frometon, n.ma_tomate, n.ma_pizza }
    
  def test_format_5(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples").load()
    
    assert set(world.data_properties()) == { n.price }
    assert set(world.classes()) == { n.Meat, n.Tomato, n.Eggplant, n.Olive, n.Vegetable, n.NonPizza, n.Pizza, n.Cheese, n.VegetarianPizza, n.Topping }
    assert set(world.object_properties()) == { n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of }
    assert set(world.annotation_properties()) == { n.annot }
    assert set(world.properties()) == { n.price, n.has_topping, n.has_main_topping, n.main_topping_of, n.topping_of, n.annot }
    assert set(world.individuals()) == { n.mon_frometon, n.ma_tomate, n.ma_pizza }
    
  def test_format_6(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    import subprocess
    rapper = subprocess.Popen(["rapper", "-q", "-g", os.path.join(HERE, "test.owl")], stdout = subprocess.PIPE)
    triples1 = rapper.stdout.read().decode("unicode-escape")
    rapper.stdout.close()
    rapper.wait()
    
    rapper = subprocess.Popen(["rapper", "-q", "-g", "-", "http://test/xxx.owl"], stdin = subprocess.PIPE, stdout = subprocess.PIPE)
    n.save(rapper.stdin, "rdfxml")
    rapper.stdin.close()
    triples2 = rapper.stdout.read().decode("unicode-escape")
    rapper.stdout.close()
    rapper.wait()
    
    self.assert_ntriples_equivalent(triples1, triples2)
    
  def test_format_8(self):
    import re, owlready2.owlxml_2_ntriples
    
    triples1 = ""
    def on_triple(s,p,o):
      nonlocal triples1
      triples1 += "%s %s %s .\n" % (s,p,o)
    owlready2.owlxml_2_ntriples.parse(os.path.join(HERE, "test_owlxml_2.owl"), on_triple)
    
    f = open(os.path.join(HERE, "test_owlxml_2.ntriples"), "rb")
    triples2 = f.read().decode("unicode-escape")
    f.close()
    
    self.assert_ntriples_equivalent(triples1, triples2)
    
  def test_format_9(self):
    world = self.new_world()
    onto = world.get_ontology("http://test.org/test_owlxml_2.owl").load()
    
    d = onto.C.equivalent_to[0].value
    
    assert isinstance(d, ConstrainedDatatype)
    assert d.base_datatype is float
    assert d.min_inclusive == 100.0
    assert d.max_exclusive == 110.0
    
    c = onto.C.is_a[-1].property
    
    assert isinstance(c, Inverse)
    assert c.property is onto.P2
    
  def test_format_10(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/test_owlxml_bug.owl")
    ok    = 0
    try:
      onto.load()
    except OwlReadyOntologyParsingError:
      ok = 1
      
    assert ok == 1
    assert not onto.loaded
    assert len(world.graph) == 1
    
  def test_format_11(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/test_rdfxml_bug.owl")
    ok    = 0
    try:
      onto.load()
    except OwlReadyOntologyParsingError:
      ok = 1
      
    assert ok == 1
    assert not onto.loaded
    assert len(world.graph) == 1
    
  def test_format_13(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/test_ntriples_bug.ntriples")
    ok    = 0
    try:
      onto.load()
    except OwlReadyOntologyParsingError:
      ok = 1
      
    assert ok == 1
    assert not onto.loaded
    assert len(world.graph) == 1
    
  def test_format_14(self):
    import re, owlready2.owlxml_2_ntriples
    
    triples1 = ""
    def on_triple(s,p,o):
      nonlocal triples1
      triples1 += "%s %s %s .\n" % (s,p,o)
    owlready2.owlxml_2_ntriples.parse(os.path.join(HERE, "test_propchain_owlxml.owl"), on_triple)
    
    f = open(os.path.join(HERE, "test_propchain.ntriples"), "rb")
    triples2 = f.read().decode("unicode-escape")
    f.close()
    
    self.assert_ntriples_equivalent(triples1, triples2)
    
  def test_format_15(self):
    world = self.new_world()
    onto  = world.get_ontology("http://www.test.org/test_breakline.owl").load()
    
    assert onto.C.comment.first() == r"""Comment long
on
multiple lines with " and ’ and \ and & and < and > and é."""
    
    f = BytesIO()
    onto.save(f, format = "ntriples")
    s = f.getvalue().decode("utf8")
    
    assert s.count("\n") <= 4
    assert s == """<http://www.test.org/test_breakline.owl> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Ontology> .
<http://www.test.org/test_breakline.owl#C> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Class> .
<http://www.test.org/test_breakline.owl#C> <http://www.w3.org/2000/01/rdf-schema#comment> "Comment long\\non\\nmultiple lines with \\" and ’ and \\\\ and & and < and > and é."@en .
"""
    
  def test_format_16(self):
    world = self.new_world()
    onto  = world.get_ontology("http://www.test.org/test_annot_on_bn.owl").load()
    
    assert len(onto.graph) == 16
    
    s = comment[onto.C, owl_equivalentclass, onto.C.equivalent_to[0]].first()
    assert s == "Test"
    
  def test_format_17(self):
    world = self.new_world()
    onto  = world.get_ontology("http://www.test.org/test_annot_on_bn2.owl").load()
    
    assert len(onto.graph) == 29
    
    c = comment[onto.C, rdfs_subclassof, onto.C.is_a[-1]].first()
    d = comment[onto.D, rdfs_subclassof, onto.D.is_a[-1]].first()
    assert c == "Annot on C"
    assert d == "Annot on D"
    
  def test_format_18(self):
    world1 = self.new_world()
    onto1  = world1.get_ontology("http://www.test.org/test_annotated_axiom1.owl").load()
    world2 = self.new_world()
    onto2  = world2.get_ontology("http://www.test.org/test_annotated_axiom2.owl").load()
    
    assert len(onto1.graph) == 20
    assert len(onto2.graph) == 20
    
  def test_format_19(self):
    world = self.new_world()
    onto  = world.get_ontology("http://www.test.org/test_annotated_axiom3.owl").load()
    
    assert len(onto.graph) == 9
    
  def test_format_20(self):
    world = self.new_world()
    n = world.get_ontology("http://www.test.org/test_ns.owl").load()
    
    import subprocess
    rapper = subprocess.Popen(["rapper", "-q", "-g", os.path.join(HERE, "test_ns.owl")], stdout = subprocess.PIPE)
    triples1 = rapper.stdout.read().decode("unicode-escape")
    rapper.stdout.close()
    rapper.wait()
    
    triples2 = ""
    def on_triple(s,p,o):
      nonlocal triples2
      triples2 += "%s %s %s .\n" % (s,p,o)
    owlready2.rdfxml_2_ntriples.parse(os.path.join(HERE, "test_ns.owl"), on_triple)
    
    self.assert_ntriples_equivalent(triples1, triples2)
    
  def test_format_21(self):
    world = self.new_world()
    o = world.get_ontology("http://www.test.org/test_id.owl").load()
    
    assert issubclass(o.Prop1, ObjectProperty)
    assert issubclass(o.Prop2, ObjectProperty)
    assert o.Prop1.namespace == o
    assert o.Prop2.namespace == o
    assert o.Prop1.iri == "http://www.test.org/test_id.owl#Prop1"
    assert o.Prop2.iri == "http://www.test.org/test_id.owl#Prop2"
    
    
  def test_search_1(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    l = n.search(iri = "*Pizza")
    assert set(l) == { n.Pizza, n.NonPizza, n.VegetarianPizza }
    
    l = n.search(has_topping = n.ma_tomate)
    assert set(l) == { n.ma_pizza }
    
  def test_search_2(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    l = n.search(has_topping = [n.ma_tomate, n.mon_frometon])
    assert set(l) == { n.ma_pizza }
    
    l = n.search(has_topping = [n.ma_tomate, n.Cheese()])
    assert set(l) == set()
    
  def test_search_3(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    l = n.search(is_a = n.Pizza)
    assert set(l) == { n.ma_pizza, n.VegetarianPizza }
    
    l = n.search(type = n.Pizza)
    assert set(l) == { n.ma_pizza }
    
    l = n.search(subclass_of = n.Pizza)
    assert set(l) == { n.VegetarianPizza }
    
    
  def test_rdflib_1(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    g = world.as_rdflib_graph()
    
    assert (list(g.objects(rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza"),
                           rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#price")))[0].toPython()
            == 9.9)
    
    assert (set(g.objects(rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza"),
                          rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")))
            == { rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#Pizza"),
                 rdflib.URIRef("http://www.w3.org/2002/07/owl#NamedIndividual"),
            })
    
    tomato = n.Tomato()
    
    nb = len(world.graph)
    
    g.store.context_graphs[n].add(
      (rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza"),
       rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#has_topping"),
       rdflib.URIRef(tomato.iri),
    ))
    
    assert len(world.graph) == nb + 1
    
    g.store.context_graphs[n].remove(
      (rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza"),
       rdflib.URIRef("http://www.semanticweb.org/jiba/ontologies/2017/0/test#has_topping"),
       None,
    ))
    
    assert len(world.graph) == nb - 2
    
  def test_rdflib_2(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    g = world.as_rdflib_graph()
    
    r = g.query("""SELECT ?p WHERE {
    <http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza> <http://www.semanticweb.org/jiba/ontologies/2017/0/test#price> ?p .
    }
    """)
    
    assert list(r)[0][0].toPython() == 9.9
    
    
  def test_refactor_1(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    p = n.ma_pizza
    n.ma_pizza.name = "ma_pizza_2"
    assert n.ma_pizza is None
    assert n.ma_pizza_2 is p
    assert set(n.ma_pizza_2.has_topping) == { n.ma_tomate, n.mon_frometon }
    assert p.iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza_2"
    assert world["http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza_2"] is p
    
  def test_refactor_2(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    p = n.ma_pizza
    n.ma_pizza.iri = "http://t/p"
    assert n.ma_pizza is None
    assert set(p.has_topping) == { n.ma_tomate, n.mon_frometon }
    assert p.iri == "http://t/p"
    assert world["http://t/p"] is p
    assert n.get_namespace("http://t/").p is p
        
  def test_refactor_3(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    p = n.Pizza
    n.Pizza.name = "Pizza_2"
    assert n.Pizza is None
    assert n.Pizza_2 is p
    assert p.iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#Pizza_2"
    assert world["http://www.semanticweb.org/jiba/ontologies/2017/0/test#Pizza_2"] is p
    
  def test_refactor_4(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    p = n.Pizza
    n.Pizza.iri = "http://t/p"
    assert n.Pizza is None
    assert p.iri == "http://t/p"
    assert world["http://t/p"] is p
    assert n.get_namespace("http://t/").p is p
    
    
  def test_date_1(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class has_datetime(C >> datetime.datetime, FunctionalProperty): pass
      
    c = C()
    d = datetime.datetime(2017, 4, 19, 11, 28, 0)
    c.has_datetime = d
    self.assert_triple(c.storid, has_datetime.storid, '"2017-04-19T11:28:00"%s' % _universal_datatype_2_abbrev[datetime.datetime])
    
    del c.has_datetime
    assert c.has_datetime == d
    
  def test_date_2(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class has_date(C >> datetime.date, FunctionalProperty): pass
      
    c = C()
    d = datetime.date(2017, 4, 19)
    c.has_date = d
    self.assert_triple(c.storid, has_date.storid, '"2017-04-19"%s' % _universal_datatype_2_abbrev[datetime.date])
    
    del c.has_date
    assert c.has_date == d
    
  def test_date_3(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class has_time(C >> datetime.time, FunctionalProperty): pass
      
    c = C()
    d = datetime.time(11, 28, 0)
    c.has_time = d
    self.assert_triple(c.storid, has_time.storid, '"11:28:00"%s' % _universal_datatype_2_abbrev[datetime.time])
    
    del c.has_time
    assert c.has_time == d
    
    
  def test_datatype_1(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/3/test_datatype.owl").load()
    
    d = n.p.range[0]
    assert d.base_datatype is float
    assert d.min_exclusive == 10.0
    assert d.max_exclusive == 20.0
    
    d.base_datatype = int
    
    self.assert_triple(d.storid, owl_ondatatype, _universal_datatype_2_abbrev[int], world)
    
    d.min_exclusive = 15
    d.max_exclusive = 20
    
    list_bnode = world.get_triple_sp(d.storid, owl_withrestrictions)
    l = list(n._parse_list_as_rdf(list_bnode))
    s = set()
    for i in l:
      p,o = world.get_triples_s(i)[0]
      o = from_literal(o)
      s.add((p,o))
    assert s == { (xmls_minexclusive, 15),
                  (xmls_maxexclusive, 20) }
    
  def test_datatype_2(self):
    world = self.new_world()
    n = world.get_ontology("http://www.test.org/test.owl")
    
    with n:
      class C(Thing): pass
      class P(DataProperty):
        range = [
          ConstrainedDatatype(str, max_length = 8),
        ]

    d = P.range[0]
    
    self.assert_triple(d.storid, owl_ondatatype, _universal_datatype_2_abbrev[str], world)
    
    list_bnode = world.get_triple_sp(d.storid, owl_withrestrictions)
    l = list(n._parse_list_as_rdf(list_bnode))
    s = set()
    for i in l:
      p,o = world.get_triples_s(i)[0]
      o = from_literal(o)
      s.add((p,o))
    assert s == { (xmls_maxlength, 8) }

    
  def test_inverse_1(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/3/test_inverse.owl").load()
    
    r = n.C.is_a[-1]
    assert isinstance(r.property, Inverse)
    assert r.property.property is n.P
    
  def test_inverse_2(self):
    world = self.new_world()
    n = world.get_ontology("http://www.test.org/test.owl")
    
    with n:
      class P(ObjectProperty): pass
      class C(Thing): pass
      class D(Thing):
        is_a = [Inverse(P).some(C)]
        
    r = D.is_a[-1]
    assert isinstance(r.property, Inverse)
    self.assert_triple(r.property.storid, owl_inverse_property, P.storid, world)
    
  def test_inverse_3(self):
    world = self.new_world()
    n = world.get_ontology("http://www.test.org/test.owl")
    
    with n:
      class P1(ObjectProperty): pass
      class P2(ObjectProperty): pass
      class IP2(ObjectProperty):
        inverse_property = P2

    assert Inverse(Inverse(P1)) is P1
    assert Inverse(P2) is IP2
    assert Inverse(IP2) is P2
    
    
  def test_propchain_1(self):
    w = self.new_world()
    o = w.get_ontology("http://test/test_propchain.owl").load()
    
    obo = o.get_namespace("http://purl.obolibrary.org/obo/")
    
    assert len(obo.BFO_0000066.property_chain) == 1
    assert obo.BFO_0000066.property_chain[0].properties == [obo.BFO_0000050, obo.BFO_0000066]
    
  def test_propchain_2(self):
    w = self.new_world()
    o = w.get_ontology("http://test/test_propchain.owl")

    with o:
      class C(Thing): pass
      
      class P1(C >> C): pass
      class P2(C >> C): pass
      class P3(C >> C): pass
      class P4(C >> C): pass
      
      class P(C >> C): pass
      
    P.property_chain.append(PropertyChain([P1, P2]))
    
    bns = list(w.get_triples_sp(P.storid, owl_propertychain))
    assert len(bns) == 1
    assert o._parse_list(bns[0]) == [P1, P2]
    
    P.property_chain.append(PropertyChain([P3, P4]))
    
    bns = list(w.get_triples_sp(P.storid, owl_propertychain))
    assert len(bns) == 2
    assert o._parse_list(bns[0]) == [P1, P2]
    assert o._parse_list(bns[1]) == [P3, P4]
    
    del P.property_chain[0]
    
    bns = list(w.get_triples_sp(P.storid, owl_propertychain))
    assert len(bns) == 1
    assert o._parse_list(bns[0]) == [P3, P4]
    
  def test_destroy_1(self):
    w = self.new_world()
    o = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    destroy_entity(o.Pizza)
    
    assert len(w.graph) == 58
    
  def test_destroy_2(self):
    w = self.new_world()
    o = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    o.Pizza
    o.NonPizza
    assert o.Pizza
    assert len(o.NonPizza.is_a) == 2
    assert isinstance(o.NonPizza.is_a[-1], Not)
    assert o.NonPizza.is_a[-1].Class is o.Pizza
    
    destroy_entity(o.Pizza)
    
    assert len(w.graph) == 58
    assert o.Pizza is None
    assert len(o.NonPizza.is_a) == 1
    assert o.NonPizza.is_a[0] is Thing
    
  def test_destroy_3(self):
    w = self.new_world()
    o = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    destroy_entity(o.Meat)

    assert len(w.graph) == 68
    
  def test_destroy_4(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class D(C):     pass
      
    #w.graph.dump()
    #print(len(w.graph))
    
    destroy_entity(C)
    
    #w.graph.dump()
    #print(len(w.graph))
    #print(D.is_a)
    
    assert D.is_a == [Thing]
    assert o.C is None
    assert not o.D is None
    
  def test_destroy_5(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C1(Thing): pass
      class C2(Thing): pass
      class C3(Thing): pass
      
      class D(Thing):
        is_a = [C1 | C2 | C3]
        
    destroy_entity(C2)
    
    #w.graph.dump()
    #print(len(w.graph))
    #print(D.is_a)
    
    assert len(w.graph) == 7
    assert D.is_a == [Thing]
    
  def test_destroy_6(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      
      class p(C >> C): pass

    assert p.range  == [C]
    assert p.domain == [C]
    
    destroy_entity(C)
    
    assert p.range  == []
    assert p.domain == []
    
  def test_destroy_7(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass

    c = C()
    
    destroy_entity(C)
    
    assert c.is_a  == [Thing]
    
  def test_destroy_8(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class D(Thing): pass
      class E(Thing): pass
      AllDisjoint([C, D, E])
      
    destroy_entity(C)
    
    assert len(w.graph) == 5
    assert len(list(o.disjoints())) == 0
    
  def test_destroy_9(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      c1 = C()
      c2 = C()
      c3 = C()
      AllDisjoint([c1, c2, c3])
      C.is_a.append(OneOf([c1, c2, c3]))
      
    destroy_entity(c1)
    
    assert len(w.graph) == 7
    assert len(list(o.disjoints())) == 0
    
  def test_destroy_10(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class D(C): pass
      label[D, rdfs_subclassof, D] = "Test"
      
    destroy_entity(D)
    
    assert len(w.graph) == 3
    
  def test_destroy_11(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class D(Thing): pass
      class E(Thing): pass
      
      C.equivalent_to.append(D)
      D.equivalent_to.append(E)
      
    destroy_entity(D)
    
    assert C.equivalent_to == []
    assert E.equivalent_to == []
    assert len(w.graph) == 5
    
  def test_destroy_12(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class D(Thing): pass
      class p(ObjectProperty): pass
      
      D.is_a.append(p.some(C))
      
    destroy_entity(C)
    
    assert len(w.graph) == 4
    
  def test_destroy_13(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class D(Thing): pass
      class p(ObjectProperty): pass
      class q(ObjectProperty): pass
      
      D.is_a.append(p.some(q.only(Not(C))))
      
    destroy_entity(C)
    
    assert D.is_a == [Thing]
    assert len(w.graph) == 5
    
  def test_destroy_14(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class p(ObjectProperty): pass
      c1 = C()
      C.is_a.append(p.value(c1))
      
    destroy_entity(c1)
    
    assert C.is_a == [Thing]
    assert len(w.graph) == 4
    
  def test_destroy_15(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class p(ObjectProperty): pass
      c1 = C()
      C.is_a.append(p.value(c1))
      c1.p = [c1]
      
    destroy_entity(p)
    
    assert C.is_a == [Thing]
    assert getattr(c1, "p", None) == None
    assert len(w.graph) == 5
    
    
class Paper(BaseTest, unittest.TestCase):
  def test_paper_ic2017(self):
    world = self.new_world()
    onto = world.get_ontology("http://www.lesfleursdunormal.fr/static/_downloads/paper_ic2017.owl")
    
    with onto:
      class Origine(Thing): pass
      class Acquise(Origine): pass
      class Constitutionnelle(Origine): pass
      Origine.is_a.append(Acquise | Constitutionnelle)
      AllDisjoint([Acquise, Constitutionnelle])
      
      
      class aPourOrigine(ObjectProperty): pass
      
      class Maladie(Thing):
        is_a = [aPourOrigine.some(Origine),
                aPourOrigine.only(Origine)]
        
      class MaladieHémorragique(Maladie): pass
      
      class MHAcquise(MaladieHémorragique):
        equivalent_to = [MaladieHémorragique & aPourOrigine.some(Acquise)]
        
      class MHConsti(MaladieHémorragique):
        equivalent_to = [MaladieHémorragique & aPourOrigine.some(Constitutionnelle)]
        
        
      class Médicament(Thing): pass
      class ContreIndication(Thing): pass
      
      class aPourContreIndication(ObjectProperty): pass
      class contreIndicationDe(ObjectProperty):
        inverse_property = aPourContreIndication
        
      class aPourMaladie(ObjectProperty): pass
      class maladieDe(ObjectProperty):
        inverse_property = aPourMaladie
        
      ciA = ContreIndication("ciA")
      ciA.is_a.append(aPourMaladie.some(MHAcquise))
      ciA.is_a.append(aPourMaladie.only(MHAcquise))
      ciC = ContreIndication("ciC")
      ciC.is_a.append(aPourMaladie.some(MHConsti))
      ciC.is_a.append(aPourMaladie.only(MHConsti))
      
      MHAcquise.is_a.append(maladieDe.value(ciA))
      MHConsti .is_a.append(maladieDe.value(ciC))
      
      m = Médicament("m")
      m.aPourContreIndication = [ciA, ciC]
      m.is_a.append(aPourContreIndication.only(OneOf([ciA, ciC])))
      
      
      class Maladie_CI_avec_m(Maladie):
        equivalent_to = [Maladie & maladieDe.some(contreIndicationDe.some(OneOf([m])))]
    
      sync_reasoner(world, debug = 0)
    
    assert MaladieHémorragique in Maladie_CI_avec_m.equivalent_to
    assert issubclass(MaladieHémorragique, Maladie_CI_avec_m)
    
  def test_paper_5(self):
    world = self.new_world()
    onto = world.get_ontology("http://www.lesfleursdunormal.fr/static/_downloads/paper_5.owl")
    
    with onto:
      class Disorder(Thing): pass
      class Drug(Thing): pass
      class Contraindication(Thing): pass
      
      AllDisjoint([Disorder, Drug, Contraindication])
      
      
      class has_for_drug(ObjectProperty):
        domain   = [Contraindication]
        range    = [Drug]

      class has_for_disorder(ObjectProperty):
        domain   = [Contraindication]
        range    = [Disorder]

      class contraindicated_with(ObjectProperty):
        domain           = [Drug]
        range            = [Contraindication]
        inverse_property = has_for_drug

      class contraindicates(ObjectProperty):
        domain           = [Disorder]
        range            = [Contraindication]
        inverse_property = has_for_disorder

      class HemorrhagicDisorder(Disorder): pass

      class AcquiredHemorrhagicDisorder(HemorrhagicDisorder): pass

      class ConstitutiveHemorrhagicDisorder(HemorrhagicDisorder): pass

      partition(HemorrhagicDisorder, [AcquiredHemorrhagicDisorder, ConstitutiveHemorrhagicDisorder])

      class Heparin(Drug): pass

      class AntiplateletDrug(Drug): pass

      class Ticagrelor(AntiplateletDrug): pass

      class Aspirin(AntiplateletDrug): pass

      AllDisjoint([Heparin, AntiplateletDrug])
      AllDisjoint([Heparin, Ticagrelor, Aspirin])


      # Create the four contraindications (step 1 in the paper)

      ci1 = Contraindication()
      ci2 = Contraindication()
      ci3 = Contraindication()
      ci4 = Contraindication()


      # Relate drug classes to contraindications (step 2 in the paper)

      Ticagrelor.contraindicated_with = [ci1]
      Heparin   .contraindicated_with = [ci2]
      Aspirin   .contraindicated_with = [ci3, ci4]


      # Relate disorder classes to contraindications (step 3 in the paper)

      HemorrhagicDisorder            .contraindicates = [ci1]
      AcquiredHemorrhagicDisorder    .contraindicates = [ci3]
      ConstitutiveHemorrhagicDisorder.contraindicates = [ci2, ci4]


      # Assert that everything is known about contraindications (step 4 in the paper)

      close_world(Contraindication)


      # Assert that everything is known about drugs (step 5 in the paper)

      close_world(Drug)


      # Create classes for reasoning and execute the reasoner

      class DisorderContraindicatingAspirin(Disorder):
        equivalent_to = [Disorder & contraindicates.some(has_for_drug.some(Aspirin))]

      class DisorderContraindicatingTicagrelor(Disorder):
        equivalent_to = [Disorder & contraindicates.some(has_for_drug.some(Ticagrelor))]

      class DisorderContraindicatingHeparin(Disorder):
        equivalent_to = [Disorder & contraindicates.some(has_for_drug.some(Heparin))]


      class DisorderOKWithAspirin(Disorder):
        equivalent_to = [Disorder & Not(contraindicates.some(has_for_drug.some(Aspirin)))]

      class DisorderOKWithTicagrelor(Disorder):
        equivalent_to = [Disorder & Not(contraindicates.some(has_for_drug.some(Ticagrelor)))]

      class DisorderOKWithHeparin(Disorder):
        equivalent_to = [Disorder & Not(contraindicates.some(has_for_drug.some(Heparin)))]
        
    sync_reasoner(world, debug = 0)
    
    CI   = "CI   "
    OK   = "Ok   "
    CIOK = "CI/Ok"
    
    t = []
    for disorder_class in [HemorrhagicDisorder, AcquiredHemorrhagicDisorder, ConstitutiveHemorrhagicDisorder]:
      for contraindicating_class, ok_class in [
          (DisorderContraindicatingAspirin, DisorderOKWithAspirin),
          (DisorderContraindicatingHeparin, DisorderOKWithHeparin),
          (DisorderContraindicatingTicagrelor, DisorderOKWithTicagrelor),
      ]:
        if   issubclass(disorder_class, contraindicating_class): t.append(CI)
        elif issubclass(disorder_class, ok_class):               t.append(OK)
        else:                                                    t.append(CIOK)

    x  = "\n"
    x += "                                  ticagrelor heparin aspirin\n"
    x += "             hemorrhagic disorder %s      %s   %s\n" % (t[0], t[1], t[2])
    x += "    acquired hemorrhagic disorder %s      %s   %s\n" % (t[3], t[4], t[5])
    x += "constitutive hemorrhagic disorder %s      %s   %s\n" % (t[6], t[7], t[8])

    assert x.strip() == """
                                  ticagrelor heparin aspirin
             hemorrhagic disorder CI         CI/Ok   CI   
    acquired hemorrhagic disorder CI         Ok      CI   
constitutive hemorrhagic disorder CI         CI      CI   """.strip()

  def test_paper_ic2015(self):
    world = self.new_world()
    onto = world.get_ontology("http://www.lesfleursdunormal.fr/static/_downloads/crepes_et_galettes.owl")
    onto.load()
    
    ma_galette = onto.Galette()
    ma_galette.a_pour_garniture = [ onto.Tomate(),
                                    onto.Viande() ]
    
    ok = 0
    class GaletteNonVégétarienne(onto.Galette):
      equivalent_to = [
        onto.Galette
        & ( onto.a_pour_garniture.some(onto.Viande)
          | onto.a_pour_garniture.some(onto.Poisson)
        ) ]
      def manger(self):
        nonlocal ok
        ok = 1
      
    sync_reasoner(world, debug = 0)
    
    assert ma_galette.__class__ is GaletteNonVégétarienne
    
    ma_galette.manger()
    
    assert ok == 1


    
if __name__ == '__main__': unittest.main()
  
