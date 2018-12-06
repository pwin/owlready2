# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2018 Jean-Baptiste LAMY
# LIMICS (Laboratoire d'informatique médicale et d'ingénierie des connaissances en santé), UMR_S 1142
# University Paris 13, Sorbonne paris-Cité, Bobigny, France

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import importlib

from owlready2.base import *
from owlready2.base import _universal_abbrev_2_iri, _universal_iri_2_abbrev, _universal_abbrev_2_datatype, _universal_datatype_2_abbrev

from owlready2.triplelite import *

CURRENT_NAMESPACES = [None]


_LOG_LEVEL = 0
def set_log_level(x):
  global _LOG_LEVEL
  _LOG_LEVEL = x
  
class Namespace(object):  
  def __init__(self, world_or_ontology, base_iri, name = None):
    if not(base_iri.endswith("#") or base_iri.endswith("/")): raise ValueError("base_iri must end with '#' or '/' !")
    name = name or base_iri[:-1].rsplit("/", 1)[-1]
    if name.endswith(".owl") or name.endswith(".rdf"): name = name[:-4]
    
    if   isinstance(world_or_ontology, Ontology):
      self.ontology = world_or_ontology
      self.world    = world_or_ontology.world
      self.ontology._namespaces[base_iri] = self
      
    elif isinstance(world_or_ontology, World):
      self.ontology = None
      self.world    = world_or_ontology
      self.world._namespaces[base_iri] = self
      
    else:
      self.ontology = None
      self.world    = None
      
    self.base_iri = base_iri
    self.name     = name
    
  def __enter__(self):
    if self.ontology is None: raise ValueError("Cannot assert facts in this namespace: it is not linked to an ontology! (it is probably a global namespace created by get_namespace(); please use your_ontology.get_namespace() instead)")
    if self.world.graph: self.world.graph.acquire_write_lock()
    CURRENT_NAMESPACES.append(self)
    
  def __exit__(self, exc_type = None, exc_val = None, exc_tb = None):
    del CURRENT_NAMESPACES[-1]
    if self.world.graph: self.world.graph.release_write_lock()
    
  def __repr__(self): return """%s.get_namespace("%s")""" % (self.ontology, self.base_iri)
  
  def __getattr__(self, attr): return self.world["%s%s" % (self.base_iri, attr)] #return self[attr]
  def __getitem__(self, name): return self.world["%s%s" % (self.base_iri, name)]
  

class _GraphManager(object):
  def _abbreviate  (self, iri):
    return _universal_iri_2_abbrev.get(iri, iri)
  def _unabbreviate(self, abb):
    return _universal_abbrev_2_iri.get(abb, abb)
  
  def _get_obj_triple_sp_o(self, subject, predicate): return None
  def _get_obj_triple_po_s(self, predicate, object): return None
  def _get_data_triples_sp_od(self, subject, predicate): return []
  
  def _get_obj_triples_transitive_sp (self, subject, predicate, already = None): return set()
  def _get_obj_triples_transitive_po (self, predicate, object, already = None): return set()
  def _get_obj_triples_transitive_sym(self, subject, predicate): return set()
  def _get_obj_triples_transitive_sp_indirect(self, subject, predicates_inverses, already = None): return set()
  def _get_obj_triples_spo_spo(self, subject = None, predicate = None, object = None): return []
  _get_triples_s_p = _get_obj_triples_spo_spo
  
  def _has_data_triple_spod(self, subject = None, predicate = None, object = None, d = ""): return False
  _has_obj_triple_spo = _has_data_triple_spod
  
  def _get_obj_triples_cspo(self, subject = None, predicate = None, object = None, ontology_graph = None): return []
  def _get_obj_triples_sp_o(self, subject, predicate): return []
  def _get_obj_triples_sp_co(self, s, p): return []
  #def get_equivs_s_o(self, s): return [s]
  def _get_triples_sp_od(self, s, p): return []
  
  def get_triples(self, s = None, p = None, o = None):
    if   isinstance(o, int):
      return self._get_obj_triples_spo_spo(s, p, o)
    elif isinstance(o, str):
      from owlready2.driver import INT_DATATYPES, FLOAT_DATATYPES
      o, d = o.rsplit('"', 1)
      o = o[1:]
      if   d.startswith("@"): pass
      elif d.startswith("^"):
        d = d[3:-1]
        if   d in INT_DATATYPES:   o = int  (o)
        elif d in FLOAT_DATATYPES: o = float(o)
        d = self._abbreviate(d)
      else:                   d = 0
      print((s, p, o, d))
      return self._get_data_triples_spod_spod(s, p, o, d)
    else:
      r = []
      for s,p,o,d in self._get_triples_spod_spod(s, p, None, None):
        if   d == 0:             o = '"%s"'       %  o
        elif isinstance(d, int): o = '"%s"^^<%s>' % (o, self._unabbreviate(d))
        elif isinstance(d, str): o = '"%s"%s'     % (o, d)
        r.append((s,p,o))
      return r
    
  def _refactor(self, storid, new_iri): pass
  
  def _get_annotation_axioms(self, source, property, target, target_d):
    if target_d is None:
      for bnode in self._get_obj_triples_po_s(rdf_type, owl_axiom):
        for p, o in self._get_obj_triples_s_po(bnode):
          if   p == owl_annotatedsource: # SIC! If on a single if, elif are not appropriate.
            if o != source: break
          elif p == owl_annotatedproperty:
            if o != property: break
          elif p == owl_annotatedtarget:
            if o != target: break
        else:
          yield bnode
    else:
      for bnode in self._get_obj_triples_po_s(rdf_type, owl_axiom):
        for p, o, d in self._get_triples_s_pod(bnode):
          if   p == owl_annotatedsource: # SIC! If on a single if, elif are not appropriate.
            if o != source: break
          elif p == owl_annotatedproperty:
            if o != property: break
          elif p == owl_annotatedtarget:
            if o != target: break
        else:
          yield bnode
          
  def _del_obj_triple_spod(self, s = None, p = None, o = None):
    if CURRENT_NAMESPACES[-1] is None: self._del_obj_triple_raw_spo(s, p, o)
    else:   CURRENT_NAMESPACES[-1].ontology._del_obj_triple_raw_spo(s, p, o)
    if _LOG_LEVEL > 1:
      if not s < 0: s = self._unabbreviate(s)
      if p: p = self._unabbreviate(p)
      if o and not (o < 0 or o.startswith('"')): o = self._unabbreviate(o)
      print("* Owlready2 * DEL TRIPLE", s, p, o, file = sys.stderr)
      
  def _del_data_triple_spoddd(self, s = None, p = None, o = None, d = None):
    if CURRENT_NAMESPACES[-1] is None: self._del_data_triple_raw_spodd(s, p, o, d)
    else:   CURRENT_NAMESPACES[-1].ontology._del_data_triple_raw_spodd(s, p, o, d)
    if _LOG_LEVEL > 1:
      if not s < 0: s = self._unabbreviate(s)
      if p: p = self._unabbreviate(p)
      if d and (not d.startswith("@")): d = self._unabbreviate(d)
      print("* Owlready2 * DEL TRIPLE", s, p, o, d, file = sys.stderr)
      
  def _parse_list(self, bnode):
    l = []
    while bnode and (bnode != rdf_nil):
      first, d = self._get_triple_sp_od(bnode, rdf_first)
      if first != rdf_nil: l.append(self._to_python(first, d))
      bnode = self._get_obj_triple_sp_o(bnode, rdf_rest)
    return l
  
  def _parse_list_as_rdf(self, bnode):
    while bnode and (bnode != rdf_nil):
      first, d = self._get_triple_sp_od(bnode, rdf_first)
      if first != rdf_nil: yield first, d
      bnode = self._get_obj_triple_sp_o(bnode, rdf_rest)
      
  def _to_python(self, o, d = None, main_type = None, main_onto = None, default_to_none = False):
    if d is None:
      if   o < 0: return self._parse_bnode(o)
      if   o in _universal_abbrev_2_datatype: return _universal_abbrev_2_datatype[o] 
      else: return self.world._get_by_storid(o, None, main_type, main_onto, None, default_to_none)
    else: return from_literal(o, d)
    raise ValueError
  
  def _to_rdf(self, o):
    if hasattr(o, "storid"): return o.storid, None
    d = _universal_datatype_2_abbrev.get(o)
    if not d is None: return d, None
    return to_literal(o)
  
  def classes(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_class):
      if not s < 0: yield self.world._get_by_storid(s)
      
  def inconsistent_classes(self):
    for s in self._get_obj_triples_transitive_sym(owl_nothing, owl_equivalentclass):
      if not s < 0: yield self.world._get_by_storid(s)
      
  def data_properties(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_data_property):
      if not s < 0: yield self.world._get_by_storid(s)
  def object_properties(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_object_property):
      if not s < 0: yield self.world._get_by_storid(s)
  def annotation_properties(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_annotation_property):
      if not s < 0: yield self.world._get_by_storid(s)
  def properties(self): return itertools.chain(self.data_properties(), self.object_properties(), self.annotation_properties())
  
  def individuals(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_named_individual):
      if not s < 0:
        i = self.world._get_by_storid(s)
        if isinstance(i, Thing):
          yield i
          
  def disjoint_classes(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_alldisjointclasses):
      yield self._parse_bnode(s)
    for c,s,p,o in self._get_obj_triples_cspo_cspo(None, None, owl_disjointwith, None):
      with LOADING: a = AllDisjoint((s, p, o), self.world.graph.context_2_user_context(c), None)
      yield a # Must yield outside the with statement
      
  def disjoint_properties(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_alldisjointproperties):
      yield self._parse_bnode(s)
    for c,s,p,o in self._get_obj_triples_cspo_cspo(None, None, owl_propdisjointwith, None):
      with LOADING: a = AllDisjoint((s, p, o), self.world.graph.context_2_user_context(c), None)
      yield a # Must yield outside the with statement
      
  def different_individuals(self):
    for s in self._get_obj_triples_po_s(rdf_type, owl_alldifferent):
      yield self._parse_bnode(s)
      
  def disjoints(self): return itertools.chain(self.disjoint_classes(), self.disjoint_properties(), self.different_individuals())

  def general_axioms(self):
    for s in itertools.chain(self._get_obj_triples_po_s(rdf_type, owl_restriction),
                             self._get_obj_triples_po_s(rdf_type, owl_class),
                             ):
      if s < 0:
        sub = self._get_obj_triple_po_s(rdfs_subclassof, s)
        if sub is None: yield self._parse_bnode(s)
        
  def search(self, _use_str_as_loc_str = True, debug = False, **kargs):
    from owlready2.triplelite import _SearchList
    
    prop_vals = []
    for k, v0 in kargs.items():
      if isinstance(v0, _SearchList) or not isinstance(v0, list): v0 = (v0,)
      for v in v0:
        if   k == "iri":
          prop_vals.append((" iri", v, None))
        elif (k == "is_a") or (k == "subclass_of") or (k == "type"):
          if isinstance(v, _SearchList): v2 = v
          else:                          v2 = [child.storid for child in v.descendants()]
          prop_vals.append((" %s" % k, v2, None))
        else:
          d = None
          k2 = self.world._props.get(k)
          if k2 is None:
            k2 = _universal_iri_2_abbrev.get(k) or k
          else:
            if k2.inverse_property:
              k2 = (k2.storid, k2.inverse.storid)
            else:
              k2 = k2.storid
          if v is None:
            v2 = None
          else:
            if   isinstance(v, FTS):  v2 = v; d = "*"
            elif isinstance(v, NumS): v2 = v; d = "*"
            elif isinstance(v, _SearchList): v2 = v
            else:
              v2, d = self.world._to_rdf(v)
              if ((not d is None) and (isinstance(v2, (int, float)))) or (_use_str_as_loc_str and (d == 60)): # A string, which can be associated to a language in RDF
                d = "*"
          prop_vals.append((k2, v2, d))
          
    #r = self.graph.search(prop_vals, debug = debug)
    #return self.world._get_by_storid(o) for (o,) in r if not o < 0]
    return _SearchList(self.world, prop_vals)
    
  def search_one(self, **kargs): return self.search(**kargs).first()
    
  
onto_path = []

owl_world = None

_cache = [None] * (2 ** 16) #50000
_cache_index = 0

class World(_GraphManager):
  def __init__(self, backend = "sqlite", filename = ":memory:", dbname = "owlready2_quadstore", **kargs):
    global owl_world
    
    self.world            = self
    self.filename         = filename
    self.ontologies       = {}
    self._props           = {}
    self._reasoning_props = {}
    self._entities        = weakref.WeakValueDictionary()
    self._namespaces      = weakref.WeakValueDictionary()
    self._rdflib_store    = None
    self.graph            = None
    
    if not owl_world is None:
      self._entities.update(owl_world._entities) # add OWL entities in the world
      self._props.update(owl_world._props)
      
    if filename:
      self.set_backend(backend, filename, dbname, **kargs)
      
  def set_backend(self, backend = "sqlite", filename = ":memory:", dbname = "owlready2_quadstore", **kargs):
    if   backend == "sqlite":
      from owlready2.triplelite import Graph
      if self.graph and len(self.graph):
        self.graph = Graph(filename, world = self, clone = self.graph, **kargs)
      else:
        self.graph = Graph(filename, world = self, **kargs)
    else:
      raise ValueError("Unsupported backend type '%s'!" % backend)
    for method in self.graph.__class__.BASE_METHODS + self.graph.__class__.WORLD_METHODS:
      setattr(self, method, getattr(self.graph, method))
    
    self.filename = filename
    
    for ontology in self.ontologies.values():
      ontology.graph, new_in_quadstore = self.graph.sub_graph(ontology)
      for method in ontology.graph.__class__.BASE_METHODS + ontology.graph.__class__.ONTO_METHODS:
        setattr(ontology, method, getattr(ontology.graph, method))
        
    for iri in self.graph.ontologies_iris():
      self.get_ontology(iri) # Create all possible ontologies if not yet done

    self._full_text_search_properties = CallbackList([self._get_by_storid(storid, default_to_none = True) or storid for storid in self.graph.get_fts_prop_storid()], self, World._full_text_search_changed)
    
  def close(self): self.graph.close()
  
  def get_full_text_search_properties(self): return self._full_text_search_properties
  def set_full_text_search_properties(self, l):
    old = self._full_text_search_properties
    self._full_text_search_properties = CallbackList(l, self, World._full_text_search_changed)
    self._full_text_search_changed(old)
  full_text_search_properties = property(get_full_text_search_properties, set_full_text_search_properties)
  def _full_text_search_changed(self, old):
    old = set(old)
    new = set(self._full_text_search_properties)
    for Prop in old - new:
      self.graph.disable_full_text_search(Prop.storid)
    for Prop in new - old:
      self.graph.enable_full_text_search(Prop.storid)
  
  def new_blank_node(self): return self.graph.new_blank_node()
  
  def save(self, file = None, format = "rdfxml", **kargs):
    if   file is None:
      self.graph.commit()
    elif isinstance(file, str):
      if _LOG_LEVEL: print("* Owlready2 * Saving world %s to %s..." % (self, file), file = sys.stderr)
      file = open(file, "wb")
      self.graph.save(file, format, **kargs)
      file.close()
    else:
      if _LOG_LEVEL: print("* Owlready2 * Saving world %s to %s..." % (self, getattr(file, "name", "???")), file = sys.stderr)
      self.graph.save(file, format, **kargs)
      
  def as_rdflib_graph(self):
    if self._rdflib_store is None:
      import owlready2.rdflib_store
      self._rdflib_store = owlready2.rdflib_store.TripleLiteRDFlibStore(self)
    return self._rdflib_store.main_graph

  def sparql_query(self, sparql):
    g = self.as_rdflib_graph()
    r = g.query(sparql)
    for row in r:
      yield tuple(g.store._2_python(x) for x in row)
      
      
  def get_ontology(self, base_iri):
    if (not base_iri.endswith("/")) and (not base_iri.endswith("#")):
      if   ("%s#" % base_iri) in self.ontologies: base_iri = base_iri = "%s#" % base_iri
      elif ("%s/" % base_iri) in self.ontologies: base_iri = base_iri = "%s/" % base_iri
      else:                                       base_iri = base_iri = "%s#" % base_iri
    if base_iri in self.ontologies: return self.ontologies[base_iri]
    return Ontology(self, base_iri)
  
  def get_namespace(self, base_iri, name = ""):
    if (not base_iri.endswith("/")) and (not base_iri.endswith("#")):
      if   ("%s#" % base_iri) in self.ontologies: base_iri = base_iri = "%s#" % base_iri
      elif ("%s/" % base_iri) in self.ontologies: base_iri = base_iri = "%s/" % base_iri
      else:                                       base_iri = base_iri = "%s#" % base_iri
    if base_iri in self._namespaces: return self._namespaces[base_iri]
    return Namespace(self, base_iri, name or base_iri[:-1].rsplit("/", 1)[-1])
    
  
  def get(self, iri):
    return self._entities.get(self._abbreviate(iri))
  
  def __getitem__(self, iri):
    return self._get_by_storid(self._abbreviate(iri), iri)
  
  def _get_by_storid(self, storid, full_iri = None, main_type = None, main_onto = None, trace = None, default_to_none = True):
    entity = self._entities.get(storid)
    if not entity is None: return entity
    
    try:
      return self._load_by_storid(storid, full_iri, main_type, main_onto, default_to_none)
    except RecursionError:
      return self._load_by_storid(storid, full_iri, main_type, main_onto, default_to_none, ())
    
  def _load_by_storid(self, storid, full_iri = None, main_type = None, main_onto = None, default_to_none = True, trace = None):
    with LOADING:
      types       = []
      is_a_bnodes = []
      for graph, obj in self._get_obj_triples_sp_co(storid, rdf_type):
        if main_onto is None: main_onto = self.graph.context_2_user_context(graph)
        if   obj == owl_class:               main_type = ThingClass
        elif obj == owl_object_property:     main_type = ObjectPropertyClass;     types.append(ObjectProperty)
        elif obj == owl_data_property:       main_type = DataPropertyClass;       types.append(DataProperty)
        elif obj == owl_annotation_property: main_type = AnnotationPropertyClass; types.append(AnnotationProperty)
        elif (obj == owl_named_individual) or (obj == owl_thing):
          if main_type is None: main_type = Thing
        else:
          if not main_type: main_type = Thing
          if obj < 0: is_a_bnodes.append((self.graph.context_2_user_context(graph), obj))
          else:
            Class = self._get_by_storid(obj, None, ThingClass, main_onto)
            if isinstance(Class, EntityClass): types.append(Class)
            elif Class is None: raise ValueError("Cannot get '%s'!" % obj)
            
      if main_type is None: # Try to guess it
        if   self._has_obj_triple_spo(None, rdf_type, storid) or self._has_obj_triple_spo(None, rdfs_subclassof, storid): main_type = ThingClass
        elif self._has_obj_triple_spo(storid, None, None) or self._has_data_triple_spod(storid, None, None, ""): main_type = Thing
        
      if main_type and (not main_type is Thing):
        if not trace is None:
            if storid in trace:
              s = "\n  ".join([(i if i < 0 else self._unabbreviate(i)) for i in trace[trace.index(storid):]])
              print("* Owlready2 * Warning: ignoring cyclic subclass of/subproperty of, involving:\n  %s\n" % s, file = sys.stderr)
              return None
            trace = (*trace, storid)
            
        is_a_entities = []
        for graph, obj in self._get_obj_triples_sp_co(storid, main_type._rdfs_is_a):
          if obj < 0: is_a_bnodes.append((self.graph.context_2_user_context(graph), obj))
          else:
            obj2 = self._entities.get(obj)
            if obj2 is None: obj2 = self._load_by_storid(obj, None, main_type, main_onto, default_to_none, trace)
            if not obj2 is None: is_a_entities.append(obj2)
            
      if main_onto is None:
        main_onto = self.get_ontology("http://anonymous/")
        full_iri = full_iri or self._unabbreviate(storid)
        if full_iri.startswith(owl.base_iri) or full_iri.startswith(rdfs.base_iri) or full_iri.startswith("http://www.w3.org/1999/02/22-rdf-syntax-ns#"): return None
        
      if main_onto:
        full_iri = full_iri or self._unabbreviate(storid)
        splitted = full_iri.rsplit("#", 1)
        if len(splitted) == 2:
          namespace = main_onto.get_namespace("%s#" % splitted[0])
          name = splitted[1]
        else:
          splitted = full_iri.rsplit("/", 1)
          if len(splitted) == 2:
            namespace = main_onto.get_namespace("%s/" % splitted[0])
            name = splitted[1]
          else:
            namespace = main_onto.get_namespace("")
            name = full_iri
            
            
      # Read and create with classes first, but not construct, in order to break cycles.
      if   main_type is ThingClass:
        types = tuple(is_a_entities) or (Thing,)
        entity = ThingClass(name, types, { "namespace" : namespace, "storid" : storid } )
        
      elif main_type is ObjectPropertyClass:
        try:
          types = tuple(t for t in types if t.iri != "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property")
          entity = ObjectPropertyClass(name, types or (ObjectProperty,), { "namespace" : namespace, "is_a" : is_a_entities, "storid" : storid } )
        except TypeError as e:
          if e.args[0].startswith("metaclass conflict"):
            print("* Owlready2 * WARNING: %s belongs to more than one entity types (e.g. Class, Property, Individual): %s; I'm trying to fix it..." % (full_iri, list(types) + is_a_entities), file = sys.stderr)
            is_a_entities = [t for t in is_a_entities if issubclass_python(t, ObjectProperty)]
            entity = ObjectPropertyClass(name, types or (ObjectProperty,), { "namespace" : namespace, "is_a" : is_a_entities, "storid" : storid } )
            
      elif main_type is DataPropertyClass:
        try:
          types = tuple(t for t in types if t.iri != "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property")
          entity = DataPropertyClass(name, types or (DataProperty,), { "namespace" : namespace, "is_a" : is_a_entities, "storid" : storid } )
        except TypeError as e:
          if e.args[0].startswith("metaclass conflict"):
            print("* Owlready2 * WARNING: %s belongs to more than one entity types (e.g. Class, Property, Individual): %s; I'm trying to fix it..." % (full_iri, list(types) + is_a_entities), file = sys.stderr)
            is_a_entities = [t for t in is_a_entities if issubclass_python(t, DataProperty)]
            entity = DataPropertyClass(name, types or (DataProperty,), { "namespace" : namespace, "is_a" : is_a_entities, "storid" : storid } )
            
      elif main_type is AnnotationPropertyClass:
        types = tuple(t for t in types if t.iri != "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property")
        entity = AnnotationPropertyClass(name, types or (AnnotationProperty,), { "namespace" : namespace, "is_a" : is_a_entities, "storid" : storid } )
        
      elif main_type is Thing:
        if   len(types) == 1: Class = types[0]
        elif len(types) >  1: Class = FusionClass._get_fusion_class(types)
        else:                 Class = Thing
        entity = Class(name, namespace = namespace)
        
      else:
        if default_to_none: return None
        return full_iri or self._unabbreviate(storid)
      
      if is_a_bnodes:
        list.extend(entity.is_a, (onto._parse_bnode(bnode) for onto, bnode in is_a_bnodes))
        
    global _cache, _cache_index
    _cache[_cache_index] = entity
    _cache_index += 1
    if _cache_index >= len(_cache): _cache_index = 0
    
    return entity
  
  def _parse_bnode(self, bnode):
    for ontology in self.ontologies.values():
      if ontology._has_obj_triple_spo(bnode, None, None):
        return ontology._parse_bnode(bnode)
      
     
class Ontology(Namespace, _GraphManager):
  def __init__(self, world, base_iri, name = None):
    self.world       = world # Those 2 attributes are required before calling Namespace.__init__
    self._namespaces = weakref.WeakValueDictionary()
    Namespace.__init__(self, self, base_iri, name)
    self.loaded                = False
    self._bnodes               = weakref.WeakValueDictionary()
    self.storid                = world._abbreviate(base_iri[:-1])
    self._imported_ontologies  = CallbackList([], self, Ontology._import_changed)
    self.metadata              = Metadata(self, self.storid)
    
    if world.graph is None:
      self.graph = None
    else:
      self.graph, new_in_quadstore = world.graph.sub_graph(self)
      for method in self.graph.__class__.BASE_METHODS + self.graph.__class__.ONTO_METHODS:
        setattr(self, method, getattr(self.graph, method))
      if not new_in_quadstore:
        self._load_properties()
        
    world.ontologies[self.base_iri] = self
    if _LOG_LEVEL: print("* Owlready2 * Creating new ontology %s <%s>." % (self.name, self.base_iri), file = sys.stderr)
    
    if (not LOADING) and (not self.graph is None):
      if not self._has_obj_triple_spo(self.storid, rdf_type, owl_ontology):
        if self.world.graph: self.world.graph.acquire_write_lock()
        self._add_obj_triple_spo(self.storid, rdf_type, owl_ontology)
        if self.world.graph: self.world.graph.release_write_lock()
        
  def destroy(self):
    self.world.graph.acquire_write_lock()
    del self.world.ontologies[self.base_iri]
    self.graph.destroy()
    for entity in list(self.world._entities.values()):
      if entity.namespace.ontology is self: del self.world._entities[entity.storid]
    self.world.graph.release_write_lock()
    
  def get_imported_ontologies(self): return self._imported_ontologies
  def set_imported_ontologies(self, l):
    old = self._imported_ontologies
    self._imported_ontologies = CallbackList(l, self, Ontology._import_changed)
    self._import_changed(old)
  imported_ontologies = property(get_imported_ontologies, set_imported_ontologies)
    
  def _import_changed(self, old):
    old = set(old)
    new = set(self._imported_ontologies)
    for ontology in old - new:
      self._del_obj_triple_spod(self.storid, owl_imports, ontology.storid)
    for ontology in new - old:
      self._add_obj_triple_spo(self.storid, owl_imports, ontology.storid)
      
  def get_namespace(self, base_iri, name = ""):
    if (not base_iri.endswith("/")) and (not base_iri.endswith("#")): base_iri = "%s#" % base_iri
    r = self._namespaces.get(base_iri)
    if not r is None: return r
    return Namespace(self, base_iri, name or base_iri[:-1].rsplit("/", 1)[-1])
  
  def __exit__(self, exc_type = None, exc_val = None, exc_tb = None):
    Namespace.__exit__(self, exc_type, exc_val, exc_tb)
    if not self.loaded:
      self.loaded = True
      if self.graph: self.graph.set_last_update_time(time.time())
      
  def load(self, only_local = False, fileobj = None, reload = False, reload_if_newer = False, **args):
    if self.loaded and (not reload): return self
    if self.base_iri == "http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#":
      f = os.path.join(os.path.dirname(__file__), "owlready_ontology.owl")
    elif not fileobj:
      f = fileobj or _get_onto_file(self.base_iri, self.name, "r", only_local)
    else:
      f = ""

    self.world.graph.acquire_write_lock()
    
    new_base_iri = None
    if f.startswith("http:") or f.startswith("https:"):
      if  reload or (self.graph.get_last_update_time() == 0.0): # Never loaded
        if _LOG_LEVEL: print("* Owlready2 *     ...loading ontology %s from %s..." % (self.name, f), file = sys.stderr)
        fileobj = urllib.request.urlopen(f)
        try:     new_base_iri = self.graph.parse(fileobj, default_base = self.base_iri, **args)
        finally: fileobj.close()
    elif fileobj:
      if _LOG_LEVEL: print("* Owlready2 *     ...loading ontology %s from %s..." % (self.name, getattr(fileobj, "name", "") or getattr(fileobj, "url", "???")), file = sys.stderr)
      try:     new_base_iri = self.graph.parse(fileobj, default_base = self.base_iri, **args)
      finally: fileobj.close()
    else:
      if reload or (reload_if_newer and (os.path.getmtime(f) > self.graph.get_last_update_time())) or (self.graph.get_last_update_time() == 0.0):
        if _LOG_LEVEL: print("* Owlready2 *     ...loading ontology %s from %s..." % (self.name, f), file = sys.stderr)
        fileobj = open(f, "rb")
        try:     new_base_iri = self.graph.parse(fileobj, default_base = self.base_iri, **args)
        finally: fileobj.close()
      else:
        if _LOG_LEVEL: print("* Owlready2 *     ...loading ontology %s (cached)..." % self.name, file = sys.stderr)
        
    self.loaded = True
    
    if new_base_iri and (new_base_iri != self.base_iri):
      self.graph.add_ontology_alias(new_base_iri, self.base_iri)
      self.base_iri = new_base_iri
      self._namespaces[self.base_iri] = self.world.ontologies[self.base_iri] = self
      if new_base_iri.endswith("#"):
        self.storid = self.world._abbreviate(new_base_iri[:-1])
      else:
        self.storid = self.world._abbreviate(new_base_iri)
      self.metadata = Metadata(self, self.storid) # Metadata depends on storid
      
    elif not self.graph._has_obj_triple_spo(self.storid, rdf_type, owl_ontology): # Not always present (e.g. not in dbpedia)
      if self.world.graph: self.world.graph.acquire_write_lock()
      self._add_obj_triple_raw_spo(self.storid, rdf_type, owl_ontology)
      if self.world.graph: self.world.graph.release_write_lock()
      
    self.world.graph.release_write_lock()
    
    # Search for property names
    if self.world.graph.indexed: self._load_properties()
    
    # Load imported ontologies
    imported_ontologies = [self.world.get_ontology(self._unabbreviate(abbrev_iri)).load() for abbrev_iri in self.world._get_obj_triples_sp_o(self.storid, owl_imports)]
    self._imported_ontologies._set(imported_ontologies)
    
    # Import Python module
    for module, d in self._get_data_triples_sp_od(self.storid, owlready_python_module):
      module = from_literal(module, d)
      if _LOG_LEVEL: print("* Owlready2 *     ...importing Python module %s required by ontology %s..." % (module, self.name), file = sys.stderr)
      
      try: importlib.__import__(module)
      except ImportError:
        print("\n* Owlready2 * ERROR: cannot import Python module %s!\n" % module, file = sys.stderr)
        print("\n\n\n", file = sys.stderr)
        raise
    return self
  
  def _load_properties(self):
    props = []
    #for i in self.graph.execute("select * from quads").fetchall(): print(i)
    for prop_storid in itertools.chain(self._get_obj_triples_po_s(rdf_type, owl_object_property), self._get_obj_triples_po_s(rdf_type, owl_data_property), self._get_obj_triples_po_s(rdf_type, owl_annotation_property)):
      Prop = self.world._get_by_storid(prop_storid)
      python_name_d = self.world._get_data_triple_sp_od(prop_storid, owlready_python_name)
      
      if python_name_d is None:
        props.append(Prop.python_name)
      else:
        with LOADING: Prop.python_name = python_name_d[0]
        props.append("%s (%s)" % (Prop.python_name, Prop.name))
    if _LOG_LEVEL:
      print("* Owlready2 *     ...%s properties found: %s" % (len(props), ", ".join(props)), file = sys.stderr)
      
  
  def indirectly_imported_ontologies(self, already = None):
    already = already or set()
    if not self in already:
      already.add(self)
      yield self
      for ontology in self._imported_ontologies: yield from ontology.indirectly_imported_ontologies(already)
      
  def save(self, file = None, format = "rdfxml", **kargs):
    if   file is None:
      file = _open_onto_file(self.base_iri, self.name, "wb")
      if _LOG_LEVEL: print("* Owlready2 * Saving ontology %s to %s..." % (self.name, getattr(file, "name", "???")), file = sys.stderr)
      self.graph.save(file, format, **kargs)
      file.close()
    elif isinstance(file, str):
      if _LOG_LEVEL: print("* Owlready2 * Saving ontology %s to %s..." % (self.name, file), file = sys.stderr)
      file = open(file, "wb")
      self.graph.save(file, format, **kargs)
      file.close()
    else:
      if _LOG_LEVEL: print("* Owlready2 * Saving ontology %s to %s..." % (self.name, getattr(file, "name", "???")), file = sys.stderr)
      self.graph.save(file, format, **kargs)
      
  def _add_obj_triple_spo(self, s, p, o):
    if CURRENT_NAMESPACES[-1] is None: self._add_obj_triple_raw_spo(s, p, o)
    else:   CURRENT_NAMESPACES[-1].ontology._add_obj_triple_raw_spo(s, p, o)
    if _LOG_LEVEL > 1:
      if not s < 0: s = self._unabbreviate(s)
      if p: p = self._unabbreviate(p)
      if o > 0: o = self._unabbreviate(o)
      print("* Owlready2 * ADD TRIPLE", s, p, o, file = sys.stderr)
      
  def _set_obj_triple_spo(self, s, p, o):
    if CURRENT_NAMESPACES[-1] is None: self._set_obj_triple_raw_spo(s, p, o)
    else:   CURRENT_NAMESPACES[-1].ontology._set_obj_triple_raw_spo(s, p, o)
    if _LOG_LEVEL > 1:
      if not s < 0: s = self._unabbreviate(s)
      if p: p = self._unabbreviate(p)
      if o > 0: o = self._unabbreviate(o)
      print("* Owlready2 * SET TRIPLE", s, p, o, file = sys.stderr)
      
  def _add_data_triple_spoddd(self, s, p, o, d):
    if CURRENT_NAMESPACES[-1] is None: self._add_data_triple_raw_spodd(s, p, o, d)
    else:   CURRENT_NAMESPACES[-1].ontology._add_data_triple_raw_spodd(s, p, o, d)
    if _LOG_LEVEL > 1:
      if not s < 0: s = self._unabbreviate(s)
      if p: p = self._unabbreviate(p)
      if d and (not d.startswith("@")): d = self._unabbreviate(d)
      print("* Owlready2 * ADD TRIPLE", s, p, o, d, file = sys.stderr)
      
  def _set_data_triple_spoddd(self, s, p, o, d):
    if CURRENT_NAMESPACES[-1] is None: self._set_data_triple_raw_spodd(s, p, o, d)
    else:   CURRENT_NAMESPACES[-1].ontology._set_data_triple_raw_spodd(s, p, o, d)
    if _LOG_LEVEL > 1:
      if not s < 0: s = self._unabbreviate(s)
      if p: p = self._unabbreviate(p)
      if d and (not d.startswith("@")): d = self._unabbreviate(d)
      print("* Owlready2 * SET TRIPLE", s, p, o, d, file = sys.stderr)
    
  # Will be replaced by the graph methods
  def _add_obj_triple_raw_spo(self, subject, predicate, object): pass
  def _set_obj_triple_raw_spo(self, subject, predicate, object): pass
  def _del_obj_triple_raw_spo(self, subject, predicate, object): pass
  def _add_data_triple_raw_spodsd(self, subject, predicate, object, d): pass
  def _set_data_triple_raw_spodsd(self, subject, predicate, object, d): pass
  def _del_data_triple_raw_spodsd(self, subject, predicate, object, d): pass
    
  def _add_annotation_axiom(self, source, property, target, target_d, annot, value, d):
    for bnode in self.world._get_annotation_axioms(source, property, target, target_d):
      break # Take first
    else:
      bnode = self.world.new_blank_node() # Not found => new axiom
      self._add_obj_triple_spo(bnode, rdf_type, owl_axiom)
      self._add_obj_triple_spo(bnode, owl_annotatedsource  , source)
      self._add_obj_triple_spo(bnode, owl_annotatedproperty, property)
      if target_d is None:
        self._add_obj_triple_spo(bnode, owl_annotatedtarget, target)
      else:
        self._add_data_triple_spoddd(bnode, owl_annotatedtarget, target, target_d)
    
    if d is None: self._add_obj_triple_spo  (bnode, annot, value)
    else:         self._add_data_triple_spoddd(bnode, annot, value, d)
    return bnode
    
  
  def _del_annotation_axiom(self, source, property, target, target_d, annot, value, d):
    for bnode in self._get_obj_triples_po_s(rdf_type, owl_axiom):
      ok    = False
      other = False
      for p, o, d in self._get_triples_s_pod(bnode):
        if   p == owl_annotatedsource: # SIC! If on a single if, elif are not appropriate.
          if o != source: break
        elif p == owl_annotatedproperty:
          if o != property: break
        elif p == owl_annotatedtarget:
          if o != target: break
        elif  p == rdf_type: pass
        elif (p == annot) and (o == value): ok = True
        else: other = True
      else:
        if ok:
          if other:
            if d is None: self._del_obj_triple_spod(bnode, annot, value)
            else:         self._del_data_triple_spoddd(bnode, annot, value, None)
          else:
            self._del_obj_triple_spod  (bnode, None, None)
            self._del_data_triple_spoddd(bnode, None, None, None)
          return bnode

      
  def _parse_bnode(self, bnode):
    r = self._bnodes.get(bnode)
    if not r is None: return r
    
    with LOADING:
      restriction_property = restriction_type = restriction_cardinality = Disjoint = members = on_datatype = with_restriction = None
      for pred, obj in self._get_obj_triples_s_po(bnode):
        if   pred == owl_complementof:   r = Not(None, self, bnode); break # will parse the rest on demand
        elif pred == owl_unionof:        r = Or (obj , self, bnode); break
        elif pred == owl_intersectionof: r = And(obj , self, bnode); break
        
        elif pred == owl_onproperty: restriction_property = self._to_python(obj, None)
        
        elif pred == SOME:      restriction_type = SOME;
        elif pred == ONLY:      restriction_type = ONLY;
        elif pred == VALUE:     restriction_type = VALUE;
        elif pred == HAS_SELF:  restriction_type = HAS_SELF;
#        elif pred == EXACTLY:   restriction_type = EXACTLY; restriction_cardinality = self._to_python(obj, XXX)
#        elif pred == MIN:       restriction_type = MIN;     restriction_cardinality = self._to_python(obj)
#        elif pred == MAX:       restriction_type = MAX;     restriction_cardinality = self._to_python(obj)
#        elif pred == owl_cardinality:     restriction_type = EXACTLY; restriction_cardinality = self._to_python(obj)
#        elif pred == owl_min_cardinality: restriction_type = MIN;     restriction_cardinality = self._to_python(obj)
#        elif pred == owl_max_cardinality: restriction_type = MAX;     restriction_cardinality = self._to_python(obj)
        
        elif pred == owl_oneof: r = OneOf(self._parse_list(obj), self, bnode); break
        
        elif pred == owl_members:          members = obj
        elif pred == owl_distinctmembers:  members = obj
        
        elif pred == owl_inverse_property:
          r = Inverse(self._to_python(obj, None), self, bnode, False)
          break
        
        elif pred == rdf_type:
          if   obj == owl_alldisjointclasses:    Disjoint = AllDisjoint
          elif obj == owl_alldisjointproperties: Disjoint = AllDisjoint
          elif obj == owl_alldifferent:          Disjoint = AllDisjoint
          
          elif obj == owl_axiom:                 return None
          
        elif pred == owl_ondatatype:       on_datatype = _universal_abbrev_2_datatype[obj]
        elif pred == owl_withrestrictions: with_restriction = obj
        
      else:
        if   restriction_type:
          #r = Restriction(restriction_property, restriction_type, restriction_cardinality, None, self, bnode)
          r = Restriction(restriction_property, restriction_type, None, None, self, bnode)
        elif Disjoint:
          r = Disjoint(members, self, bnode)
        elif on_datatype and with_restriction:
          r = ConstrainedDatatype(on_datatype, self, bnode, with_restriction)
        else:
          for pred, obj, d in self._get_data_triples_s_pod(bnode):
            if   pred == VALUE:     restriction_type = VALUE;
            elif pred == EXACTLY:   restriction_type = EXACTLY; restriction_cardinality = self._to_python(obj, d)
            elif pred == MIN:       restriction_type = MIN;     restriction_cardinality = self._to_python(obj, d)
            elif pred == MAX:       restriction_type = MAX;     restriction_cardinality = self._to_python(obj, d)
            elif pred == owl_cardinality:     restriction_type = EXACTLY; restriction_cardinality = self._to_python(obj, d)
            elif pred == owl_min_cardinality: restriction_type = MIN;     restriction_cardinality = self._to_python(obj, d)
            elif pred == owl_max_cardinality: restriction_type = MAX;     restriction_cardinality = self._to_python(obj, d)
            if restriction_type:
              r = Restriction(restriction_property, restriction_type, restriction_cardinality, None, self, bnode)
            else:
              s = ""
              raise ValueError("Cannot parse blank node %s: unknown node type!")
            
    self._bnodes[bnode] = r
    return r

  def _del_list(self, bnode):
    while bnode and (bnode != rdf_nil):
      bnode_next = self._get_obj_triple_sp_o(bnode, rdf_rest)
      self._del_obj_triple_spod(bnode, None, None)
      self._del_data_triple_spoddd(bnode, None, None, None)
      bnode = bnode_next
      
  def _set_list(self, bnode, l):
    if not l:
      self._add_obj_triple_spo(bnode, rdf_first, rdf_nil)
      self._add_obj_triple_spo(bnode, rdf_rest,  rdf_nil)
      return
    for i in range(len(l)):
      o,d = self._to_rdf(l[i])
      if d is None: self._add_obj_triple_spo  (bnode, rdf_first, o)
      else:         self._add_data_triple_spoddd(bnode, rdf_first, o, d)
      if i < len(l) - 1:
        bnode_next = self.world.new_blank_node()
        self._add_obj_triple_spo(bnode, rdf_rest, bnode_next)
        bnode = bnode_next
      else:
        self._add_obj_triple_spo(bnode, rdf_rest, rdf_nil)
        
  def _set_list_as_rdf(self, bnode, l):
    if not l:
      self._add_obj_triple_spo(bnode, rdf_first, rdf_nil)
      self._add_obj_triple_spo(bnode, rdf_rest,  rdf_nil)
      return
    for i in range(len(l)):
      if l[i][1] is None: self._add_obj_triple_spo  (bnode, rdf_first, l[i][0])
      else:               self._add_data_triple_spoddd(bnode, rdf_first, l[i][0], l[i][1])
      if i < len(l) - 1:
        bnode_next = self.world.new_blank_node()
        self._add_obj_triple_spo(bnode, rdf_rest, bnode_next)
        bnode = bnode_next
      else:
        self._add_obj_triple_spo(bnode, rdf_rest, rdf_nil)
        
  def __repr__(self): return """get_ontology("%s")""" % (self.base_iri)
  
  
class Metadata(object):
  def __init__(self, namespace, storid):
    object.__setattr__(self, "namespace", namespace)
    object.__setattr__(self, "storid"   , storid)
    
  def __getattr__(self, attr):
    Prop = self.namespace.world._props.get(attr)
    values = [self.namespace.ontology._to_python(o, d) for o, d in self.namespace.world._get_triples_sp_od(self.storid, Prop.storid)]
    values = ValueList(values, self, Prop)
    self.__dict__[attr] = values
    return values
  
  def __setattr__(self, attr, values):
    Prop = self.namespace.world._props.get(attr)
    if isinstance(Prop, AnnotationPropertyClass):
        if not isinstance(values, list):
          if values is None: values = []
          else:              values = [values]
        getattr(self, attr).reinit(values)
        
    else:
      raise ValueError("Metadata can only used defined annotation properties!")
  
  
  
def _open_onto_file(base_iri, name, mode = "r", only_local = False):
  if base_iri.endswith("#") or base_iri.endswith("/"): base_iri = base_iri[:-1]
  if base_iri.startswith("file://"): return open(base_iri[7:], mode)
  for dir in onto_path:
    for ext in ["", ".owl", ".rdf", ".n3"]:
      filename = os.path.join(dir, "%s%s" % (name, ext))
      if os.path.exists(filename): return open(filename, mode)
  if (mode.startswith("r")) and not only_local: return urllib.request.urlopen(base_iri)
  if (mode.startswith("w")): return open(os.path.join(onto_path[0], "%s.owl" % name), mode)
  raise FileNotFoundError

def _get_onto_file(base_iri, name, mode = "r", only_local = False):
  if base_iri.endswith("#") or base_iri.endswith("/"): base_iri = base_iri[:-1]
  if base_iri.startswith("file://"): return base_iri[7:]
  
  for dir in onto_path:
    filename = os.path.join(dir, base_iri.rsplit("/", 1)[-1])
    if os.path.exists(filename): return filename
    for ext in ["", ".nt", ".ntriples", ".rdf", ".owl"]:
      filename = os.path.join(dir, "%s%s" % (name, ext))
      if os.path.exists(filename): return filename
  if (mode.startswith("r")) and not only_local: return base_iri
  if (mode.startswith("w")): return os.path.join(onto_path[0], "%s.owl" % name)
  raise FileNotFoundError



owl_world = World(filename = None)
rdfs      = owl_world.get_ontology("http://www.w3.org/2000/01/rdf-schema#")
owl       = owl_world.get_ontology("http://www.w3.org/2002/07/owl#")
owlready  = owl_world.get_ontology("http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#")
anonymous = owl_world.get_ontology("http://anonymous/")

