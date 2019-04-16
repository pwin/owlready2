# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2019 Jean-Baptiste LAMY
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
from owlready2.base       import _universal_abbrev_2_datatype, _universal_datatype_2_abbrev

_NEXT_DOMAIN_RANGE = ContextVar("_NEXT_DOMAIN_RANGE", default = None)


SymmetricProperty = () # Forward declaration

#_check_superclasses = False

_default_class_property_type = ["some"]
def set_default_class_property_type(types):
  global _default_class_property_type
  _default_class_property_type = types

class PropertyClass(EntityClass):
  _rdfs_is_a        = rdfs_subpropertyof
  _owl_equivalent   = owl_equivalentproperty
  _owl_disjointwith = owl_propdisjointwith
  
  # def __new__(MetaClass, name, superclasses, obj_dict):
  #   if _check_superclasses:
  #     nb_base = 0
  #     if ObjectProperty     in superclasses: nb_base += 1
  #     if DataProperty       in superclasses: nb_base += 1
  #     if AnnotationProperty in superclasses: nb_base += 1
  #     if nb_base > 1:
  #       iri = "%s%s" % (obj_dict["namespace"].base_iri, name)
  #       if (ObjectProperty in superclasses) and (DataProperty in superclasses):
  #         raise TypeError("Property '%s' is both an ObjectProperty and a DataProperty!" % iri)
  #       if (ObjectProperty in superclasses) and (AnnotationProperty in superclasses):
  #         raise TypeError("Property '%s' is both an ObjectProperty and an AnnotationProperty!" % iri)
  #       if (AnnotationProperty in superclasses) and (DataProperty in superclasses):
  #         raise TypeError("Property '%s' is both an AnnotationProperty and a DataProperty!" % iri)
  #   return EntityClass.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __init__(Prop, name, bases, obj_dict):
    next_domain_range = _NEXT_DOMAIN_RANGE.get()
    if next_domain_range:
      domain         = [next_domain_range[0]]
      range          = [next_domain_range[1]]
      _NEXT_DOMAIN_RANGE.set(None)
    else:
      domain            = obj_dict.pop("domain", False)
      range             = obj_dict.pop("range", False)
    inverse_property    = obj_dict.pop("inverse_property", None) or obj_dict.pop("inverse", False)
    python_name         = obj_dict.pop("python_name", None)
    class_property_type = obj_dict.pop("class_property_type", None)
    super().__init__(name, bases, obj_dict)
    
    Prop.namespace.world._props[name] = Prop
    
    type.__setattr__(Prop, "_domain", None)
    type.__setattr__(Prop, "_range", None)
    type.__setattr__(Prop, "_property_chain", None)
    type.__setattr__(Prop, "_inverse_property", False)
    type.__setattr__(Prop, "_python_name", name)
    
    _class_property_type = CallbackList(
      (o for o, d in Prop.namespace.world._get_data_triples_sp_od(Prop.storid, owlready_class_property_type)),
      Prop, PropertyClass._class_property_type_changed)
    
    type.__setattr__(Prop, "_class_property_type", _class_property_type)
    types = _class_property_type or _default_class_property_type
    type.__setattr__(Prop, "_class_property_some",     "some"     in types)
    type.__setattr__(Prop, "_class_property_only",     "only"     in types)
    type.__setattr__(Prop, "_class_property_relation", "relation" in types)
    
    if not LOADING:
      if not domain is False:
        Prop.domain.extend(domain)
        
      if not range is False:
        Prop.range.extend(range)
        
      if not inverse_property is False:
        Prop.inverse_property = inverse_property
        
      if not python_name is None:
        Prop.python_name = python_name
        
      if not class_property_type is None:
        Prop.class_property_type = class_property_type
        
        
        
  def _add_is_a_triple(Prop, base):
    if   base in _CLASS_PROPS: pass
    elif base in _TYPE_PROPS:  Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, rdf_type       , base.storid)
    else:                      Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, Prop._rdfs_is_a, base.storid)
    
  def _del_is_a_triple(Prop, base):
    if   base in _CLASS_PROPS: pass
    elif base in _TYPE_PROPS:  Prop.namespace.ontology._del_obj_triple_spo(Prop.storid, rdf_type       , base.storid)
    else:                      Prop.namespace.ontology._del_obj_triple_spo(Prop.storid, Prop._rdfs_is_a, base.storid)
    
    
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
      Prop.namespace.ontology._del_obj_triple_spo(Prop.storid, rdf_domain, x.storid)
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
      Prop.namespace.ontology._del_obj_triple_spo(Prop.storid, rdf_range, x2)
      if isinstance(x, ClassConstruct): x._set_ontology(None)
    for x in new - old:
      if isinstance(x, ClassConstruct): x._set_ontology(Prop.namespace.ontology)
      x2 = _universal_datatype_2_abbrev.get(x) or x.storid
      Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, rdf_range, x2)
      
    if "_range_iri" in Prop.__dict__: del Prop._range_iri
    
    
  def get_range_iri(Prop):
    if not "_range_iri" in Prop.__dict__:
      iris = []
      for o in Prop.namespace.world._get_obj_triples_sp_o(Prop.storid, rdf_range):
        if o > 0: iris.append(Prop.namespace.world._unabbreviate(o))
        else:     iris.append("_:%s" % (-o))
      type.__setattr__(Prop, "_range_iri", CallbackList(iris, Prop, PropertyClass._range_iri_changed))
    return Prop._range_iri
  
  def set_range_iri(Prop, value): Prop.range_iri.reinit(value)
  
  range_iri = property(get_range_iri, set_range_iri)
  
  def _range_iri_changed(Prop, old):
    new = frozenset(Prop.range_iri)
    old = frozenset(old)
    for x in old - new:
      if x.startswith("_"): x2 = -int(x[2:])
      else:                 x2 = Prop.namespace.world._abbreviate(x)
      Prop.namespace.ontology._del_obj_triple_spo(Prop.storid, rdf_range, x2)        
    for x in new - old:
      if x.startswith("_"): x2 = -int(x[2:])
      else:                 x2 = Prop.namespace.world._abbreviate(x)
      Prop.namespace.ontology._add_obj_triple_spo(Prop.storid, rdf_range, x2)
      
    if Prop._range: Prop._range = None
      
      
  def get_class_property_type(Prop): return Prop._class_property_type
  def set_class_property_type(Prop, value): Prop.class_property_type.reinit(value)
  class_property_type = property(get_class_property_type, set_class_property_type)
  
  def _class_property_type_changed(Prop, old):
    types = Prop._class_property_type or _default_class_property_type
    type.__setattr__(Prop, "_class_property_some",     "some"     in types)
    type.__setattr__(Prop, "_class_property_only",     "only"     in types)
    type.__setattr__(Prop, "_class_property_relation", "relation" in types)
    Prop.namespace.ontology._del_data_triple_spod(Prop.storid, owlready_class_property_type, None, None)
    for x in Prop._class_property_type:
      Prop.namespace.ontology._add_data_triple_spod(Prop.storid, owlready_class_property_type, x, 0)
      
      
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
      Prop.namespace.ontology._del_obj_triple_spo(Prop.storid, owl_propertychain, x.storid)
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
    
    return IndividualValueList(
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
    if not LOADING: Prop.namespace.ontology._set_data_triple_spod(Prop.storid, owlready_python_name, *to_literal(python_name))
    del Prop.namespace.world._props[Prop._python_name]
    Prop.namespace.world._props[python_name] = Prop
    Prop._python_name = python_name
  python_name = property(get_python_name, set_python_name)
  
  def some    (Prop,     value): return Restriction(Prop, SOME    , None, value)
  def only    (Prop,     value): return Restriction(Prop, ONLY    , None, value)
  def value   (Prop,     value): return Restriction(Prop, VALUE   , None, value)
  def has_self(Prop,     value = True): return Restriction(Prop, HAS_SELF, None, value)
  def exactly (Prop, nb, value = None): return Restriction(Prop, EXACTLY, nb  , value)
  def min     (Prop, nb, value = None): return Restriction(Prop, MIN    , nb  , value)
  def max     (Prop, nb, value = None): return Restriction(Prop, MAX    , nb  , value)
  
  def __lt__(prop, value): return prop.some(ConstrainedDatatype(type(value), max_exclusive = value))
  def __le__(prop, value): return prop.some(ConstrainedDatatype(type(value), max_inclusive = value))
  def __gt__(prop, value): return prop.some(ConstrainedDatatype(type(value), min_exclusive = value))
  def __ge__(prop, value): return prop.some(ConstrainedDatatype(type(value), min_inclusive = value))

  
  def _get_value_for_individual(Prop, entity):
    value = entity.namespace.world._get_triple_sp_od(entity.storid, Prop.storid)
    if not value is None: return entity.namespace.ontology._to_python(*value)
    
  def _get_values_for_individual(Prop, entity):
    return IndividualValueList((entity.namespace.ontology._to_python(o, d) for o, d in entity.namespace.world._get_triples_sp_od(entity.storid, Prop.storid)),
                               entity, Prop)
  
  _get_value_for_class  = _get_value_for_individual
  _get_values_for_class = _get_values_for_individual
  
  def _get_indirect_value_for_individual(Prop, entity):
    values = Prop._get_indirect_values_for_individual(entity)
    if   not values:       return None
    elif len(values) == 1: return values[0]
    return _most_specific(values)
  
  def _get_indirect_values_for_individual(Prop, entity):
    world = entity.namespace.world
    onto  = entity.namespace.ontology
    
    if   not isinstance(entity, EntityClass):
      eqs    = list(entity.equivalent_to.self_and_indirect_equivalent())
      values = { onto._to_python(o, d)
                 for P    in Prop.descendants()
                 for eq   in eqs
                 for o, d in world._get_triples_sp_od(eq.storid, P.storid) }
      for eq in eqs:
        values.extend(Prop._get_indirect_values_for_individual(eq.__class__))
        
    else:
      storids = [ancestor.storid for ancestor in entity.ancestors()]
      values = { onto._to_python(o, d)
                 for P      in Prop.descendants()
                 for storid in storids
                 for o, d   in world._get_triples_sp_od(storid, P.storid) }
    return list(values)
  
  def _get_indirect_value_for_class(Prop, entity):
    values = Prop._get_indirect_values_for_class(entity)
    if   not values:       return None
    elif len(values) == 1: return values[0]
    return _most_specific(values)
  
  _get_indirect_values_for_class = _get_indirect_values_for_individual
  
  def _set_value_for_individual(Prop, entity, value):
    if value is None: entity.namespace.ontology._del_triple_spod(entity.storid, Prop.storid, None, None)
    else:             entity.namespace.ontology._set_triple_spod(entity.storid, Prop.storid, *entity.namespace.ontology._to_rdf(value))
    if (not instance(entity, EntityClass)) and (Prop is entity.namespace.world._props.get(Prop._python_name)):
      entity.__dict__[Prop.python_name] = [value]
      
  _set_value_for_class  = _set_value_for_individual
  
  def _set_values_for_individual(Prop, entity, values): Prop[entity].reinit(values)
  _set_values_for_class = _set_values_for_individual
  
  def __getitem__(Prop, entity):
    if isinstance(entity, EntityClass):
      return Prop._get_values_for_class(entity)
    else:
      if Prop is entity.namespace.world._props.get(Prop._python_name): # use cached value
        if Prop.is_functional_for(entity.__class__): return FunctionalIndividualValueList([getattr(entity, Prop._python_name)], entity, Prop)
        else:                                        return getattr(entity, Prop._python_name)
      else:
        l = Prop._get_values_for_individual(entity)
        if Prop.is_functional_for(entity.__class__): l.__class__ = FunctionalIndividualValueList
        return l
      
  def __setitem__(Prop, entity, value):
    if isinstance(entity, EntityClass):
      Prop._set_values_for_class(entity, value)
    else:
      Prop._set_values_for_individual(entity, value)
      

  
_FUNCTIONAL_FOR_CACHE = weakref.WeakKeyDictionary()

class Property(metaclass = PropertyClass):
  namespace = rdf
  _inverse_storid = 0
  
  @classmethod
  def is_functional_for(Prop, Class):
    cache = _FUNCTIONAL_FOR_CACHE.get(Class)
    if cache is None:
      cache = _FUNCTIONAL_FOR_CACHE[Class] = {}
    else:
      r = cache.get(Prop)
      if not r is None: return r
      
    ranges  = set(Prop.range)
    singles = set()
    
    for restriction in _inherited_properties_value_restrictions(Class, {Prop}, set()):
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
    
  
class ObjectPropertyClass(ReasoningPropertyClass):
  _owl_type = owl_object_property
  
  def __init__(Prop, name, bases, obj_dict):
    super().__init__(name, bases, obj_dict)
    
    if issubclass_python(Prop, SymmetricProperty):
      type.__setattr__(Prop, "_inverse_storid", Prop.storid)
      
    else:
      for inverse_storid in Prop.namespace.world._get_obj_triples_sp_o(Prop.storid, owl_inverse_property):
        if inverse_storid > 0: break
      else:
        for inverse_storid in Prop.namespace.world._get_obj_triples_po_s(owl_inverse_property, Prop.storid):
          if inverse_storid > 0: break
        else: inverse_storid = 0
      #inverse_storid = Prop.namespace.world._get_obj_triples_sp_o(Prop.storid, owl_inverse_property) or Prop.namespace.world._get_obj_triples_po_s(owl_inverse_property, Prop.storid)
      type.__setattr__(Prop, "_inverse_storid", inverse_storid or 0)
      if inverse_storid: type.__setattr__(Prop, "_inverse_property", Prop.namespace.world._get_by_storid(inverse_storid))
      else:              type.__setattr__(Prop, "_inverse_property", None)
      
  def get_inverse_property(Prop):
    return Prop._inverse_property
  
  def set_inverse_property(Prop, value):
    Prop.namespace.ontology._set_obj_triple_spo(Prop.storid, owl_inverse_property, value and value.storid)
    type.__setattr__(Prop, "_inverse_property", value)
    if value:
      type.__setattr__(Prop, "_inverse_storid", value.storid)
      if not value._inverse_property is Prop: value.inverse_property = Prop
    else:
      type.__setattr__(Prop, "_inverse_storid", 0)
      
  inverse_property = inverse = property(get_inverse_property, set_inverse_property)
  
  def _class_is_a_changed(Prop, old):
    super()._class_is_a_changed(old)
    if   (SymmetricProperty in old) and (not SymmetricProperty in Prop.is_a):
      if Prop._inverse_property: type.__setattr__(Prop, "_inverse_storid", Prop._inverse_property.storid)
      else:                      type.__setattr__(Prop, "_inverse_storid", 0)
    elif (SymmetricProperty in Prop.is_a) and (not SymmetricProperty in old):
      type.__setattr__(Prop, "_inverse_storid", Prop.storid)
      
      
  def _get_value_for_individual(Prop, entity):
    value = (entity.namespace.world._get_obj_triple_sp_o(entity.storid, Prop.storid)
         or (Prop._inverse_storid and
             entity.namespace.world._get_obj_triple_po_s(Prop._inverse_storid, entity.storid)) )
    if value:
      return entity.namespace.ontology._to_python(value)
    
  def _get_value_for_class(Prop, entity):
    if   Prop._class_property_relation: return Prop._get_value_for_individual(entity)
    
    elif Prop._class_property_some:
      for r in _property_value_restrictions(entity, Prop):
        if (r.type == VALUE) or (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1): return r.value
        
    elif Prop._class_property_only:
      for r in _property_value_restrictions(Class, Prop):
        if (r.type == ONLY):
          for value in _flatten_only(r): return value
          
          
  def _get_values_for_individual(Prop, entity):
    if Prop._inverse_storid:
      #return IndividualValueList((entity.namespace.ontology._to_python(o)
      #                            for g in (entity.namespace.world._get_obj_triples_sp_o(entity.storid, Prop.storid),
      #                                      entity.namespace.world._get_obj_triples_po_s(Prop._inverse_storid, entity.storid))
      #                            for o in g ), entity, Prop)
      return IndividualValueList((entity.namespace.ontology._to_python(o)
                                  for o in  entity.namespace.world._get_obj_triples_spi_o(entity.storid, Prop.storid, Prop._inverse_storid)),
                                  entity, Prop)
    else:
      return IndividualValueList((entity.namespace.ontology._to_python(o)
                                  for o in  entity.namespace.world._get_obj_triples_sp_o(entity.storid, Prop.storid)),
                                  entity, Prop)
                                 
  def _get_values_for_class(Prop, entity):
    if   Prop._class_property_relation: return Prop._get_values_for_individual(entity)
    
    elif Prop._class_property_some:
      return ClassValueList(set(r.value for r in _property_value_restrictions(entity, Prop)
                                if (r.type == VALUE) or (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1)),
                                entity, Prop)
    
    elif Prop._class_property_only:
      return ClassValueList(set(x for r in _property_value_restrictions(entity, Prop)
                                if (r.type == ONLY)
                                for x in _flatten_only(r) ), entity, Prop)
      
                                 
  def _get_indirect_values_for_individual(Prop, entity):
    world   = entity.namespace.world
    onto    = entity.namespace.ontology
    Props   = Prop.descendants()
    eqs     = list(entity.equivalent_to.self_and_indirect_equivalent())
    already_applied_class = set()
    
    prop_storids = []
    values       = set()
    for P in Props:
      if issubclass(P, TransitiveProperty):
        if P._inverse_storid: prop_storids.append((P.storid, P._inverse_storid))
        else:                 prop_storids.append((P.storid, None))
      else:
        if P._inverse_storid:
          values.update(onto._to_python(o)
                        for eq in eqs
                        for g in (world._get_obj_triples_sp_o(eq.storid, P.storid), world._get_obj_triples_po_s(P._inverse_storid, eq.storid))
                        for o in g )
        else:
          values.update(onto._to_python(o)
                        for eq in eqs
                        for o in  world._get_obj_triples_sp_o(eq.storid, P.storid) )
          
    if prop_storids:
      for eq in eqs:
        new_values = [onto._to_python(o) for o in world._get_obj_triples_transitive_sp_indirect(eq.storid, prop_storids)]
        
        for o in new_values:
          values.add(o)
          if not o.__class__ in already_applied_class:
            values.update(Prop._get_indirect_values_for_class(o.__class__, True))
            already_applied_class.add(o.__class__)
          for o2 in o.equivalent_to.indirect():
            if not ((o2 in new_values) or (o2 in values)):
              values.add(o2)
              if not o2.__class__ in already_applied_class:
                values.update(Prop._get_indirect_values_for_class(o2.__class__, True))
                already_applied_class.add(o2.__class__)
                
    for eq in eqs:
      if not eq.__class__ in already_applied_class:
        values.update(Prop._get_indirect_values_for_class(eq.__class__, True))
        already_applied_class.add(eq.__class__)
        
    return list(values)
  
  def _get_indirect_values_for_class(Prop, entity, transitive_exclude_self = True):
    world = entity.namespace.world
    onto  = entity.namespace.ontology
    Props = Prop.descendants()
    
    if   Prop._class_property_relation:
      storids = [ancestor.storid for ancestor in entity.ancestors()]
      
      prop_storids = []
      values       = set()
      for P in Props:
        if issubclass_python(P, TransitiveProperty):
          if P._inverse_storid: prop_storids.append((P.storid, P._inverse_storid))
          else:                 prop_storids.append((P.storid, None))
        else:
          if P._inverse_storid:
            values.update(onto._to_python(o) for storid in storids
                                             for g in (world._get_obj_triples_sp_o(storid, P.storid),
                                                       world._get_obj_triples_po_s(P._inverse_storid, storid))
                                             for o in g )
          else:
            values.update(onto._to_python(o) for storid in storids
                                             for o in  world._get_obj_triples_sp_o(storid, P.storid) )
              
      if prop_storids:
        values.update(onto._to_python(o) for storid in storids
                                         for o in world._get_obj_triples_transitive_sp_indirect(storid, prop_storids))
        if transitive_exclude_self: values.discard(entity)


    elif Prop._class_property_some:
      if issubclass_python(Prop, TransitiveProperty):
        values = set()
        def walk(o):
          values.add(o)
          for r in _inherited_properties_value_restrictions(o, Props, set()):
            if   r.type == VALUE:
              if not r.value in values:
                for o2 in r.value.equivalent_to.self_and_indirect_equivalent():
                  if not o2 in values:
                    values.add(o2)
                    values.update(Prop._get_indirect_values_for_individual(o2))
                    
            elif (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1):
              if not r.value in values: walk(r.value)

          if isinstance(o, ThingClass):
            for e in o.equivalent_to.indirect():
              if not e in values: walk(e)
              
        walk(entity)
        if transitive_exclude_self: values.discard(entity)
        
      else:
        values = set(r.value for r in _inherited_properties_value_restrictions(entity, Props, set())
                             if (r.type == VALUE) or (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1) )
        
    elif Prop._class_property_only: # Effect of transitivity on ONLY restrictions is unclear -- probably no effect?
      or_valuess = [set(_flatten_only(r)) for r in _inherited_properties_value_restrictions(entity, Props, set())
                                          if (r.type == ONLY)]
      values = or_valuess[0]
      for or_values in or_valuess[1:]:
        new_values = values & or_values
        for vs1, vs2 in ((values, or_values), (or_values, values)):
          vs2_classes = tuple(o for o in vs2 if isinstance(o, EntityClass))
          for v in vs1 - vs2:
            if isinstance(v, EntityClass):
              if issubclass(v, vs2_classes): new_values.add(v)
            else:
              if isinstance(v, vs2_classes): new_values.add(v)
        values = new_values
        
    return list(values)
  
  def _set_value_for_individual(Prop, entity, value):
    if value is None: entity.namespace.ontology._del_obj_triple_spo(entity.storid, Prop.storid, None)
    else:             entity.namespace.ontology._set_obj_triple_spo(entity.storid, Prop.storid, value.storid)
    if (not instance(entity, EntityClass)) and (Prop is entity.namespace.world._props.get(Prop._python_name)):
      entity.__dict__[Prop.python_name] = value
      
  def _set_value_for_class (Prop, entity, value ): Prop._get_values_for_class(entity).reinit([value])
  
  
class ObjectProperty(Property, metaclass = ObjectPropertyClass):
  namespace = owl


class DataPropertyClass(ReasoningPropertyClass):
  _owl_type = owl_data_property
  inverse_property = None
  
  def _get_value_for_individual(Prop, entity):
    value = entity.namespace.world._get_data_triple_sp_od(entity.storid, Prop.storid)
    if not value is None: return entity.namespace.ontology._to_python(*value)
    
  def _get_value_for_class(Prop, entity):
    if   Prop._class_property_relation: Prop._get_value_for_individual(entity)
    
    elif Prop._class_property_some:
        for r in _property_value_restrictions(entity, Prop):
          if (r.type == VALUE) or (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1):
            return r.value
          
    elif Prop._class_property_only:
      for r in _property_value_restrictions(Class, Prop):
        if (r.type == ONLY):
          for value in _flatten_only(r): return value
            
  def _get_values_for_individual(Prop, entity):
    return IndividualValueList((entity.namespace.ontology._to_python(o, d)
                                for o, d in entity.namespace.world._get_data_triples_sp_od(entity.storid, Prop.storid)),
                               entity, Prop)
      
  def _get_values_for_class(Prop, entity):
    if   Prop._class_property_relation:
      return Prop._get_values_for_individual(entity)
    
    elif Prop._class_property_some:
      return ClassValueList(set(r.value for r in _property_value_restrictions(entity, Prop)
                                if (r.type == VALUE) or (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1) ),
                            entity, Prop)
        
    elif Prop._class_property_only:
      return ClassValueList(set(x for r in _property_value_restrictions(entity, Prop)
                                if (r.type == ONLY)
                                for x in _flatten_only(r) ),
                            entity, Prop)
    
    
  def _get_indirect_value_for_individual(Prop, entity):
    values = Prop._get_indirect_values_for_individual(entity)
    if   len(values) == 0: return None
    elif len(values) == 1: return values[0]
    # XXX datatype
    return _most_specific(values)
  
  def _get_indirect_value_for_class(Prop, entity):
    values = Prop._get_indirect_values_for_class(entity)
    if   len(values) == 0: return None
    elif len(values) == 1: return values[0]
    # XXX datatype
    return _most_specific(values)
  
  def _get_indirect_values_for_individual(Prop, entity):
    eqs    = list(entity.equivalent_to.self_and_indirect_equivalent())
    values = [entity.namespace.ontology._to_python(o, d)
              for P    in Prop.descendants()
              for eq   in eqs
              for o, d in entity.namespace.world._get_data_triples_sp_od(eq.storid, P.storid)]
    
    values.extend(Prop._get_indirect_values_for_class(entity.__class__))
    return values

  
  def _get_indirect_values_for_class(Prop, entity):
    Props = Prop.descendants()
    
    if   Prop._class_property_relation:
      storids = [ancestor.storid for ancestor in entity.ancestors()]
      return [ entity.namespace.ontology._to_python(o, d)
               for storid in storids
               for P in Props
               for o, d in entity.namespace.world._get_data_triples_sp_od(storid, P.storid) ]
      
    elif Prop._class_property_some:
      return list(set(r.value for r in _inherited_properties_value_restrictions(entity, Props, set())
                      if (r.type == VALUE) or (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1) ))
    
    elif Prop._class_property_only:
      return list(set(x for r in _inherited_properties_value_restrictions(entity, Props, set())
                      if (r.type == ONLY)
                      for x in _flatten_only(r) ))
    
  def _set_value_for_individual(Prop, entity, value):
    if value is None: entity.namespace.ontology._del_data_triple_spod(entity.storid, Prop.storid, None, None)
    else:             entity.namespace.ontology._set_data_triple_spod(entity.storid, Prop.storid, *entity.namespace.ontology._to_rdf(value))
    if (not instance(entity, EntityClass)) and (Prop is entity.namespace.world._props.get(Prop._python_name)):
      entity.__dict__[Prop.python_name] = value
      
  def _set_value_for_class (Prop, entity, value ): Prop._get_values_for_class(entity).reinit([value])


class DatatypeProperty(Property, metaclass = DataPropertyClass):
  namespace = owl

DataProperty = DatatypeProperty

class FunctionalProperty(Property):
  namespace = owl
  @classmethod
  def is_functional_for(Prop, o): return True

class InverseFunctionalProperty(Property): namespace = owl
class TransitiveProperty       (Property): namespace = owl
class SymmetricProperty        (Property): namespace = owl
class AsymmetricProperty       (Property): namespace = owl
class ReflexiveProperty        (Property): namespace = owl
class IrreflexiveProperty      (Property): namespace = owl

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
      e.namespace.world._del_obj_triple_spo(None, e.storid, None)
      # XXX inverse ?
    elif e._owl_type == owl_data_property:
      for s,p,o,d in e.namespace.world._get_data_triples_spod_spod(None, e.storid, None, None):
        modified_entities.add(s)
      e.namespace.world._del_data_triple_spod(None, e.storid, None, None)
      
    else: #e._owl_type == owl_annotation_property:
      for s,p,o,d in e.namespace.world._get_triples_spod_spod(None, e.storid, None, None):
        modified_entities.add(s)
      e.namespace.world._del_obj_triple_spo (None, e.storid, None)
      e.namespace.world._del_data_triple_spod(None, e.storid, None, None)
      
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





def _property_value_restrictions(x, Prop):
  for parents in (x.is_a, x.equivalent_to.indirect()):
    for r in parents:
      if   isinstance(r, Restriction):
        if (Prop is None) or (r.property is Prop): yield r
        
      elif isinstance(r, And):
        for r2 in r.Classes:
          if isinstance(r2, Restriction):
            if (Prop is None) or (r2.property is Prop): yield r2
            
            


def _inherited_properties_value_restrictions(x, Props, already):
  if   isinstance(x, Restriction):
    if (Props is None) or (x.property in Props): yield x
    
  elif isinstance(x, And):
    for x2 in x.Classes:
      yield from _inherited_properties_value_restrictions(x2, Props, already)
      
  elif isinstance(x, EntityClass) or isinstance(x, Thing):
    already.add(x)
    parents = [ parent
                for parents in (x.is_a, list(x.equivalent_to.indirect()))
                for parent in parents
                if not parent in already ]
    
    # Need two passes in order to favor restriction on the initial class rather than those on the ancestor classes
    for parent in parents:
      if isinstance(parent, Restriction) and ((Props is None) or (parent.property in Props)): yield parent
      
    for parent in parents:
      if not isinstance(parent, Restriction):
        yield from _inherited_properties_value_restrictions(parent, Props, already)
        
    #parentss = (x.is_a, list(x.equivalent_to.indirect()))
    #for parents in parentss:
    #  for parent in parents:
    #    if isinstance(parent, Restriction) and (not parent in already):
    #      if parent.property in Props: yield parent
    #      
    #for parents in parentss:
    #  for parent in parents:
    #    if (not isinstance(parent, Restriction)) and (not parent in already):
    #      already.add(parent)
    #      yield from _inherited_properties_value_restrictions(parent, Props, already)
      
      
def _flatten_only(r):
  if isinstance(r.value, Or):
    for i in r.value.Classes:
      if isinstance(i, OneOf): yield from i.instances
      else:                    yield i
  else:
    if isinstance(r.value, OneOf): yield from r.value.instances
    else:                          yield r.value
    

def _most_specific(s):
  best = None
  for e in s:
    if not isinstance(e, EntityClass): return e # Individuals are more specific than classes
    if (best is None) or (issubclass_python(e, best)): best = e
  return best


    
class IndividualValueList(CallbackListWithLanguage):
  __slots__ = ["_Prop"]
  def __init__(self, l, obj, Prop):
    list.__init__(self, l)
    self._obj  = obj
    self._Prop = Prop
    
  # def transitive(self):
  #   n = self._obj.namespace
  #   if self._Prop.inverse_property:
  #     for o in n.world._get_obj_triples_transitive_sp_indirect(self._obj.storid, [(self._Prop.storid, self._Prop.inverse_property.storid)]):
  #       yield n.ontology._to_python(o)
  #   else:
  #     for o in n.world._get_obj_triples_transitive_sp(self._obj.storid, self._Prop.storid):
  #       yield n.ontology._to_python(o)
        
  # def transitive_symmetric(self):
  #   n = self._obj.namespace
  #   for o in n.world._get_obj_triples_transitive_sym(self._obj.storid, self._Prop.storid):
  #     yield n.ontology._to_python(o)
      
  # def symmetric(self):
  #   yield from self
  #   n = self._obj.namespace
  #   for o in n.world._get_obj_triples_po_s(self._Prop.storid, self._obj.storid):
  #     yield n.ontology._to_python(o)
      
  def indirect(self):
    return self._Prop._get_indirect_values_for_individual(self._obj)

  def _callback(self, obj, old):
    old = set(old)
    new = set(self)
    inverse  = self._Prop.inverse_property
    
    if   self._Prop._owl_type == owl_object_property:
      for removed in old - new:
        obj.namespace.ontology._del_obj_triple_spo(obj.storid, self._Prop.storid, removed.storid)
        if inverse:
          obj.namespace.ontology._del_obj_triple_spo(removed.storid, inverse.storid, obj.storid) # Also remove inverse
          removed.__dict__.pop(inverse.python_name, None) # Remove => force reloading; XXX optimizable
          
      for added in new - old:
        obj.namespace.ontology._add_obj_triple_spo(obj.storid, self._Prop.storid, added.storid)
        if inverse: added.__dict__.pop(inverse.python_name, None) # Remove => force reloading; XXX optimizable
        
    elif self._Prop._owl_type == owl_data_property:
      for removed in old - new:
        obj.namespace.ontology._del_data_triple_spod(obj.storid, self._Prop.storid, obj.namespace.ontology._to_rdf(removed)[0], None)
        
      for added in new - old:
        obj.namespace.ontology._add_data_triple_spod(obj.storid, self._Prop.storid, *obj.namespace.ontology._to_rdf(added))
        
    else: #self._Prop._owl_type == owl_annotation_property:
      for removed in old - new:
        if hasattr(removed, "storid"):
          obj.namespace.ontology._del_obj_triple_spo(obj.storid, self._Prop.storid, removed.storid)
        else:
          obj.namespace.ontology._del_data_triple_spod(obj.storid, self._Prop.storid, obj.namespace.ontology._to_rdf(removed)[0], None)
          
      for added in new - old:
        if hasattr(added, "storid"):
          obj.namespace.ontology._add_obj_triple_spo(obj.storid, self._Prop.storid, added.storid)
        else:
          obj.namespace.ontology._add_data_triple_spod(obj.storid, self._Prop.storid, *obj.namespace.ontology._to_rdf(added))

class FunctionalIndividualValueList(IndividualValueList):
  __slots__ = []
  def _callback(self, obj, old):
    super()._callback(obj, old)
    if not isinstance(obj, EntityClass): # Update cache
      if self: obj.__dict__[self._Prop.python_name] = self[0]
      else:    obj.__dict__[self._Prop.python_name] = None
      
          
class ClassValueList(CallbackListWithLanguage):
  __slots__ = ["_Prop"]
  def __init__(self, l, obj, Prop):
    list.__init__(self, l)
    self._obj  = obj
    self._Prop = Prop
    
  def _callback(self, obj, old):
    self._obj._on_class_prop_changed(self._Prop, old, self)
    
  def indirect(self):
    return self._Prop._get_indirect_values_for_class(self._obj)
  
