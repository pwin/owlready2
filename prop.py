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

import weakref

from owlready2.namespace  import *
from owlready2.entity     import *
from owlready2.entity     import _inherited_property_value_restrictions
from owlready2.individual import ValueList
from owlready2.base       import _universal_abbrev_2_datatype, _universal_datatype_2_abbrev


_next_domain_range = None
_check_superclasses = False

class PropertyClass(EntityClass):
  _rdfs_is_a        = rdfs_subpropertyof
  _owl_equivalent   = owl_equivalentproperty
  _owl_disjointwith = owl_propdisjointwith
  
  def __new__(MetaClass, name, superclasses, obj_dict):
    if _check_superclasses:
      nb_base = 0
      if ObjectProperty     in superclasses: nb_base += 1
      if DataProperty       in superclasses: nb_base += 1
      if AnnotationProperty in superclasses: nb_base += 1
      if nb_base > 1:
        iri = "%s%s" % (obj_dict["namespace"].base_iri, name)
        if (ObjectProperty in superclasses) and (DataProperty in superclasses):
          raise TypeError("Property '%s' is both an ObjectProperty and a DataProperty!" % iri)
        if (ObjectProperty in superclasses) and (AnnotationProperty in superclasses):
          raise TypeError("Property '%s' is both an ObjectProperty and an AnnotationProperty!" % iri)
        if (AnnotationProperty in superclasses) and (DataProperty in superclasses):
          raise TypeError("Property '%s' is both an AnnotationProperty and a DataProperty!" % iri)
    return EntityClass.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __init__(Prop, name, bases, obj_dict):
    global _next_domain_range
    
    if _next_domain_range:
      domain         = [_next_domain_range[0]]
      range          = [_next_domain_range[1]]
      _next_domain_range = None
    else:
      domain         = obj_dict.pop("domain", False)
      range          = obj_dict.pop("range", False)
    inverse_property = obj_dict.pop("inverse_property", None) or obj_dict.pop("inverse", False)
    python_name      = obj_dict.pop("python_name", None)
    super().__init__(name, bases, obj_dict)
    
    Prop.namespace.world._props[name] = Prop
    
    type.__setattr__(Prop, "_domain", None)
    type.__setattr__(Prop, "_range", None)
    type.__setattr__(Prop, "_property_chain", None)
    type.__setattr__(Prop, "_inverse_property", False)
    type.__setattr__(Prop, "_python_name", name)
    
    if not LOADING:
      if not domain is False:
        Prop.domain.extend(domain)
        
      if not range is False:
        Prop.range.extend(range)
        
      if not inverse_property is False:
        Prop.inverse_property = inverse_property
        
      if not python_name is None: Prop.python_name = python_name
      
  def _add_is_a_triple(Prop, base):
    if   base in _CLASS_PROPS: pass
    elif base in _TYPE_PROPS:  Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, rdf_type       , base.storid)
    else:                      Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, Prop._rdfs_is_a, base.storid)
    
  def _del_is_a_triple(Prop, base):
    if   base in _CLASS_PROPS: pass
    elif base in _TYPE_PROPS:  Prop.namespace.ontology._del_obj_triple_spod(Prop.storid, rdf_type       , base.storid)
    else:                      Prop.namespace.ontology._del_obj_triple_spod(Prop.storid, Prop._rdfs_is_a, base.storid)
    
    
  def get_domain(Prop):
    if Prop._domain is None:
      Prop._domain = CallbackList((Prop.namespace.world._to_python(o, default_to_none = True) for o in Prop.namespace.world._get_obj_triples_sp_o(Prop.storid, rdf_domain)),
                                  Prop, PropertyClass._domain_changed)
    return Prop._domain

  def set_domain(Prop, value): Prop.domain.reinit(value)
  
  domain = property(get_domain, set_domain)
  
  def _domain_changed(Prop, old):
    new = frozenset(Prop.domain)
    old = frozenset(old)
    for x in old - new:
      Prop.namespace.ontology._del_obj_triple_spod(Prop.storid, rdf_domain, x.storid)
      if isinstance(x, ClassConstruct): x._set_ontology(None)
    for x in new - old:
      if isinstance(x, ClassConstruct): x._set_ontology(Prop.namespace.ontology)
      Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, rdf_domain, x.storid)
      
  def domains_indirect(Prop):
    yield from Prop.domain
    for parent_prop in Prop.__bases__:
      if isinstance(parent_prop, PropertyClass): yield from parent_prop.domains_indirect()
      
      
  def get_range(Prop):
    if Prop._range is None:
      Prop._range = CallbackList(
        (_universal_abbrev_2_datatype.get(o) or Prop.namespace.world._to_python(o, default_to_none = True)
         for o in Prop.namespace.world._get_obj_triples_sp_o(Prop.storid, rdf_range)),
        Prop, PropertyClass._range_changed)
    return Prop._range
  
  def set_range(Prop, value): Prop.range.reinit(value)
  
  range = property(get_range, set_range)
  
  def _range_changed(Prop, old):
    new = frozenset(Prop.range)
    old = frozenset(old)
    for x in old - new:
      x2 = _universal_datatype_2_abbrev.get(x) or x.storid
      Prop.namespace.ontology._del_obj_triple_spod(Prop.storid, rdf_range, x2)
      if isinstance(x, ClassConstruct): x._set_ontology(None)
    for x in new - old:
      if isinstance(x, ClassConstruct): x._set_ontology(Prop.namespace.ontology)
      x2 = _universal_datatype_2_abbrev.get(x) or x.storid
      Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, rdf_range, x2)
      
      
  def get_property_chain(Prop):
    if Prop._property_chain is None:
      Prop._property_chain = CallbackList(
        (PropertyChain(o, Prop.namespace.ontology)
          for o in Prop.namespace.world._get_obj_triples_sp_o(Prop.storid, owl_propertychain)),
        Prop, PropertyClass._property_chain_changed)
    return Prop._property_chain
  
  def set_property_chain(Prop, value): Prop.property_chain.reinit(value)
  
  property_chain = property(get_property_chain, set_property_chain)
  
  def _property_chain_changed(Prop, old):
    new = frozenset(Prop._property_chain)
    old = frozenset(old)
    for x in old - new:
      Prop.namespace.ontology._del_obj_triple_spod(Prop.storid, owl_propertychain, x.storid)
      x._set_ontology(None)
    for x in new - old:
      x._set_ontology(Prop.namespace.ontology)
      Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, owl_propertychain, x.storid)
    
    
  def __getattr__(Prop, attr):
    Annot = Prop.namespace.world._props.get(attr)
    if Annot is None:
      raise AttributeError("'%s' annotation property is not defined." % attr)
    if not issubclass_python(Annot, AnnotationProperty):
      raise AttributeError("Property can only have annotation property values!")
    
    return ValueList(
      (Prop.namespace.ontology._to_python(o,d) for o,d in Prop.namespace.world._get_triples_sp_od(Prop.storid, Annot.storid)),
      Prop, Annot) # Do NOT cache in __dict__, to avoid inheriting annotations
  
  def __setattr__(Class, attr, value):
    if attr in SPECIAL_PROP_ATTRS:
      super().__setattr__(attr, value)
      return
    
    Prop = Class.namespace.world._props.get(attr)
    if isinstance(Prop, ReasoningPropertyClass):
      raise AttributeError("Property cannot have non-annotation properties!")
    if   value is None:               value = []
    elif not isinstance(value, list): value = [value]
    getattr(Class, attr).reinit(value)
    
  def get_python_name(Prop):
    return Prop._python_name
  def set_python_name(Prop, python_name):
    if not LOADING: Prop.namespace.ontology._set_data_triple_spoddd(Prop.storid, owlready_python_name, *to_literal(python_name))
    del Prop.namespace.world._props[Prop._python_name]
    Prop.namespace.world._props[python_name] = Prop
    Prop._python_name = python_name
  python_name = property(get_python_name, set_python_name)
  
  def some    (Prop,     value): return Restriction(Prop, SOME    , None, value)
  def only    (Prop,     value): return Restriction(Prop, ONLY    , None, value)
  def value   (Prop,     value): return Restriction(Prop, VALUE   , None, value)
  def has_self(Prop,     value): return Restriction(Prop, HAS_SELF, None, value)
  def exactly (Prop, nb, value = None): return Restriction(Prop, EXACTLY, nb  , value)
  def min     (Prop, nb, value = None): return Restriction(Prop, MIN    , nb  , value)
  def max     (Prop, nb, value = None): return Restriction(Prop, MAX    , nb  , value)
  
  def __lt__(prop, value): return prop.some(ConstrainedDatatype(type(value), max_exclusive = value))
  def __le__(prop, value): return prop.some(ConstrainedDatatype(type(value), max_inclusive = value))
  def __gt__(prop, value): return prop.some(ConstrainedDatatype(type(value), min_exclusive = value))
  def __ge__(prop, value): return prop.some(ConstrainedDatatype(type(value), min_inclusive = value))
  
_FUNCTIONAL_FOR_CACHE = weakref.WeakKeyDictionary()

class Property(metaclass = PropertyClass):
  namespace = owl
  
  @classmethod
  def is_functional_for(Prop, Class):
    #if hasattr(Class, "_functional_for_cache"):
    #  r = Class._functional_for_cache.get(Prop)
    #  if not r is None: return r
    #else:
    #  type.__setattr__(Class, "_functional_for_cache", {})
    cache = _FUNCTIONAL_FOR_CACHE.get(Class)
    if cache is None:
      cache = _FUNCTIONAL_FOR_CACHE[Class] = {}
    else:
      r = cache.get(Prop)
      if not r is None: return r
      
    ranges  = set(Prop.range)
    singles = set()
    
    for restriction in _inherited_property_value_restrictions(Class, Prop, set()):
      if     restriction.type == ONLY:
        ranges.add(restriction.value)
      elif ((restriction.type == EXACTLY) or (restriction.type == MAX)) and (restriction.cardinality == 1):
        if restriction.value is None:
          cache[Prop] = True
          return True
        singles.add(restriction.value)

    cache[Prop] = r = not ranges.isdisjoint(singles)
    
    return r

  @classmethod
  def get_relations(Prop):
    for s,p,o,d in Prop.namespace.world._get_triples_spod_spod(None, Prop.storid, None, ""):
      s = Prop.namespace.world._get_by_storid(s)
      o = Prop.namespace.ontology._to_python(o, d)
      yield s, o
        
        
class ReasoningPropertyClass(PropertyClass):
  def __init__(Prop, name, bases, obj_dict):
    super().__init__(name, bases, obj_dict)
    
    if (not Prop.namespace.world is owl_world):
      Prop.namespace.world._reasoning_props[Prop._python_name] = Prop
      
      
  def set_python_name(Prop, python_name):
    Prop.namespace.world._reasoning_props.pop(Prop._python_name, None)
    Prop.namespace.world._reasoning_props[python_name] = Prop
    PropertyClass.set_python_name(Prop, python_name)
  python_name = property(PropertyClass.get_python_name, set_python_name)
  
  def __getitem__(Prop, entity):
    if isinstance(entity, Thing):
      return entity._get_instance_prop_value(Prop, Prop.python_name, True)
    else:
      return entity._get_class_prop_value(Prop, Prop.python_name, True)
    
  
class ObjectPropertyClass(ReasoningPropertyClass):
  _owl_type = owl_object_property
  
  def get_inverse_property(Prop):
    if Prop._inverse_property is False:
      inverse_storid = Prop.namespace.world._get_obj_triple_sp_o(Prop.storid, owl_inverse_property) or Prop.namespace.world._get_obj_triple_po_s(owl_inverse_property, Prop.storid)
      if inverse_storid: Prop._inverse_property = Prop.namespace.world._get_by_storid(inverse_storid)
      else:              Prop._inverse_property = None
    return Prop._inverse_property
  
  def set_inverse_property(Prop, value):
    Prop.namespace.ontology._set_obj_triple_spo(Prop.storid, owl_inverse_property, value and value.storid)
    Prop._inverse_property = value
    if value and not (value.inverse_property is Prop): value.inverse_property = Prop
    
  inverse_property = inverse = property(get_inverse_property, set_inverse_property)
  
  
class ObjectProperty(Property, metaclass = ObjectPropertyClass): pass


class DataPropertyClass(ReasoningPropertyClass):
  _owl_type = owl_data_property
  inverse_property = None

class DataProperty  (Property, metaclass = DataPropertyClass): pass

class FunctionalProperty(Property):
  @classmethod
  def is_functional_for(Prop, o): return True

class InverseFunctionalProperty(Property): pass
class TransitiveProperty       (Property): pass
class SymmetricProperty        (Property): pass
class AsymmetricProperty       (Property): pass
class ReflexiveProperty        (Property): pass
class IrreflexiveProperty      (Property): pass

_CLASS_PROPS = { DataProperty, ObjectProperty }
_TYPE_PROPS  = { FunctionalProperty, InverseFunctionalProperty, TransitiveProperty, SymmetricProperty, AsymmetricProperty, ReflexiveProperty, IrreflexiveProperty }


class PropertyChain(object):
  def __init__(self, Properties, ontology = None):
    if isinstance(Properties, int):
      self.storid = Properties
    else:
      self.storid = None
      self.properties = CallbackList(Properties, self, PropertyChain._callback)
    self.ontology = ontology
    if ontology and not LOADING: self._create_triples(ontology)
    
  def _set_ontology(self, ontology):
    if not LOADING:
      if   self.ontology and not ontology:
        self._destroy_triples(self.ontology)
      elif ontology and not self.ontology:
        if self.storid is None: self.storid = ontology.world.new_blank_node()
        self._create_triples(ontology)
      elif ontology and self.ontology:
        raise OwlReadySharedBlankNodeError("A PropertyChain cannot be shared by two ontologies. Please create a dupplicate.")
      
    self.ontology = ontology
    for Prop in self.properties:
      if hasattr(Prop, "_set_ontology"): Prop._set_ontology(ontology)
      
  def __getattr__(self, attr):
    if attr == "properties":
      self.properties = CallbackList(self.ontology._parse_list(self.storid), self, PropertyChain._callback)
      return self.properties
    return super().__getattribute__(attr)
  
  def _invalidate_list(self):
    try: del self.properties
    except: pass
    
  def _callback(self, old):
    if self.ontology:
      self._destroy_triples(self.ontology)
      self._create_triples (self.ontology)
      
  def _destroy_triples(self, ontology):
    ontology._del_list(self.storid)
    
  def _create_triples(self, ontology):
    ontology._set_list(self.storid, self.properties)
    
  def __repr__(self):
    return "PropertyChain([%s])" % (", ".join(repr(x) for x in self.properties))
  




def destroy_entity(e):
  if isinstance(e, PropertyClass):
    modified_entities = set()
    if   e._owl_type == owl_object_property:
      for s,p,o in e.namespace.world._get_obj_triples_spo_spo(None, e.storid, None):
        modified_entities.add(s)
      e.namespace.world._del_obj_triple_spod(None, e.storid, None)
      # XXX inverse ?
    elif e._owl_type == owl_data_property:
      for s,p,o,d in e.namespace.world._get_data_triples_spod_spod(None, e.storid, None, None):
        modified_entities.add(s)
      e.namespace.world._del_data_triple_spoddd(None, e.storid, None, None)
      
    else: #e._owl_type == owl_annotation_property:
      for s,p,o,d in e.namespace.world._get_triples_spod_spod(None, e.storid, None, None):
        modified_entities.add(s)
      e.namespace.world._del_obj_triple_spod  (None, e.storid, None)
      e.namespace.world._del_data_triple_spoddd(None, e.storid, None, None)
      
    for s in modified_entities:
      s = e.namespace.world._entities.get(s)
      if s:
        delattr(s, e._python_name)
        
    e.namespace.world._props          .pop(e._python_name, None)
    e.namespace.world._reasoning_props.pop(e._python_name, None)
    
  def destroyer(bnode):
    if bnode == e.storid: return
    
    class_construct = e.namespace.ontology._bnodes.pop(bnode, None)
    if class_construct:
      for subclass in class_construct.subclasses(True):
        if   isinstance(subclass, EntityClass) or isinstance(subclass, Thing):
          subclass.is_a.remove(class_construct)
          
  def relation_updater(destroyed_storids, storid, relations):
    o = e.namespace.world._entities.get(storid)
    if o:
      for r in relations:
        if  (r == rdf_type) or (r == rdfs_subpropertyof):
          o.is_a.reinit([i for i in o.is_a if not i.storid in destroyed_storids])
        elif r == rdfs_subclassof:
          o.is_a.reinit([i for i in o.is_a if not i.storid in destroyed_storids])
          for Subclass in o.descendants(True, True): _FUNCTIONAL_FOR_CACHE.pop(Subclass, None)
          
        elif (r == owl_equivalentproperty) or (r == owl_equivalentindividual):
          if o._equivalent_to._indirect:
            for o2 in o.equivalent_to._indirect: o2._equivalent_to._indirect = None
            o._equivalent_to._indirect = None
        elif r == owl_equivalentclass:
          if o._equivalent_to._indirect:
            for o2 in o.equivalent_to._indirect: o2._equivalent_to._indirect = None
            o._equivalent_to._indirect = None
          for Subclass in o.descendants(True, True): _FUNCTIONAL_FOR_CACHE.pop(Subclass, None)
          
        elif r == rdf_domain:
          o._domain = None
        elif r == rdf_range:
          o._range = None
          
        else:
          r = e.namespace.world._entities.get(r)
          
  e.namespace.world.graph.destroy_entity(e.storid, destroyer, relation_updater)
  
  e.namespace.world._entities.pop(e.storid, None)
