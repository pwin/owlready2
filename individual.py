# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2017 Jean-Baptiste LAMY
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

import owlready2
from owlready2.namespace import *
from owlready2.entity    import *
from owlready2.entity    import _inherited_property_value_restrictions


class ValueList(CallbackListWithLanguage):
  __slots__ = ["_Prop"]
  def __init__(self, l, obj, Prop):
    list.__init__(self, l)
    self._obj  = obj
    self._Prop = Prop
    
  def _callback(self, obj, old):
    old = set(old)
    new = set(self)
    inverse  = self._Prop.inverse_property
    
    for removed in old - new:
      obj.namespace.ontology.del_triple(obj.storid, self._Prop.storid, obj.namespace.ontology._to_rdf(removed))
      if inverse:
        obj.namespace.ontology.del_triple(removed.storid, inverse.storid, obj.storid) # Also remove inverse
        removed.__dict__.pop(inverse.python_name, None) # Remove => force reloading; XXX optimizable
        
    for added in new - old:
      obj.namespace.ontology.add_triple(obj.storid, self._Prop.storid, obj.namespace.ontology._to_rdf(added))
      if inverse: added.__dict__.pop(inverse.python_name, None) # Remove => force reloading; XXX optimizable
      

    
class Thing(metaclass = ThingClass):
  namespace = owl
  
  def get_name(self): return self._name
  def set_name(self, name):
    self._name = name
    self.namespace.world.refactor(self.storid, "%s%s" % (self.namespace.base_iri, name))
  name = property(get_name, set_name)
  
  def get_iri(self): return "%s%s" % (self.namespace.base_iri, self._name)
  def set_iri(self, new_iri):
    splitted = new_iri.rsplit("#", 1)
    if len(splitted) == 2:
      self.namespace = self.namespace.ontology.get_namespace("%s#" % splitted[0])
    else:
      splitted = new_iri.rsplit("/", 1)
      self.namespace = self.namespace.ontology.get_namespace("%s/" % splitted[0])
    self._name = splitted[1]
    self.namespace.world.refactor(self.storid, new_iri)
  iri = property(get_iri, set_iri)
  
  def __init__(self, name = None, namespace = None, **kargs):
    self.namespace = namespace or CURRENT_NAMESPACES[-1] or self.__class__.namespace
    if isinstance(self.__class__, FusionClass):
      self.__dict__["is_a"] = CallbackList(self.__class__.__bases__, self, Thing._instance_is_a_changed)
    else:
      self.__dict__["is_a"] = CallbackList([self.__class__], self, Thing._instance_is_a_changed)
    self.__dict__["_equivalent_to"] = None
    if name:
      iri = "%s%s" % (self.namespace.base_iri, name)
      self._name = name
    else:
      iri = self.namespace.world.new_numbered_iri("%s%s" % (self.namespace.base_iri, self.generate_default_name()))
      self._name = iri[len(self.namespace.base_iri):]
    self.storid = self.namespace.world.abbreviate(iri)
    self.namespace.world._entities[self.storid] = self
    
    if not LOADING:
      self.namespace.ontology.add_triple(self.storid, rdf_type, owl_named_individual)
      for parent in self.is_a:
        self.namespace.ontology.add_triple(self.storid, rdf_type, parent.storid)
        
      for attr, value in kargs.items(): setattr(self, attr, value)
      
  def generate_default_name(self): return self.__class__.name.lower()
  
  def _get_is_instance_of(self):    return self.is_a
  def _set_is_instance_of(self, v): self.is_a = v
  is_instance_of = property(_get_is_instance_of, _set_is_instance_of)
  
  def _instance_is_a_changed(self, old):
    new = set(self.is_a)
    old = set(old)
    
    for base in old - new:
      if not LOADING: self.namespace.ontology.del_triple(self.storid, rdf_type, base.storid)
      if isinstance(base, ClassConstruct): base._set_ontology(None)
    bases = ThingClass._find_base_classes(self.is_a)
    if len(bases) == 1:
      self.__class__ = bases[0]
    elif bases:
      self.__class__ = FusionClass._get_fusion_class(bases)
    else:
      self.__class__ = Thing
      list.insert(self.is_a, 0, Thing)
      
    for base in new - old:
      if isinstance(base, ClassConstruct): base._set_ontology(self.namespace.ontology)
      if not LOADING: self.namespace.ontology.add_triple(self.storid, rdf_type, base.storid)
      
  #def __attrs__(self): # Not Python standard, but used by EditObj
  
  def get_equivalent_to(self):
    if self._equivalent_to is None:
      eqs = [
        self.namespace.world._to_python(o)
        for o in self.namespace.world.get_transitive_sym(self.storid, owl_equivalentindividual)
        if o != self.storid
      ]
      self._equivalent_to = CallbackList(eqs, self, Thing._instance_equivalent_to_changed)
    return self._equivalent_to
  
  def set_equivalent_to(self, value): self.equivalent_to.reinit(value)
  
  equivalent_to = property(get_equivalent_to, set_equivalent_to)
  
  def _instance_equivalent_to_changed(self, old):
    new = frozenset(self._equivalent_to)
    old = frozenset(old)

    for x in old - new:
      self.namespace.ontology.del_triple(self.storid, owl_equivalentindividual, x   .storid)
      self.namespace.ontology.del_triple(x   .storid, owl_equivalentindividual, self.storid)
      if isinstance(x, ClassConstruct): x._set_ontology(None)
      else: # Invalidate it
        for x2 in x.equivalent_to: x2._equivalent_to = None
        x._equivalent_to = None

    for x in new - old:
      self.namespace.ontology.add_triple(self.storid, owl_equivalentindividual, x.storid)
      if isinstance(x, ClassConstruct): x._set_ontology(self.namespace.ontology)
      else: # Invalidate it
        for x2 in x.equivalent_to: x2._equivalent_to = None
        x._equivalent_to = None

    self._equivalent_to = None # Invalidate, because the addition / removal may add its own equivalent.
  
  def differents(self):
    for s, p, o, c in self.namespace.world.get_quads(None, rdf_type, owl_alldifferent, None):
      onto = self.namespace.world.graph.context_2_user_context(c)
      list_bnode = self.namespace.world.get_triple_sp(s, owl_distinctmembers)
      storids = set(onto._parse_list_as_rdf(list_bnode))
      if self.storid in storids: yield onto._parse_bnode(s)
      
  
  def __getattr__(self, attr):
    if attr == "equivalent_to": return self.get_equivalent_to()
    
    Prop = self.namespace.world._props.get(attr)
    if Prop is None: raise AttributeError("'%s' property is not defined." % attr)
    
    #for domain in Prop.domain:
    #  if not domain._satisfied_by(self):
    #    try:    repr_self = repr(self)
    #    except: repr_self = "<instance of %s>" % self.__class__
    #    raise AttributeError("%s has no attribute '%s', and '%s' property has incompatible domain." % (repr_self, attr, attr))
    
    values = [self.namespace.ontology._to_python(o) for o in self.namespace.world.get_triples_sp(self.storid, Prop.storid)]
    if Prop.is_functional_for(self.__class__):
      if (not values) and Prop.inverse_property:
        values = [self.namespace.ontology._to_python(s) for s in self.namespace.world.get_triples_po(Prop.inverse_property.storid, self.storid)]
      if   len(values) > 1:
        try:    repr_self = repr(self)
        except: repr_self = "<instance of %s>" % self.__class__
        raise AttributeError("More than one value for %s.%s (storid %s), but the property if functional or the class has been restricted." % (repr_self, attr, self.storid))
      elif not values: values = None
      else:            values = values[0]
      
    else:
      if Prop.inverse_property:
        values.extend(self.namespace.ontology._to_python(s) for s in self.namespace.world.get_triples_po(Prop.inverse_property.storid, self.storid))
      values = ValueList(values, self, Prop)
      
    self.__dict__[attr] = values
    return values
  
  def __setattr__(self, attr, value):
    if attr == "equivalent_to": return self.set_equivalent_to(value)
    
    if attr in SPECIAL_ATTRS:
      if attr == "is_a": self.is_a.reinit(value)
      else:              super().__setattr__(attr, value)
    else:
      Prop = self.namespace.world._props.get(attr)
      if Prop:
        old_value = self.__dict__.get(attr, None)
        
        if Prop.is_functional_for(self.__class__):
          if Prop.inverse_property and (not old_value is None):
            old_value.__dict__.pop(Prop.inverse_property.python_name, None) # Remove => force reloading; XXX optimizable
            self.namespace.ontology.del_triple(old_value.storid, Prop.inverse_property.storid, self.storid) # Also remove inverse
            
          super().__setattr__(attr, value)
          
          if value is None:
            self.namespace.ontology.del_triple(self.storid, Prop.storid, None)
          else:
            self.namespace.ontology.set_triple(self.storid, Prop.storid, self.namespace.ontology._to_rdf(value))
            if Prop.inverse_property: value.__dict__.pop(Prop.inverse_property.python_name, None) # Remove => force reloading; XXX optimizable
            
        else:
          if not isinstance(value, list): raise ValueError("Property '%s' is not functional, cannot assign directly (use .append() or assign a list)." % attr)
          getattr(self, attr).reinit(value)
          
      else:
        super().__setattr__(attr, value)
        
  def _get_instance_possible_relations(self, ignore_domainless_properties = False):
    for Prop in self.namespace.world._reasoning_props.values():
      all_domains = set(Prop.domains_indirect())
      if ignore_domainless_properties and (not all_domains):
        for restrict in _inherited_property_value_restrictions(self, Prop):
          yield Prop
          break
      else:
        for domain in all_domains:
          if not domain._satisfied_by(self): break
        else:
          yield Prop
  
  


class Nothing(Thing): pass


class FusionClass(ThingClass):
  ontology = anonymous
  
  _FUSION_CLASSES = {}
  
  @staticmethod
  def _get_fusion_class(Classes):
    Classes = _keep_most_specific(Classes)
    Classes = tuple(sorted(Classes, key = lambda Class: Class.__name__))
    if len(Classes) == 1: return Classes[0]
    if Classes in FusionClass._FUSION_CLASSES: return FusionClass._FUSION_CLASSES[Classes]
    name = "_AND_".join(Class.__name__ for Class in Classes)
    with anonymous: # Force triple insertion into anonymous
      fusion_class = FusionClass._FUSION_CLASSES[Classes] = FusionClass(name, Classes, { "namespace" : anonymous })
    return fusion_class

