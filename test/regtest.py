
import sys, os, unittest, tempfile, atexit, datetime
from io import StringIO, BytesIO

try:
  import rdflib
except:
  pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import owlready2, owlready2.util
from owlready2 import *
from owlready2.base import _universal_abbrev_2_datatype, _universal_datatype_2_abbrev

from owlready2.ntriples_diff import *

print("Testing Owlready2 version 2-%s located in %s" % (VERSION, owlready2.__file__))


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

BACKEND = "sqlite"
if "--postgresql" in sys.argv:
  sys.argv.remove("--postgresql")
  BACKEND = "postgresql"

_QUADSTORE_ID = 0

if BACKEND == "postgresql":
  def remove_dbs():
    for i in range(1, _QUADSTORE_ID + 1):
      os.system("dropdb owlready2_quadstore_%s &" % i)
  atexit.register(remove_dbs)

class BaseTest(object):
  def setUp(self):
    self.nb_triple    = len(default_world.graph)
    
  def assert_nb_created_triples(self, x):
    assert (len(default_world.graph) - self.nb_triple) == x
    
  def assert_triple(self, s, p, o, d = None, world = default_world):
    if d is None:
      if not world._has_obj_triple_spo(s, p, o):
        if s > 0: s = world._unabbreviate(s)
        p = world._unabbreviate(p)
        if o > 0: o = world._unabbreviate(o)
        print("MISSING TRIPLE", s, p, o)
        raise AssertionError
    else:
      if not world._has_data_triple_spod(s, p, o, d):
        if s > 0: s = world._unabbreviate(s)
        p = world._unabbreviate(p)
        print("MISSING TRIPLE", s, p, o, d)
        raise AssertionError
    
  def assert_not_triple(self, s, p, o, d = None, world = default_world):
    if d is None:
      if world._has_obj_triple_spo(s, p, o):
        if s > 0: s = world._unabbreviate(s)
        p = world._unabbreviate(p)
        if o > 0: o = world._unabbreviate(o)
        print("UNEXPECTED TRIPLE", s, p, o)
        raise AssertionError
    else:
      if world._has_data_triple_spod(s, p, o, d):
        if s > 0: s = world._unabbreviate(s)
        p = world._unabbreviate(p)
        print("UNEXPECTED TRIPLE", s, p, o, d)
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
    global _QUADSTORE_ID
    
    if   BACKEND == "sqlite":
      filename = self.new_tmp_file()
      world = World(filename = filename)
      
    elif BACKEND == "postgresql":
      _QUADSTORE_ID += 1
      os.system("createdb owlready2_quadstore_%s" % _QUADSTORE_ID)
      world = World(backend = "postgresql", dbname = "owlready2_quadstore_%s" % _QUADSTORE_ID)
      
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
    assert iri in default_world._entities
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
    assert not iri in default_world._entities
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
    if BACKEND == "sqlite": world.set_backend(filename = ":memory:")
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
    A = world._abbreviate("http://test.org/t.owl#A")
    B = world._abbreviate("http://test.org/t.owl#B")
    o._add_obj_triple_spo(A, rdf_type, owl_class)
    #missing triple (B, rdf_type, owl_class)
    o._add_obj_triple_spo(A, rdfs_subclassof, B)
    
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
    self.assert_triple(c1.storid, prop.storid, *to_literal(1), world = o2)
    
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
    
  def test_ontology_8(self):
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1.owl")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2.owl")
    o1.imported_ontologies.append(o2)
    file = BytesIO()
    o1.save(file)
    assert """<owl:imports rdf:resource="http://www.semanticweb.org/jiba/ontologies/2017/0/test2.owl"/>""" in file.getvalue().decode("utf8")
    
  def test_ontology_9(self):
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1.owl")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2.owl")
    o1.imported_ontologies = [o2]
    file = BytesIO()
    o1.save(file)
    assert """<owl:imports rdf:resource="http://www.semanticweb.org/jiba/ontologies/2017/0/test2.owl"/>""" in file.getvalue().decode("utf8")
    
  def test_ontology_10(self):
    temp_dir = tempfile.TemporaryDirectory()
    onto_path.insert(0, temp_dir.name)
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1.owl")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2.owl")
    o1.imported_ontologies = [o2]
    o1.save()
    o2.save()
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1.owl").load()
    assert len(o1.imported_ontologies) == 1
    
    onto_path.remove(temp_dir.name)
    temp_dir.cleanup()
    
  def test_ontology_11(self):
    temp_dir = tempfile.TemporaryDirectory()
    onto_path.insert(0, temp_dir.name)
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1.owl")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2.owl")
    o1.imported_ontologies = [o2]
    o1.save()
    o2.save()
    
    w  = self.new_world()
    o1 = w.get_ontology("file://%s/test1.owl" % temp_dir.name).load()
    assert len(o1.imported_ontologies) == 1
    
    onto_path.remove(temp_dir.name)
    temp_dir.cleanup()

  def test_ontology_12(self):
    temp_dir = tempfile.TemporaryDirectory()
    onto_path.insert(0, temp_dir.name)
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2")
    o1.imported_ontologies = [o2]
    o1.save()
    o2.save()
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1").load()
    assert len(o1.imported_ontologies) == 1
    
    onto_path.remove(temp_dir.name)
    temp_dir.cleanup()
    
  def test_ontology_13(self):
    temp_dir = tempfile.TemporaryDirectory()
    onto_path.insert(0, temp_dir.name)
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2")
    o1.imported_ontologies = [o2]
    o1.save()
    o2.save()
    
    w  = self.new_world()
    o1 = w.get_ontology("file://%s/test1.owl" % temp_dir.name).load()
    assert len(o1.imported_ontologies) == 1
    
    onto_path.remove(temp_dir.name)
    temp_dir.cleanup()
    
  def test_ontology_14(self):
    temp_dir = tempfile.TemporaryDirectory()
    onto_path.insert(0, temp_dir.name)
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1/")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2/")
    o1.imported_ontologies = [o2]
    o1.save()
    o2.save()
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1/").load()
    assert len(o1.imported_ontologies) == 1
    
    onto_path.remove(temp_dir.name)
    temp_dir.cleanup()
    
  def test_ontology_15(self):
    temp_dir = tempfile.TemporaryDirectory()
    onto_path.insert(0, temp_dir.name)
    
    w  = self.new_world()
    o1 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test1/")
    o2 = w.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test2/")
    o1.imported_ontologies = [o2]
    o1.save()
    o2.save()
    
    w  = self.new_world()
    o1 = w.get_ontology("file://%s/test1.owl" % temp_dir.name).load()
    assert len(o1.imported_ontologies) == 1
    
    onto_path.remove(temp_dir.name)
    temp_dir.cleanup()
    
  def test_ontology_16(self):
    w = self.new_world()
    o = w.get_ontology("http://test.org/test_ontoslash/").load()
    
    assert o.base_iri == "http://test.org/test_ontoslash/"
    assert o.Class1
    assert o.Class2
    assert o.Class1.iri == "http://test.org/test_ontoslash/Class1"
    assert o.Class2.iri == "http://test.org/test_ontoslash/Class2"
    
  def test_ontology_17(self):
    w = self.new_world()
    o = w.get_ontology("file://%s/test_ontoslash.owl" % HERE).load()
    
    assert o.base_iri == "http://test.org/test_ontoslash/"
    assert o.Class1
    assert o.Class2
    assert o.Class1.iri == "http://test.org/test_ontoslash/Class1"
    assert o.Class2.iri == "http://test.org/test_ontoslash/Class2"
    
  def test_ontology_18(self):
    w = self.new_world()
    o = w.get_ontology("file://%s/test_ontoslash.owl" % HERE).load()
    
    assert len(o.imported_ontologies) == 1
        
  def test_ontology_19(self):
    w = self.new_world()
    o = w.get_ontology("http://test.org/t.owl")
    
    o.metadata.comment = "com1"
    o.metadata.comment.append("com2")
    
    self.assert_triple(o.storid, comment.storid, *to_literal("com1"), world = w)
    self.assert_triple(o.storid, comment.storid, *to_literal("com2"), world = w)
    
  def test_ontology_20(self):
    w = self.new_world()
    o = w.get_ontology("file://%s/test_ontoslash.owl" % HERE).load()
    
    o.metadata.comment = "com1"
    o.metadata.comment.append("com2")
    
    self.assert_triple(o.storid, comment.storid, *to_literal("com1"), world = w)
    self.assert_triple(o.storid, comment.storid, *to_literal("com2"), world = w)
    
  def test_ontology_21(self):
    w = self.new_world()
    o = w.get_ontology("file://%s/test_ontoslash.owl" % HERE).load()
    
    assert o.metadata.comment == ["TEST"]
    
  def test_ontology_22(self):
    w = self.new_world()
    o = w.get_ontology("http://test.org/test.owl")

    assert o.graph.get_last_update_time() == 0.0
    
    with o:
      class C(Thing): pass
      
    assert o.graph.get_last_update_time() != 0.0
    
  def test_ontology_23(self):
    w = self.new_world()
    o = w.get_ontology("http://test.org/test.owl")

    assert set(w.general_axioms()) == set()
    assert set(o.general_axioms()) == set()
    
    with o:
      class C(Thing): pass
      class p(ObjectProperty): pass
      class D(Thing):
        is_a = [p.some(C)]
      class E(Thing): pass
      
    assert set(w.general_axioms()) == set()
    assert set(o.general_axioms()) == set()
    
    o._add_obj_triple_spo(-2, rdf_type, owl_restriction)
    o._add_obj_triple_spo(-2, owl_onproperty, p.storid)
    o._add_obj_triple_spo(-2, SOME, D.storid)
    o._add_obj_triple_spo(-2, rdfs_subclassof, E.storid)

    assert set(w.general_axioms()) == set([o._parse_bnode(-2)])
    assert set(o.general_axioms()) == set([o._parse_bnode(-2)])
    
  def test_ontology_24(self):
    world = self.new_world()
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "test.owl"))
    onto = world.get_ontology("file://" + filename).load()
    
    r = set(onto.get_triples(onto.Pizza.storid))
    assert r == {(305, 39, '"Comment on Pizza"@en'), (305, 6, 11)}
    
    r = set(onto.get_triples(None, rdf_type, onto.Pizza.storid))
    assert r == {(319, 6, 305)}
    
    r = set(onto.get_triples(None, None, '"9.9"^^<http://www.w3.org/2001/XMLSchema#float>'))
    assert r == {(319, 310, 9.9, 58)}

    
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
      
      D.equivalent_to.indirect() # Read and define it
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
        
    assert not "equivalent_to" in D.__dict__ # Must not be set in the dict!
    
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
        
    assert set(C.equivalent_to.indirect()) == { D, E }
    assert set(D.equivalent_to.indirect()) == { C, E }
    assert set(E.equivalent_to.indirect()) == { C, D }
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
      
    assert set(C.equivalent_to.indirect()) == { D, E }
    assert set(D.equivalent_to.indirect()) == { C, E }
    assert set(E.equivalent_to.indirect()) == { C, D }
    
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
    
  def test_class_21(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/test.owl")
    
    with onto:
      class MyClass(Thing): comment = "abc"
      
    self.assert_triple(MyClass.storid, comment.storid, *to_literal("abc"), world = world)
    
    
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
    
    assert set(i2.equivalent_to.indirect()) == { i1 }
    
    i1.equivalent_to.remove(i2)
    assert set(i2.equivalent_to.indirect()) == set()
    assert set(i1.equivalent_to.indirect()) == set()
    
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
    
    assert set(i1.equivalent_to.indirect()) == { i2, i3, i4 }
    assert set(i2.equivalent_to.indirect()) == { i1, i3, i4 }
    assert set(i3.equivalent_to.indirect()) == { i1, i2, i4 }
    assert set(i4.equivalent_to.indirect()) == { i1, i2, i3 }
    
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
    self.assert_triple(c.storid, propi.storid, *to_literal(1))
    self.assert_triple(c.storid, propi.storid, *to_literal(2))
    self.assert_triple(c.storid, propif.storid, *to_literal(3))
    
  def test_individual_10(self):
    world   = self.new_world()
    onto    = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/2/test_reasoning.owl").load()
    
    assert len(onto.pizza_tomato.is_a) == 2
    
  def test_individual_11(self):
    world   = self.new_world()
    o       = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    assert set(o.ma_pizza.get_properties()) == { o.price, o.annot, comment, o.has_topping, o.has_main_topping }
    assert set(o.ma_tomate.get_inverse_properties()) == { (o.ma_pizza, o.has_topping), (o.ma_pizza, o.has_main_topping) }
    
  def test_individual_12(self):
    world   = self.new_world()
    o       = world.get_ontology("http://www.test.org/test.owl")

    with o:
      class O(Thing): pass
      class p(O >> O, TransitiveProperty): pass
      
      o1 = O()
      o2 = O(p = [o1])
      o3 = O(p = [o2])
      o4 = O(p = [o3])

    r = set(o3.p.transitive())
    assert r == { o1, o2 }
    
  def test_individual_13(self):
    world   = self.new_world()
    o       = world.get_ontology("http://www.test.org/test.owl")

    with o:
      class O(Thing): pass
      class p(O >> O, TransitiveProperty): pass
      class i(O >> O, TransitiveProperty): inverse = p
      
      o1 = O()
      o2 = O(p = [o1])
      o3 = O(p = [o2])
      o4 = O(i = [o3])
      o6 = O()
      o5 = O(i = [o4], p = [o6])
      o7 = O()
      
    r = set(o3.p.transitive())
    assert r == { o1, o2, o4, o5, o6 }
    
  def test_individual_14(self):
    world   = self.new_world()
    o       = world.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class O(Thing): pass
      class p(O >> O, TransitiveProperty, SymmetricProperty): pass
      
      o1 = O()
      o2 = O(p = [o1])
      o3 = O(p = [o2])
      o4 = O(p = [o3])
      o5 = O()
      o6 = O(p = [o5])
      o7 = O()
      
    r = set(o3.p.transitive_symmetric())
    assert r == { o3, o1, o2, o4 }
    
    r = set(o3.p.symmetric())
    assert r == { o2, o4 }
    
  def test_individual_15(self):
    world   = self.new_world()
    o       = world.get_ontology("http://www.test.org/test.owl")

    with o:
      class O(Thing): pass
      class p(O >> O, TransitiveProperty): pass
      class q(p): pass
      class s(q): pass
      
      o1 = O()
      o2 = O()
      o3 = O()
      o4 = O(s = [o3])
      o5 = O(q = [o4])
      o6 = O(s = [o5], q = [o1], p = [o2])
      o7 = O()
      o8 = O(s = [o5])
      
    r = set(o6.q.indirect())
    assert r == { o5, o1, o4, o3 }
    
  def test_individual_16(self):
    world   = self.new_world()
    o       = world.get_ontology("http://www.test.org/test.owl")

    with o:
      class BodyPart(Thing): pass
      class part_of(BodyPart >> BodyPart, TransitiveProperty): pass
      abdomen          = BodyPart("abdomen")
      heart            = BodyPart("heart"           , part_of = [abdomen])
      left_ventricular = BodyPart("left_ventricular", part_of = [heart])
      kidney           = BodyPart("kidney"          , part_of = [abdomen])
      
    assert left_ventricular.part_of == [heart]
    assert set(left_ventricular.part_of.indirect()) == { heart, abdomen }
    
  def test_individual_17(self):
    world   = self.new_world()
    onto = get_ontology("http://test.org/t.owl")
    with onto:
      class Emp(Thing): pass
      class Emp2(Thing): pass
      class p1(Thing >> int): pass
      class p2(Thing >> int): pass
      
    e1 = Emp("e")
    e2 = Emp("e")
    
    assert e1 is e2
    
    f1 = Emp("f")
    f2 = Emp2("f")
    
    assert f1 is f2
    assert isinstance(f1, Emp)
    assert isinstance(f2, Emp2)
    
    g1 = Emp("g", p1 = [1])
    g2 = Emp("g", p2 = [2])
    
    assert g1 is g2
    assert g1.p1 == [1]
    assert g1.p2 == [2]
    
  def test_individual_18(self):
    world   = self.new_world()
    onto = get_ontology("http://test.org/t.owl")
    with onto:
      class Emp1(Thing):
        def f1(self): pass
      class Emp2(Thing):
        def f2(self): pass

    e = Emp1()
    Emp2(e)
    
    e.f1()
    e.f2()
    
    assert isinstance(e, Emp1)
    assert isinstance(e, Emp2)
    
  def test_individual_19(self):
    world   = self.new_world()
    onto = get_ontology("http://test.org/test_undeclared_entity.owl").load()
    
    # Can guest it is a class
    assert [i.iri for i in onto.C.hasRelatedSynonym] == ["http://test.org/test_undeclared_entity.owl#genid1217"]
    
    assert onto.i.hasRelatedSynonym == ["http://test.org/test_undeclared_entity.owl#genid1219"]
    
  def test_individual_20(self):
    world   = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()

    nb_triples = len(n.graph)
    
    o2 = n.Cheese("mon_frometon")
    o1 = n.Cheese("mon_frometon")
    assert o1 is o2
    assert o1 is n.mon_frometon
    
    assert len(n.graph) == nb_triples
    
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
    assert default_world._get_data_triple_sp_od(pizza.storid, n.price.storid) is None
    pizza.price = 8.0

    assert from_literal(*default_world._get_data_triple_sp_od(pizza.storid, n.price.storid)) == 8.0
    pizza.price = 9.0
    assert from_literal(*default_world._get_data_triple_sp_od(pizza.storid, n.price.storid)) == 9.0
    pizza.price = None
    assert default_world._get_data_triple_sp_od(pizza.storid, n.price.storid) is None
    
  def test_prop_6(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    pizza = n.Pizza()
    assert pizza.has_topping == []
    tomato = n.Tomato()
    cheese = n.Cheese()
    pizza.has_topping = [tomato]
    assert default_world._get_obj_triple_sp_o(pizza.storid, n.has_topping.storid) == tomato.storid
    pizza.has_topping.append(cheese)
    self.assert_triple(pizza.storid, n.has_topping.storid, tomato.storid)
    self.assert_triple(pizza.storid, n.has_topping.storid, cheese.storid)
    pizza.has_topping.remove(tomato)
    assert default_world._get_obj_triple_sp_o(pizza.storid, n.has_topping.storid) == cheese.storid
    
  def test_prop_7(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class prop (DataProperty): pass
      class propf(DataProperty, FunctionalProperty): pass
    c = C()
    c.prop  = [0, 1]
    c.propf = 2
    
    self.assert_triple(c.storid, prop .storid, *to_literal(0))
    self.assert_triple(c.storid, prop .storid, *to_literal(1))
    self.assert_triple(c.storid, propf.storid, *to_literal(2))
    
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
        
    self.assert_triple(prop.storid, rdf_range, n._abbreviate("http://www.w3.org/2001/XMLSchema#integer"))
    assert isinstance(prop.range, util.CallbackList)
    
    prop.range.append(float)
    self.assert_triple(prop.storid, rdf_range, n._abbreviate("http://www.w3.org/2001/XMLSchema#decimal"))
    
    prop.range.remove(int)
    self.assert_not_triple(prop.storid, rdf_range, n._abbreviate("http://www.w3.org/2001/XMLSchema#integer"))
    
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
    for s,p,o,d in n._get_data_triples_spod_spod(c1.storid, prop.storid, None): values.add((o,d))
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
      for s,p,o in n._get_obj_triples_spo_spo(prop.storid, rdf_type, None): yield o
      
    assert set(get_types(prop1)) == { owl_data_property }
    assert set(get_types(prop2)) == { owl_object_property }
    assert set(get_types(prop3)) == { owl_object_property, n._abbreviate("http://www.w3.org/2002/07/owl#FunctionalProperty") }
    assert set(get_types(prop4)) == { owl_annotation_property }
    assert set(get_types(prop5)) == { owl_object_property }
    
    def get_subclasses(prop):
      for s,p,o in n._get_obj_triples_spo_spo(prop.storid, rdfs_subpropertyof, None): yield o
      
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
    self.assert_triple(has_prop.storid, owlready_python_name, *to_literal("props"), world = w)
    
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
    
    self.assert_triple(has_prop.storid, owlready_python_name, *to_literal("props"), world = w)
    
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
    
  def test_prop_25(self):
    world   = self.new_world()
    o       = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    assert set(o.price.get_relations()) == { (o.ma_pizza, 9.9) }
    assert set(o.has_topping.get_relations()) == { (o.ma_pizza, o.mon_frometon), (o.ma_pizza, o.ma_tomate) }
    
  def test_prop_26(self):
    world   = self.new_world()
    n       = world.get_ontology("http://www.semanticweb.org/test.owl")
    
    with n:
      class O(Thing): pass
      class C(Thing): pass
      o = O()
      
      class p(Thing >> Thing): pass
      
      class Q(Thing):
        is_a = [p.value(o), p.some(C)]
        
        
      q = Q()
      
    assert q.p == []
    assert set(q.p.indirect()) == { o, C }
    
  def test_prop_27(self):
    world   = self.new_world()
    n       = world.get_ontology("http://www.semanticweb.org/test.owl")
    
    with n:
      class O(Thing): pass
      class C(Thing): pass
      o = O()
      
      class p(Thing >> Thing): pass
      
      class Q(Thing):
        is_a = [p.value(o), p.some(C)]
        
      class Q2(Thing): pass
        
        
      q = Q()
      q.is_a.append(Q2)

    assert q.p == []
    assert set(q.p.indirect()) == { o, C }
    
  def test_prop_28(self):
    world   = self.new_world()
    n       = world.get_ontology("http://www.semanticweb.org/test.owl")
    
    with n:
      class p(Thing >> Thing, TransitiveProperty): pass
      
      class C1(Thing): pass
      class C2(Thing): pass
      class C3(Thing): pass
      class C4(Thing): pass
      c1 = C1()
      c2 = C2()
      c3 = C3()
      
      c1.p = [c2]
      c2.p = [c3]
      
      C3.is_a = [p.some(C4)]
      
    assert c1.p == [c2]
    assert set(c1.p.indirect()) == { c2, c3, C4 }
    
  def test_prop_29(self):
    world   = self.new_world()
    n       = world.get_ontology("http://www.semanticweb.org/test.owl")
    
    with n:
      class Ingredient(Thing): pass
      class Kale(Ingredient): pass
      
      class Taste(Thing): pass
      class Bitter(Taste): pass
      
      class has_taste(Ingredient >> Taste): pass
      
      bitter = Bitter()
      Kale.is_a.append(has_taste.some(Bitter))
      
      kale = Kale()
      
    assert kale.has_taste == []
    assert set(kale.has_taste.indirect()) == { Bitter }
    
  def test_prop_30(self):
    world   = self.new_world()
    n       = world.get_ontology("http://www.semanticweb.org/test.owl")
    
    with n:
      class Ingredient(Thing): pass
      class Kale(Ingredient): pass
      
      class Taste(Thing): pass
      
      class has_taste(Ingredient >> Taste): pass
      
      bitter = Taste()
      Kale.is_a.append(has_taste.value(bitter))
      
      kale = Kale()
      
    assert kale.has_taste == []
    assert set(kale.has_taste.indirect()) == { bitter }
    
    
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
    assert len(list(default_world._get_obj_triples_spo_spo(r.storid, None, None))) == 3
    
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
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 3
    
    r.value = C3
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P1.storid)
    self.assert_triple(bnode, ONLY, C3.storid)
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 3
    
    r.property = P2
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, ONLY, C3.storid)
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 3
    
    r.type        = EXACTLY
    r.cardinality = 2
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C3.storid)
    self.assert_triple(bnode, EXACTLY, 2, n._abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 4
    
    r.type        = MIN
    r.cardinality = 3
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C3.storid)
    self.assert_triple(bnode, MIN, 3, n._abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 4
    
    r.value = None
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_min_cardinality, 3, n._abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 3
    
    r.type = MAX
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_max_cardinality, 3, n._abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 3
    
    r.value = C2
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C2.storid)
    self.assert_triple(bnode, MAX, 3, n._abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 4
    
    r.type = EXACTLY
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P2.storid)
    self.assert_triple(bnode, owl_onclass, C2.storid)
    self.assert_triple(bnode, EXACTLY, 3, n._abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 4
    
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
    self.assert_triple(bnode, ONLY, n._abbreviate("http://www.w3.org/2001/XMLSchema#integer"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 3
    
    r.value       = float
    r.type        = EXACTLY
    r.cardinality = 5
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, P1.storid)
    self.assert_triple(bnode, EXACTLY, 5, n._abbreviate("http://www.w3.org/2001/XMLSchema#nonNegativeInteger"))
    self.assert_triple(bnode, owl_ondatarange, n._abbreviate("http://www.w3.org/2001/XMLSchema#decimal"))
    assert len(list(default_world._get_triples_spod_spod(bnode, None, None, None))) == 4
    
  def test_construct_restriction_5(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    a = n.has_topping.some(n.Vegetable)
    b = n.has_topping.some(n.Vegetable)
    
    assert a == b
    
  def test_construct_restriction_6(self):
    n = get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test")
    
    assert Not(n.has_topping.some(n.Meat)) in n.VegetarianPizza.is_a
    
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
      
    self.assert_triple(onto.VegetalianPizza.storid, rdfs_subclassof, onto.VegetarianPizza.storid, None, world)
    self.assert_triple(onto.pizza_tomato.storid, rdf_type, onto.VegetalianPizza.storid, None, world)
    self.assert_triple(onto.pizza_tomato_cheese.storid, rdf_type, onto.VegetarianPizza.storid, None, world)
    
    assert onto.VegetarianPizza in onto.VegetalianPizza.__bases__
    assert onto.pizza_tomato.__class__ is onto.VegetalianPizza
    assert onto.pizza_tomato_cheese.__class__ is onto.VegetarianPizza
    
    assert len(results.graph) == 4
    
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
    
  def test_reasoning_3(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/drug.owl")

    output = ""
    def print(s):
      nonlocal output
      output += s + "\n"
      
    with onto:
        class Drug(Thing):
            def take(self): print("I took a drug")

        class ActivePrinciple(Thing):
            pass

        class has_for_active_principle(Drug >> ActivePrinciple):
            python_name = "active_principles"
            
        class Placebo(Drug):
            equivalent_to = [Drug & Not(has_for_active_principle.some(ActivePrinciple))]
            def take(self): print("I took a placebo")
            
        class SingleActivePrincipleDrug(Drug):
            equivalent_to = [Drug & has_for_active_principle.exactly(1, ActivePrinciple)]
            def take(self): print("I took a drug with a single active principle")
            
        class DrugAssociation(Drug):
            equivalent_to = [Drug & has_for_active_principle.min(2, ActivePrinciple)]
            def take(self): print("I took a drug with %s active principles" % len(self.active_principles))
            
    acetaminophen   = ActivePrinciple("acetaminophen")
    amoxicillin     = ActivePrinciple("amoxicillin")
    clavulanic_acid = ActivePrinciple("clavulanic_acid")
    
    AllDifferent([acetaminophen, amoxicillin, clavulanic_acid])
    
    drug1 = Drug(active_principles = [acetaminophen])
    drug2 = Drug(active_principles = [amoxicillin, clavulanic_acid])
    drug3 = Drug(active_principles = [])
    
    close_world(Drug)
    
    # Running the reasoner
    with onto:
      sync_reasoner(world, debug = 0)
        
    # Results of the automatic classification
    drug1.take()
    drug2.take()
    drug3.take()
    
    assert drug1.__class__ is onto.SingleActivePrincipleDrug
    assert drug2.__class__ is onto.DrugAssociation
    assert drug3.__class__ is onto.Placebo
    
    assert output == """I took a drug with a single active principle
I took a drug with 2 active principles
I took a placebo
"""
    
  def test_reasoning_4(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/test.owl")
    
    with onto:
      class C(Thing): pass
      class D(Thing): pass
      class E(Thing): pass
      class p(ObjectProperty, FunctionalProperty):
        domain = [C]
        range  = [D]
        
      class F(C):
        is_a = [p.some(E)]
        
      AllDisjoint([C, D, E])
      
    sync_reasoner(world, debug = 0)
    
    assert Nothing in F.equivalent_to
    assert F in list(world.inconsistent_classes())
    
  def test_reasoning_5(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/test.owl")
    
    with onto:
      class C(Thing): pass
      class D(Thing): pass
      class E(Thing): pass
      class p(ObjectProperty, FunctionalProperty):
        domain = [C]
        range  = [D]
        
      class F(C):
        is_a = [p.some(E)]
        
      f = F()
      AllDisjoint([C, D, E])

    try:
      sync_reasoner(world, debug = 0)
    except OwlReadyInconsistentOntologyError:
      return

    assert False
     
  def test_reasoning_6(self):
    world = self.new_world()
    onto  = world.get_ontology("http://test.org/test.owl#")
    
    with onto:
      class Personne(Thing): pass
      
      class age   (Personne >> int  , FunctionalProperty): pass
      class taille(Personne >> float, FunctionalProperty): pass
      
      class PersonneAgée(Personne):
        equivalent_to = [
          Personne & (age >= 65)
        ]
        
      class PersonneGrande(Personne):
        equivalent_to = [
          Personne & taille.some(ConstrainedDatatype(float, min_inclusive = 1.8))
        ]
        
      p1 = Personne(age = 25, taille = 2.0)
      p2 = Personne(age = 39, taille = 1.7)
      p3 = Personne(age = 65, taille = 1.6)
      p4 = Personne(age = 71, taille = 1.9)
      
    sync_reasoner(world, debug = 0)

    assert set(p1.is_a) == {PersonneGrande}
    assert set(p2.is_a) == {Personne}
    assert set(p3.is_a) == {PersonneAgée}
    assert set(p4.is_a) == {PersonneAgée, PersonneGrande}
    
    
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
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test") }
      
    annot[c1, prop, c2].append("Test1")
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test"), (annot.storid, "Test1") }
      
    annot2[c1, prop, c2].append("Test2")
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test"), (annot.storid, "Test1"), (annot2.storid, "Test2") }
    
    annot[c1, prop, c2].remove("Test")
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
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
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test", "fr")), (annot.storid, locstr("A test", "en")) }
    
    assert set(annot[c1, prop, c2])  == { locstr("Un test", "fr"), locstr("A test", "en") }
    assert annot[c1, prop, c2].fr == ["Un test"]
    assert annot[c1, prop, c2].en == ["A test"]
    
    annot[c1, prop, c2].fr.append("Un second test")
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test", "fr")), (annot.storid, locstr("Un second test", "fr")), (annot.storid, locstr("A test", "en")) }
    
    annot[c1, prop, c2].fr.remove("Un test")
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un second test", "fr")), (annot.storid, locstr("A test", "en")) }
    
    annot[c1, prop, c2].fr = "Un test 2"
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test 2", "fr")), (annot.storid, locstr("A test", "en")) }
    
    annot[c1, prop, c2].fr = ["Un test 3", "Un test 4"]
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
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
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, "Test") }
    
    annot[c1, prop, c2] = []
    annots = None
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
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
    for bnode, p, o in n._get_obj_triples_spo_spo(None, rdf_type, owl_axiom):
      if ((n._get_obj_triple_sp_o(bnode, owl_annotatedsource  ) == c1.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedproperty) == prop.storid) and
          (n._get_obj_triple_sp_o(bnode, owl_annotatedtarget  ) == c2.storid)):
        annots = { (p, n._to_python(o,d)) for s,p,o,d in n._get_triples_spod_spod(bnode, None, None) if not p in [rdf_type, owl_annotatedsource, owl_annotatedproperty, owl_annotatedtarget] }
        break
    assert annots == { (annot.storid, locstr("Un test", "fr")), (annot.storid, locstr("A test", "en")) }
    
  def test_annotation_7(self):
    n = self.new_ontology()
    with n:
      class prop(ObjectProperty): pass
      
    assert prop.comment == []
    assert prop.comment.fr == []
    
    prop.comment.append(locstr("ENGLISH", "en"))
    prop.comment
    prop.comment.fr.append("FRENCH")
    
    values = set()
    for s,p,o,d in n._get_triples_spod_spod(prop.storid, comment.storid, None, None): values.add((o,d))
    assert values == { to_literal(locstr("ENGLISH", "en")), to_literal(locstr("FRENCH", "fr")) }
    
  def test_annotation_8(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      class annot(AnnotationProperty): pass
      
    C.annot.fr = "FRENCH"
    C.annot.en = "ENGLISH"
    
    values = set()
    for s,p,o,d in n._get_triples_spod_spod(C.storid, annot.storid, None, None): values.add((o,d))
    assert values == { to_literal(locstr("ENGLISH", "en")), to_literal(locstr("FRENCH", "fr")) }
    
  def test_annotation_9(self):
    n = self.new_ontology()
    with n:
      class C1(Thing): pass
      class C2(C1): pass
      class annot(AnnotationProperty): pass
      
    C1.annot.fr = "FRENCH"
    C1.annot.en = "ENGLISH"
    
    assert C2.annot == []
    assert C1().annot == []
    assert C2().annot == []
    
  def test_annotation_10(self):
    n = self.new_ontology()
    with n:
      class P1(ObjectProperty): pass
      class P2(P1): pass
      class annot(AnnotationProperty): pass
      
    P1.annot.fr = "FRENCH"
    P1.annot.en = "ENGLISH"
    
    assert P2.annot == []
    
  def test_annotation_11(self):
    n = self.new_ontology()
    with n:
      class P1(ObjectProperty): pass
      class P2(DataProperty): pass
      class P3(AnnotationProperty): pass
      class C (Thing): pass
      i = C()
    P1.comment = "annot1"
    P2.comment = "annot2"
    P3.comment = "annot3"
    C .comment = "annot4"
    i .comment = "annot5"
    
    assert P1.comment == ["annot1"]
    assert P2.comment == ["annot2"]
    assert P3.comment == ["annot3"]
    assert C .comment == ["annot4"]
    assert i .comment == ["annot5"]
    
    P1.comment = None
    P2.comment = None
    P3.comment = None
    C .comment = None
    i .comment = None
    
    assert P1.comment == []
    assert P2.comment == []
    assert P3.comment == []
    assert C .comment == []
    assert i .comment == []
    
  def test_annotation_12(self):
    n = get_ontology("http://www.test.org/test_annot_literal.owl").load()
    
    assert set(n.C.classDescription) == { locstr("Annotation value"), 8, locstr("Annotation with lang", "en") }
    
  def test_annotation_13(self):
    n = self.new_ontology()
    with n:
      class C(Thing): pass
      C.comment.append(8)
      C.comment.append("eee")
      C.comment.append(locstr("plain literal"))
      C.comment.append(locstr("literal with lang", "en"))
      
    self.assert_triple(C.storid, comment.storid, 8, n._abbreviate("http://www.w3.org/2001/XMLSchema#integer"))
    self.assert_triple(C.storid, comment.storid, "eee", n._abbreviate("http://www.w3.org/2001/XMLSchema#string"))
    self.assert_triple(C.storid, comment.storid, "plain literal", n._abbreviate("http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral"))
    self.assert_triple(C.storid, comment.storid, "literal with lang", "@en")
    
  def test_annotation_14(self):
    onto = self.new_ontology()
    with onto:
      class C(Thing): pass
      class p(C >> int): pass
      c = C(p = [1, 2])
      comment[c, p, 1] = ["Commentaire"]
      
    assert comment[c, p, 1] == ["Commentaire"]
    assert comment[c, p, 2] == []

    C.is_a.append(p.only(OneOf([1, 2, 3])))
    
  def test_annotation_15(self):
    world = self.new_world()
    onto = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2018/10/test_datatype_one_of.owl").load()
    
    assert comment[onto.d1, onto.p, 1] == ["Annotation on a triple with a datatype value."]
    assert onto.d1.p == [1]
    assert onto.D.is_a[1].value.instances == [1, 2, 3]
    
  def test_annotation_16(self):
    world = self.new_world()
    onto = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2018/10/test_datatype_one_of_owlxml.owl").load()

    assert onto.d1.p == [1]
    assert comment[onto.d1, onto.p, 1] == ["Annotation on a triple with a datatype value."]
    assert onto.D.is_a[1].value.instances == [1, 2, 3]
    
    
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
    self.assert_triple(bnode, VALUE, *to_literal("test"))
    
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
    self.assert_triple(bnode, VALUE, *to_literal("test"))
    
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
    self.assert_triple(bnode, VALUE, *to_literal("test"))
    
    O.rel = None
    assert O.is_a == [Thing]

    self.assert_not_triple(O.storid, rdfs_subclassof, bnode)
    self.assert_not_triple(bnode, rdf_type, owl_restriction)
    self.assert_not_triple(bnode, owl_onproperty, rel.storid)
    self.assert_not_triple(bnode, VALUE, *to_literal("test"))
    
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
    
  def test_class_prop_10(self):
    onto = self.new_ontology()
    with onto:
      class D(Thing): pass
      class R(Thing): pass
      class rel(ObjectProperty):
        domain   = [D]
        range    = [R]
    D.is_a.append(rel.some(R))
    
    assert D.rel == [R]
    
    D.rel.remove(R)
    
    assert D.rel == []
    
    assert D.is_a == [Thing]
    
    
  def test_class_prop_11(self):
    onto = self.new_ontology()
    with onto:
      class D(Thing): pass
      class R(Thing): pass
      class rel(ObjectProperty):
        domain   = [D]
        range    = [R]
    D.rel = [R]
    
    assert D.rel == [R]
    assert rel.some(R) in D.is_a
    
    bnode = D.is_a[-1].storid
    self.assert_triple(D.storid, rdfs_subclassof, bnode)
    self.assert_triple(bnode, rdf_type, owl_restriction)
    self.assert_triple(bnode, owl_onproperty, rel.storid)
    self.assert_triple(bnode, SOME, R.storid)

    del D.is_a[-1]

    assert D.rel == []
    
    
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
    def on_prepare_triple(s,p,o):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if not o.startswith("_"): o = "<%s>" % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    def on_prepare_data(s,p,o,d):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if   isinstance(d, str) and d.startswith("@"): o = '"%s"%s' % (o, d)
      elif d:                                        o = '"%s"^^<%s>' % (o, d)
      else:                                          o = '"%s"' % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    #owlready2.driver.parse_owlxml(os.path.join(HERE, "test_owlxml.owl"), on_prepare_triple, on_prepare_data)
    
    f = open(os.path.join(HERE, "test_owlxml.ntriples"), "rb")
    triples2 = f.read().decode("unicode-escape")
    f.close()
    
    #self.assert_ntriples_equivalent(triples1, triples2)
    
    
    triples1 = ""
    owlready2.owlxml_2_ntriples.parse(os.path.join(HERE, "test_owlxml.owl"), on_prepare_triple, on_prepare_data)
     
    self.assert_ntriples_equivalent(triples1, triples2)
    
    
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
    def on_prepare_triple(s,p,o):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if not o.startswith("_"): o = "<%s>" % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    def on_prepare_data(s,p,o,d):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if   isinstance(d, str) and d.startswith("@"): o = '"%s"%s' % (o, d)
      elif d:                                        o = '"%s"^^<%s>' % (o, d)
      else:                                          o = '"%s"' % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    
    f = open(os.path.join(HERE, "test_owlxml_2.ntriples"), "rb")
    triples2 = f.read().decode("unicode-escape")
    f.close()
    
    triples1 = ""
    owlready2.owlxml_2_ntriples.parse(os.path.join(HERE, "test_owlxml_2.owl"), on_prepare_triple, on_prepare_data)
    
    self.assert_ntriples_equivalent(triples2, triples1)
    
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
    def on_prepare_triple(s,p,o):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if not o.startswith("_"): o = "<%s>" % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    def on_prepare_data(s,p,o,d):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if   isinstance(d, str) and d.startswith("@"): o = '"%s"%s' % (o, d)
      elif d:                                        o = '"%s"^^<%s>' % (o, d)
      else:                                          o = '"%s"' % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    #owlready2.driver.parse_owlxml(os.path.join(HERE, "test_propchain_owlxml.owl"), on_prepare_triple, on_prepare_data)
    
    f = open(os.path.join(HERE, "test_propchain.ntriples"), "rb")
    triples2 = f.read().decode("unicode-escape")
    f.close()
    
    #self.assert_ntriples_equivalent(triples1, triples2)

    
    triples1 = ""
    owlready2.owlxml_2_ntriples.parse(os.path.join(HERE, "test_propchain_owlxml.owl"), on_prepare_triple, on_prepare_data)
    
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
    import owlready2.rdfxml_2_ntriples
    world = self.new_world()
    n = world.get_ontology("http://www.test.org/test_ns.owl").load()
    
    import subprocess
    rapper = subprocess.Popen(["rapper", "-q", "-g", os.path.join(HERE, "test_ns.owl")], stdout = subprocess.PIPE)
    triples2 = rapper.stdout.read().decode("unicode-escape")
    rapper.stdout.close()
    rapper.wait()
    
    triples1 = ""
    def on_prepare_triple(s,p,o):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if not o.startswith("_"): o = "<%s>" % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    def on_prepare_data(s,p,o,d):
      nonlocal triples1
      if not s.startswith("_"): s = "<%s>" % s
      p = "<%s>" % p
      if   isinstance(d, str) and d.startswith("@"): o = '"%s"%s' % (o, d)
      elif d:                                        o = '"%s"^^<%s>' % (o, d)
      else:                                          o = '"%s"' % o
      triples1 += "%s %s %s .\n" % (s,p,o)
    #owlready2.driver.parse_rdfxml(os.path.join(HERE, "test_ns.owl"), on_prepare_triple, on_prepare_data)
    
    #self.assert_ntriples_equivalent(triples1, triples2)
    
    
    triples1 = ""
    owlready2.rdfxml_2_ntriples.parse(os.path.join(HERE, "test_ns.owl"), on_prepare_triple, on_prepare_data)
    
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
    
  def test_format_22(self):
    world = self.new_world()
    o = world.get_ontology("http://www.test.org/test_url").load()
    
    assert o.O
    assert o.O2
    assert o.O3
    assert issubclass(o.O2, o.O)
    assert issubclass(o.O3, o.O2)
    assert set(o.search(subclass_of = o.O)) == { o.O2, o.O3 }
    
  def test_format_23(self):
    world = self.new_world()
    n = world.get_ontology("http://www.test.org/test_url").load()
    
    import subprocess
    rapper = subprocess.Popen(["rapper", "-q", "-g", os.path.join(HERE, "test_url.owl")], stdout = subprocess.PIPE)
    triples1 = rapper.stdout.read().decode("unicode-escape")
    rapper.stdout.close()
    rapper.wait()
    
    rapper = subprocess.Popen(["rapper", "-q", "-g", "-", "http://www.test.org/test_url"], stdin = subprocess.PIPE, stdout = subprocess.PIPE)
    n.save(rapper.stdin, "rdfxml")
    rapper.stdin.close()
    triples2 = rapper.stdout.read().decode("unicode-escape")
    rapper.stdout.close()
    rapper.wait()
    
    self.assert_ntriples_equivalent(triples1, triples2)
    
  def test_format_24(self):
    quadstore = os.path.join(HERE, "test_quadstore_slash.sqlite3")
    assert os.path.exists(quadstore)
    world = self.new_world()
    world.set_backend(filename = quadstore)
    onto = world.get_ontology("http://test.org/test_slash/").load()
    onto.graph.dump()
    assert onto.C is not None
    world.close()
    
  def test_format_25(self):
    world = self.new_world()
    world.set_backend(filename = os.path.join(HERE, "test_quadstore_slash.sqlite3"))
    onto = world.get_ontology("http://test.org/test_slash")
    assert onto.C is not None
    world.close()
    
  def test_format_26(self):
    world = self.new_world()
    onto = world.get_ontology("http://test.org/test.org#")
    self.assert_triple(onto.storid, rdf_type, owl_ontology, None, world)
    
    s = """<http://test.org/test.org#A> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Class>."""
    onto.load(fileobj = BytesIO(s.encode("utf8")))
    
    self.assert_triple(onto.storid, rdf_type, owl_ontology, None, world)
    assert len(world.graph) == 2
    
  def test_format_27(self):
    # Verify that Cython PYX version is used
    import owlready2_optimized
    
    
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
    
  def test_search_4(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    l = n.search(type = n.Pizza, has_topping = None)
    assert set(l) == set()
    
    n.ma_pizza.price = 9.9
    n.Pizza("pizzvide")
    n.Pizza("pizzvide2", price = 9.9)
    
    l = n.search(type = n.Pizza, has_topping = None)
    assert set(l) == { n.pizzvide, n.pizzvide2 }
    
    l = n.search(type = n.Pizza, price = 9.9, has_topping = None)
    assert set(l) == { n.pizzvide2 }
    
  def test_search_5(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    n.Tomato()
    
    l = n.search(type = n.Tomato, topping_of = n.ma_pizza)
    assert set(l) == { n.ma_tomate }
    
    l = n.search(topping_of = n.ma_pizza)
    assert set(l) == { n.ma_tomate, n.mon_frometon }
    
  def test_search_6(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    l = n.search(type = n.Tomato)
    assert set(l) == { n.ma_tomate }
    
    l = n.search(type = n.Topping)
    assert set(l) == { n.ma_tomate, n.mon_frometon }
    
    l = n.search(subclass_of = n.Tomato)
    assert set(l) == set()
    
    l = n.search(is_a = n.Tomato)
    assert set(l) == { n.ma_tomate }
    
    l = n.search(subclass_of = n.Topping)
    assert set(l) == { n.Tomato, n.Cheese, n.Meat, n.Vegetable, n.Eggplant, n.Olive }
    
    l = n.search(is_a = n.Topping)
    assert set(l) == { n.ma_tomate, n.mon_frometon, n.Tomato, n.Cheese, n.Meat, n.Vegetable, n.Eggplant, n.Olive }
    
  def test_search_7(self):
    world = self.new_world()
    n = world.get_ontology("http://test.org/test.owl")
    with n:
      class O(Thing): pass
      class p(O >> str): pass

    o1 = O(p = ["ABCD"])
    o2 = O(p = ["ABC"])
    o3 = O(p = ["AB", "EF"])
    o4 = O(p = ["EFG"])

    l = n.search(p = "ABC*")
    assert set(l) == { o1, o2 }
    
    l = n.search(p = "EF*")
    assert set(l) == { o3, o4 }
    
  def test_search_8(self):
    world = self.new_world()
    onto = world.get_ontology("http://test.org/test.owl")
    with onto:
      class O(Thing): pass
      class q(O >> str): pass
      class p(O >> O): pass
      class i(O >> O):
        inverse = p
        
    o1 = O()
    o2 = O()
    o3 = O()
    o4 = O()

    o1.p = [o2, o3]
    o4.p = [o2]

    assert onto.search(p = [o2, o3]) == [o1]
    
    o1 = O()
    o2 = O()
    o3 = O()
    o4 = O()

    o1.p = [o2]
    o3.i = [o1]
    
    assert onto.search(p = [o2, o3]) == [o1]
    
    o1 = O()
    o2 = O()
    o3 = O()
    o4 = O()

    o2.i = [o1, o4]
    o3.i = [o1]
    
    assert world.search(p = [o2, o3]) == [o1]
    
    o1 = O(q = ["x"])
    o2 = O(q = ["x"])
    o3 = O(q = ["y"])
    o4 = O()

    o1.p = [o2, o3]
    o4.p = [o2]
    
    assert onto.search(q = "x", p = [o2, o3]) == [o1]
    
  def test_search_9(self):
    world = self.new_world()
    onto = world.get_ontology("http://test.org/test.owl")
    with onto:
      class O(Thing): pass
      class i(O >> int,   FunctionalProperty): pass
      class f(O >> float, FunctionalProperty): pass

      o1 = O(i = 1, f = 2.3)
      o2 = O(i = 3, f = 0.3)
      o3 = O(i = 4, f = -2.3)
      o4 = O(i = 7, f = 4.6)

    assert set(onto.search(i = NumS(">" , 3  ))) == set([o3, o4])
    assert set(onto.search(f = NumS("<=", 0.3))) == set([o2, o3])
    
  def test_search_10(self):
    world = self.new_world()
    onto = world.get_ontology("http://test.org/test.owl")
    with onto:
      class O(Thing): pass
      class i(O >> int): pass

      o1 = O(i = [1])
      o2 = O(i = [3])
      o3 = O(i = [4])
      o4 = O(i = [7, 1])

    assert set(onto.search(i = NumS("<=", 3))) == set([o1, o2, o4])
    assert set(onto.search(i = NumS("=" , 1))) == set([o1, o4])
    assert set(onto.search(i = NumS(">" , 1, "<", 4))) == set([o2])
    
  def test_search_11(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    l = world.search(type = n.Pizza, has_topping = world.search(type = n.Tomato))
    assert set(l) == { n.ma_pizza }
    
    l = world.search(type = n.Tomato, topping_of = world.search(has_topping = n.mon_frometon))
    assert set(l) == { n.ma_tomate }
    
    
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
    
  def test_rdflib_3(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/test.owl")
    with n:
      class O(Thing): pass
      class p(Thing >> str): pass
      o = O("o")
      o.p = ["D"]
      
    g = world.as_rdflib_graph()
    
    r = g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    SELECT ?x WHERE {
    ?x P:p "D".
    }
    """)
    assert list(r)[0][0] is o
    
    r = g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    SELECT ?x WHERE {
    ?x P:p "E".
    }
    """)
    assert not list(r)
    
    r = g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    SELECT ?x WHERE {
    P:o P:p ?x.
    }
    """)
    assert list(r) == [["D"]]

  def test_rdflib_4(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/test.owl")
    with n:
      class O(Thing): pass
      class p(Thing >> bool, FunctionalProperty): pass
      class i(Thing >> int , FunctionalProperty): pass
      o1 = O(p = False, i = 1)
      o2 = O(p = True , i = 1)
      o3 = O(p = True , i = 2)
      
    g = world.as_rdflib_graph()
    
    r = list(g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?s WHERE {
    ?s P:i "1"^^xsd:int.
    }
    """))
    assert set(l[0] for l in r) == { o1, o2 }
    
    r = list(g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?s WHERE {
    ?s P:p "true"^^xsd:boolean.
    }
    """))
    assert set(l[0] for l in r) == { o2, o3 }
    
    r = list(g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?s WHERE {
    ?s P:p "true".
    }
    """))
    assert set(l[0] for l in r) == { o2, o3 }
    
    r = list(g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?o WHERE {
    P:o3 P:i ?o.
    }
    """))
    assert set(l[0] for l in r) == { 2 }
    
    r = list(g.query_owlready("""
    PREFIX P: <http://www.semanticweb.org/test.owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?o WHERE {
    P:o1 P:p ?o.
    }
    """))
    assert set(l[0] for l in r) == { False }
    assert type(r[0][0]) is bool
    
    
  def test__refactor_1(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    p = n.ma_pizza
    n.ma_pizza.name = "ma_pizza_2"
    assert n.ma_pizza is None
    assert n.ma_pizza_2 is p
    assert set(n.ma_pizza_2.has_topping) == { n.ma_tomate, n.mon_frometon }
    assert p.iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza_2"
    assert world["http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza_2"] is p
    
  def test__refactor_2(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    p = n.ma_pizza
    n.ma_pizza.iri = "http://t/p"
    assert n.ma_pizza is None
    assert set(p.has_topping) == { n.ma_tomate, n.mon_frometon }
    assert p.iri == "http://t/p"
    assert world["http://t/p"] is p
    assert n.get_namespace("http://t/").p is p
        
  def test__refactor_3(self):
    world = self.new_world()
    n = world.get_ontology("http://www.semanticweb.org/jiba/ontologies/2017/0/test").load()
    
    p = n.Pizza
    n.Pizza.name = "Pizza_2"
    assert n.Pizza is None
    assert n.Pizza_2 is p
    assert p.iri == "http://www.semanticweb.org/jiba/ontologies/2017/0/test#Pizza_2"
    assert world["http://www.semanticweb.org/jiba/ontologies/2017/0/test#Pizza_2"] is p
    
  def test__refactor_4(self):
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
    self.assert_triple(c.storid, has_datetime.storid, "2017-04-19T11:28:00",  _universal_datatype_2_abbrev[datetime.datetime])
    
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
    self.assert_triple(c.storid, has_date.storid, "2017-04-19", _universal_datatype_2_abbrev[datetime.date])
    
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
    self.assert_triple(c.storid, has_time.storid, "11:28:00", _universal_datatype_2_abbrev[datetime.time])
    
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
    
    self.assert_triple(d.storid, owl_ondatatype, _universal_datatype_2_abbrev[int], None, world)
    
    d.min_exclusive = 15
    d.max_exclusive = 20
    
    list_bnode = world._get_obj_triple_sp_o(d.storid, owl_withrestrictions)
    l = list(n._parse_list_as_rdf(list_bnode))
    s = set()
    for i, ii in l:
      t = world._get_data_triples_s_pod(i)
      assert len(t) == 1
      p,o,d = t[0]
      o = from_literal(o,d)
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
    
    self.assert_triple(d.storid, owl_ondatatype, _universal_datatype_2_abbrev[str], None,  world)
    
    list_bnode = world._get_obj_triple_sp_o(d.storid, owl_withrestrictions)
    l = list(n._parse_list_as_rdf(list_bnode))
    s = set()
    for i, ii in l:
      t = world._get_data_triples_s_pod(i)
      assert len(t) == 1
      p,o,d = t[0]
      o = from_literal(o,d)
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
    self.assert_triple(r.property.storid, owl_inverse_property, P.storid, None,  world)
    
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
    
    bns = list(w._get_obj_triples_sp_o(P.storid, owl_propertychain))
    assert len(bns) == 1
    assert o._parse_list(bns[0]) == [P1, P2]
    
    P.property_chain.append(PropertyChain([P3, P4]))
    
    bns = list(w._get_obj_triples_sp_o(P.storid, owl_propertychain))
    assert len(bns) == 2
    assert o._parse_list(bns[0]) == [P1, P2]
    assert o._parse_list(bns[1]) == [P3, P4]
    
    del P.property_chain[0]
    
    bns = list(w._get_obj_triples_sp_o(P.storid, owl_propertychain))
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
    
    destroy_entity(C)
    
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
    
    assert list(C.equivalent_to.indirect()) == []
    assert list(E.equivalent_to.indirect()) == []
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
    
  def test_destroy_16(self):
    w = self.new_world()
    o = w.get_ontology("http://www.test.org/test.owl")
    
    with o:
      class C(Thing): pass
      class p(AnnotationProperty): pass
      
    destroy_entity(p)
    

  def test_observe_1(self):
    import owlready2.observe

    w = self.new_world()
    onto = w.get_ontology("http://test.org/t.owl")
    
    with onto:
      class C(Thing): pass
      class D(Thing): pass
      class p(C >> str, FunctionalProperty): pass
      class ps(C >> int): pass
      
    c = C()
    
    listened = "\n"
    def listener(o, p):
      nonlocal listened
      listened += "%s %s\n" % (w._unabbreviate(o), w._unabbreviate(p))
      
    owlready2.observe.start_observing(onto)
    owlready2.observe.observe(c, listener)
    
    c.ps = [1, 2, 3]
    
    c.ps.remove(2)
    c.ps.append(4)
    
    c.p = "test"
    
    c.is_a = [D]
    
    owlready2.observe.unobserve(c, listener)
    
    c.ps = [0]
    
    assert listened == """
http://test.org/t.owl#c1 http://test.org/t.owl#ps
http://test.org/t.owl#c1 http://test.org/t.owl#ps
http://test.org/t.owl#c1 http://test.org/t.owl#ps
http://test.org/t.owl#c1 http://test.org/t.owl#ps
http://test.org/t.owl#c1 http://test.org/t.owl#ps
http://test.org/t.owl#c1 http://test.org/t.owl#p
http://test.org/t.owl#c1 http://www.w3.org/1999/02/22-rdf-syntax-ns#type
http://test.org/t.owl#c1 http://www.w3.org/1999/02/22-rdf-syntax-ns#type
"""
    
  def test_observe_2(self):
    import owlready2.observe
    
    w = self.new_world()
    onto = w.get_ontology("http://test.org/t.owl")
    
    with onto:
      class C(Thing): pass
      class D(Thing): pass
      class ps(C >> int): pass
      
    c = C()
    c.ps = [1, 2, 3]
    
    listened = set()
    def listener(o, ps):
      for p in ps:
        listened.add("%s %s" % (w._unabbreviate(o), w._unabbreviate(p)))
        
    owlready2.observe.start_observing(onto)
    owlready2.observe.observe(c.storid, listener, True, w)
    
    c.ps.remove(2)
    c.ps.append(4)
    
    c.is_a = [D]
    
    assert not listened
    
    owlready2.observe.scan_collapsed_changes()

    assert listened == {"http://test.org/t.owl#c1 http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://test.org/t.owl#c1 http://test.org/t.owl#ps"}
    
    listened = set()
    owlready2.observe.scan_collapsed_changes()
    assert not listened # Now empty
    
    owlready2.observe.unobserve(c.storid, listener, w)
    c.ps.append(5)
    owlready2.observe.scan_collapsed_changes()
    assert not listened
    
  def test_observe_3(self):
    import owlready2.observe
    
    w = self.new_world()
    onto = w.get_ontology("http://test.org/t.owl")
    
    with onto:
      class C(Thing): pass
      class D(Thing): pass
      class ps(C >> int): pass
      
    c = C()
    c.ps = [1, 2, 3]
    
    listened = set()
    def listener(o, ps):
      for p in ps:
        listened.add("%s %s" % (w._unabbreviate(o), w._unabbreviate(p)))
        
    owlready2.observe.start_observing(onto)
    owlready2.observe.observe(c, listener, True)
    
    c.ps.remove(2)
    c.ps.append(4)
    
    c.is_a = [D]
    
    assert not listened
    
    owlready2.observe.scan_collapsed_changes()
    
    assert listened == {"http://test.org/t.owl#c1 http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://test.org/t.owl#c1 http://test.org/t.owl#ps"}
    
    listened = set()
    owlready2.observe.scan_collapsed_changes()
    assert not listened # Now empty
    
    owlready2.observe.unobserve(c, listener)
    c.ps.append(5)
    owlready2.observe.scan_collapsed_changes()
    assert not listened
    
  def disabled_test_observe_4(self):
    import owlready2.observe
    
    w = self.new_world()
    onto = w.get_ontology("http://test.org/t.owl")
    
    with onto:
      class C(Thing): pass
      
    c1 = C()
    c2 = C()
    
    listened = []
    def listener(o, p):
      listened.append((o, p))
    l = owlready2.observe.InstancesOfClass(C, use_observe = True)
    owlready2.observe.start_observing(onto)
    owlready2.observe.observe(l, listener)
    
    c3 = C()

    assert listened[0][0] is l
    assert listened[0][1] == "Inverse(http://www.w3.org/1999/02/22-rdf-syntax-ns#type)"
    assert list(listened[0][2]) == [c1, c2, c3]
    assert list(listened[0][3]) == [c1, c2]
    
    assert list(l) == [c1, c2, c3]
    
  def disabled_test_observe_5(self):
    import owlready2.observe
    
    w = self.new_world()
    onto = w.get_ontology("http://test.org/t.owl")
    
    with onto:
      class C(Thing): pass
      
    c1 = C()
    c2 = C()
    
    listened = []
    def listener(o, p, new, old):
      listened.append((o, p, new, old))
    l = owlready2.observe.InstancesOfClass(C, use_observe = True)
    len(l)
    owlready2.observe.start_observing(onto)
    owlready2.observe.observe(l, listener)
    
    c3 = C()

    assert listened[0][0] is l
    assert listened[0][1] == "Inverse(http://www.w3.org/1999/02/22-rdf-syntax-ns#type)"
    assert list(listened[0][2]) == [c1, c2, c3]
    assert list(listened[0][3]) == [c1, c2]
    
    assert list(l) == [c1, c2, c3]
    
  def disabled_test_observe_6(self):
    import owlready2.observe
    
    w = self.new_world()
    onto = w.get_ontology("http://test.org/t.owl")
    
    with onto:
      class C(Thing): pass
      
    c1 = C()
    c2 = C()
    
    listened = []
    
    def listener(o, diffs):
      listened.extend(diffs)
    l = owlready2.observe.InstancesOfClass(C, use_observe = True)
    owlready2.observe.start_observing(onto)
    owlready2.observe.observe(l, listener, True)
    
    c3 = C()
    c4 = C()
    
    assert listened == []
    owlready2.observe.scan_collapsed_changes()
    
    assert listened[0][0] == "Inverse(http://www.w3.org/1999/02/22-rdf-syntax-ns#type)"
    assert list(listened[0][1]) == [c1, c2, c3, c4]
    assert list(listened[0][2]) == [c1, c2]
    
    assert list(l) == [c1, c2, c3, c4]
    
  def test_observe_7(self):
    import owlready2.observe
    
    w = self.new_world()
    onto = w.get_ontology("http://test.org/t.owl")
    
    with onto:
      class C(Thing): pass
      c1 = C()
      c2 = C()
      c2.label.en = "AAA ?"
      c2.label.fr = "Paracétamol"
      c3 = C()
      c3.label.en = "Asprine"
      c3.label.fr = "Asprin"
      
    l = owlready2.observe.InstancesOfClass(C, order_by = "label", lang = "fr", use_observe = True)
    assert list(l) == [c1, c3, c2]
    
    l = owlready2.observe.InstancesOfClass(C, order_by = "label", lang = "en", use_observe = True)
    assert list(l) == [c1, c2, c3]
    
    
  def test_fts_1(self):
    world = self.new_world()
    onto = world.get_ontology("http://test.org/t.owl")
    with onto:
      class C(Thing): pass
      
      c1 = C(label = ["Maladies du rein"])
      c2 = C(label = ["Cander du rein", "Cancer rénal"])
      c3 = C(label = ["Insuffisance rénale"])
      c4 = C(label = ["Insuffisance cardiaque"])
      
    world.full_text_search_properties.append(label)
    
    # Normal search
    assert set(world.search(label = "Maladies du rein")) == { c1 }
    assert set(world.search(label = "rein")) == set()
    
    # FTS search
    assert set(world.search(label = FTS("rein"))) == { c1, c2 }
    assert set(world.search(label = FTS("rénal"))) == { c2 }
    assert set(world.search(label = FTS("rénale"))) == { c3 }
    assert set(world.search(label = FTS("rénal*"))) == { c2, c3 }
    assert set(world.search(label = FTS("insuffisance*"))) == { c3, c4 }
    assert set(world.search(label = FTS("maladies rein"))) == { c1 }
    
    world.full_text_search_properties.remove(label)
    
  def test_fts_2(self):
    world = self.new_world()
    onto = world.get_ontology("http://test.org/t.owl")
    with onto:
      class C(Thing): pass
      class p(C >> str): pass
      
    world.full_text_search_properties.append(p)
    
    c1 = C(p = ["Maladies du rein"])
    c2 = C(p = ["Cander du rein", "Cancer rénal"])
    c3 = C(p = ["Insuffisance rénale"])
    c4 = C(p = ["Insuffisance cardiaque"])
    
    # Normal search
    assert set(world.search(p = "Maladies du rein")) == { c1 }
    assert set(world.search(p = "rein")) == set()
    
    # FTS search
    assert set(world.search(p = FTS("rein"))) == { c1, c2 }
    assert set(world.search(p = FTS("rénal"))) == { c2 }
    assert set(world.search(p = FTS("rénale"))) == { c3 }
    assert set(world.search(p = FTS("rénal*"))) == { c2, c3 }
    assert set(world.search(p = FTS("insuffisance*"))) == { c3, c4 }
    assert set(world.search(p = FTS("maladies rein"))) == { c1 }
    
    destroy_entity(c2)
    assert set(world.search(p = FTS("rénal*"))) == { c3 }
    
    c4.p = ["Insuffisance hépatique"]
    
    assert set(world.search(p = FTS("insuffisance cardi*"))) == set()
    assert set(world.search(p = FTS("insuffisance"))) == { c3, c4 }
    assert set(world.search(p = FTS("hépatique"))) == { c4 }
    
    world.full_text_search_properties.remove(p)

  def test_fts_3(self):
    tmp = self.new_tmp_file()
    world = self.new_world()
    world.set_backend(filename = tmp)
    onto = world.get_ontology("http://test.org/t.owl#")
    with onto:
      class C(Thing): pass
      class p(C >> str): pass
      
    world.full_text_search_properties.append(p)
    world.full_text_search_properties.append(label)
    
    C("c1", p = ["Maladies du rein"])
    C("c2", p = ["Cander du rein", "Cancer rénal"])
    C("c3", label = ["Insuffisance rénale"])
    C("c4", label = ["Insuffisance cardiaque"])

    S = p.storid
    
    world.save()
    world.close()
    world = None
    
    world2 = self.new_world()
    world2.set_backend(filename = tmp)
    
    assert set(world2.full_text_search_properties) == { world2["http://test.org/t.owl#p"], label }
    
    assert set(world2.search(p = FTS("rein"))) == { world2["http://test.org/t.owl#c1"], world2["http://test.org/t.owl#c2"] }
    assert set(world2.search(label = FTS("insuffisance*"))) == { world2["http://test.org/t.owl#c3"], world2["http://test.org/t.owl#c4"] }
    
  def test_fts_4(self):
    tmp = self.new_tmp_file()
    world = self.new_world()
    world.set_backend(filename = tmp)
    onto = world.get_ontology("http://test.org/t.owl#")
    with onto:
      class C(Thing): pass
      class p(C >> str): pass
      class q(C >> str): pass
      
    world.full_text_search_properties.append(p)
    
    c1 = C(p = ["Maladies du rein"])
    c2 = C(q = ["Maladies du rein"])
    
    assert set(world.search(p = FTS("rein"))) == { c1 }
    
    destroy_entity(c1)
    
    assert set(world.search(p = FTS("rein"))) == set()
    
  def test_fts_5(self):
    tmp = self.new_tmp_file()
    world = self.new_world()
    world.set_backend(filename = tmp)
    onto = world.get_ontology("http://test.org/t.owl#")
    with onto:
      class C(Thing): pass
      class p(C >> str, FunctionalProperty): pass
      
    world.full_text_search_properties.append(p)
    
    c1 = C(p = "Maladies du coeur")
    c1.p = "Maladies du rein"
    
    assert set(world.search(p = FTS("rein"))) == { c1 }
    
  def test_fts_6(self):
    tmp = self.new_tmp_file()
    world = self.new_world()
    world.set_backend(filename = tmp)
    onto = world.get_ontology("http://test.org/t.owl#")
    with onto:
      class C(Thing): pass
      
    world.full_text_search_properties.append(label)
    
    c1 = C(label = [locstr("Maladies du coeur", "fr"), locstr("Heart disorders", "en")])
    c2 = C(label = [locstr("Maladies du rein", "fr"), locstr("Kidney disorders", "en")])
    
    assert set(world.search(label = FTS("coeur"))) == { c1 }
    assert set(world.search(label = FTS("kidney"))) == { c2 }
    assert set(world.search(label = FTS("coeur", "fr"))) == { c1 }
    assert set(world.search(label = FTS("coeur", "en"))) == set()

    
class Paper(BaseTest, unittest.TestCase):
  def test_reasoning_paper_ic2017(self):
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
    
    assert MaladieHémorragique in Maladie_CI_avec_m.equivalent_to.indirect()
    assert issubclass(MaladieHémorragique, Maladie_CI_avec_m)
    
  def test_reasoning_paper_5(self):
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

  def test_reasoning_paper_ic2015(self):
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


# Add test for Pellet

for Class in [Test, Paper]:
  if Class:
    for name, func in list(Class.__dict__.items()):
      if name.startswith("test_reasoning"):
        def test_pellet(self, func = func):
          global sync_reasoner
          sync_reasoner = sync_reasoner_pellet
          func(self)
          sync_reasoner = sync_reasoner_hermit
        setattr(Class, "%s_pellet" % name, test_pellet)

del Class # Else, it is considered as an additional test class!
        
if __name__ == '__main__': unittest.main()
  
