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

from owlready2.namespace import *

from owlready2.base import _universal_iri_2_abbrev, _universal_abbrev_2_datatype, _universal_datatype_2_abbrev
_non_negative_integer = _universal_iri_2_abbrev["http://www.w3.org/2001/XMLSchema#nonNegativeInteger"]

class ClassConstruct(object):
  def __and__(a, b): return And([a, b])
  def __or__ (a, b): return Or ([a, b])
  def __invert__(a): return Not(a)
  
  def __init__(self, ontology = None, bnode = None):
    self.ontology = ontology
    self.storid   = bnode
    
    if ontology and not LOADING: self._create_triples(ontology)
    
  def _set_ontology(self, ontology):
    if not LOADING:
      if   self.ontology and not ontology:
        self._destroy_triples(self.ontology)
      elif ontology and not self.ontology:
        if self.storid is None: self.storid = ontology.world.new_blank_node()
        self._create_triples(ontology)
      elif ontology and self.ontology:
        raise OwlReadySharedBlankNodeError("A ClassConstruct cannot be shared by two ontologies, because it correspond to a RDF blank node. Please create a dupplicate.")
    self.ontology = ontology
    if self.ontology: self.ontology._bnodes[self.storid] = self
    
  def destroy(self): self._destroy_triples()
  
  def _destroy_triples(self, ontology):
    ontology._del_obj_triple_spod(self.storid, None, None)
    ontology._del_data_triple_spoddd(self.storid, None, None, None)
    
  def _create_triples (self, ontology):
    pass
  
  def subclasses(self, only_loaded = False):
    if only_loaded:
      r = []
      for x in self.ontology.world._get_obj_triples_po_s(rdfs_subclassof, self.storid):
        if not x < 0:
          r.append(self.ontology.world._entities.get(x))
      return r
    
    else:
      return [
        self.ontology.world._get_by_storid(x, None, ThingClass, self.ontology)
        for x in self.ontology.world._get_obj_triples_po_s(rdfs_subclassof, self.storid)
        if not x < 0
      ]
  

class Not(ClassConstruct):
  def __init__(self, Class, ontology = None, bnode = None):
    super().__init__(ontology, bnode)
    if not Class is None: self.__dict__["Class"] = Class
    
  def __eq__(self, other):
    return isinstance(other, Not) and (self.Class == other.Class)
  
  __hash__ = object.__hash__
  
  def __repr__(self): return "Not(%s)" % (self.Class)
  
  def __getattr__(self, attr):
    if attr == "Class":
      self.__dict__["Class"] = C = self.ontology._to_python(self.ontology._get_obj_triple_sp_o(self.storid, owl_complementof), default_to_none = True)
      return C
    return super().__getattribute__(attr)
  
  def destroy(self):
    if isinstance(self.Class, ClassConstruct): self.Class.destroy()
    ClassConstruct.destory(self)
    
  def _set_ontology(self, ontology):
    if isinstance(self.Class, ClassConstruct): self.Class._set_ontology(ontology)
    super()._set_ontology(ontology)
    
  def __setattr__(self, attr, value):
    super().__setattr__(attr, value)
    if (attr == "Class") and self.ontology: self._create_triples(self.ontology)
    
  def _create_triples(self, ontology):
    ClassConstruct._create_triples(self, ontology)
    ontology._set_obj_triple_spo(self.storid, rdf_type, owl_class)
    ontology._set_obj_triple_spo(self.storid, owl_complementof, self.Class.storid)
    
  def _satisfied_by(self, x):
    return not self.Class._satisfied_by(x)
  
  
class Inverse(ClassConstruct):
  def __new__(Class, Property, ontology = None, bnode = None, simplify = True):
    if simplify:
      if isinstance(Property, Inverse): return Property.property
      if Property.inverse_property: return Property.inverse_property
    return object.__new__(Class)
  
  def __eq__(self, other):
    return isinstance(other, Inverse) and (self.property == other.property)
  
  __hash__ = object.__hash__
  
  def __init__(self, Property, ontology = None, bnode = None, simplify = True):
    super().__init__(ontology, bnode)
    self.__dict__["property"] = Property
    
  def __repr__(self): return "Inverse(%s)" % (self.property)
  
  def __setattr__(self, attr, value):
    super().__setattr__(attr, value)
    if (attr == "property") and self.ontology: self._create_triples(self.ontology)
    
  def _create_triples(self, ontology):
    ClassConstruct._create_triples(self, ontology)
    ontology._set_obj_triple_spo(self.storid, owl_inverse_property, self.property.storid)
  
  def some   (self,     value): return Restriction(self, SOME   , None, value)
  def only   (self,     value): return Restriction(self, ONLY   , None, value)
  def value  (self,     value): return Restriction(self, VALUE  , None, value)
  def exactly(self, nb, value = None): return Restriction(self, EXACTLY, nb  , value)
  def min    (self, nb, value = None): return Restriction(self, MIN    , nb  , value)
  def max    (self, nb, value = None): return Restriction(self, MAX    , nb  , value)
  
  


class LogicalClassConstruct(ClassConstruct):
  def __init__(self, Classes, ontology = None, bnode = None):
    if isinstance(Classes, int):
      self._list_bnode = Classes
    else:
      self._list_bnode = None
      self.Classes = CallbackList(Classes, self, LogicalClassConstruct._callback)
    ClassConstruct.__init__(self, ontology, bnode)
    
  def __eq__(self, other):
    return isinstance(other, self.__class__) and (self.Classes == other.Classes)
  
  __hash__ = object.__hash__
  
  def __rshift__(Domain, Range):
    import owlready2.prop
    owlready2.prop._next_domain_range = (Domain, Range)
    if isinstance(Range, ThingClass) or isinstance(Range, ClassConstruct):
      return owlready2.prop.ObjectProperty
    else:
      return owlready2.prop.DataProperty
    
  def _set_ontology(self, ontology):
    if ontology and (self._list_bnode is None): self._list_bnode = ontology.world.new_blank_node()
    for Class in self.Classes:
      if isinstance(Class, ClassConstruct): Class._set_ontology(ontology)
    super()._set_ontology(ontology)
      
  def __getattr__(self, attr):
    if attr == "Classes":
      self.Classes = CallbackList(self.ontology._parse_list(self._list_bnode), self, LogicalClassConstruct._callback)
      return self.Classes
    return super().__getattribute__(attr)
  
  def _invalidate_list(self):
    try: del self.Classes
    except: pass
    
  def _callback(self, old):
    if self.ontology:
      self._destroy_triples(self.ontology)
      self._create_triples (self.ontology)
      
  def _destroy_triples(self, ontology):
    ClassConstruct._destroy_triples(self, ontology)
    ontology._del_list(self._list_bnode)
    
  def _create_triples(self, ontology):
    ClassConstruct._create_triples(self, ontology)
    if self.Classes and (self.Classes[0] in _universal_datatype_2_abbrev):
      ontology._add_obj_triple_spo(self.storid, rdf_type, rdfs_datatype)
    else:
      ontology._add_obj_triple_spo(self.storid, rdf_type, owl_class)
    ontology._add_obj_triple_spo(self.storid, self._owl_op, self._list_bnode)
    ontology._set_list(self._list_bnode, self.Classes)
    
  def __repr__(self):
    s = []
    for x in self.Classes:
      if isinstance(x, LogicalClassConstruct): s.append("(%s)" % x)
      else:                                    s.append(repr(x))
    if (len(s) <= 1): return "%s([%s])" % (self.__class__.__name__, ", ".join(s))
    return self._char.join(s)

  
class Or(LogicalClassConstruct):
  _owl_op = owl_unionof
  _char   = " | "
  
  def __or__ (self, b):
    return Or([*self.Classes, b])
  
  def _satisfied_by(self, x):
    for Class in self.Classes:
      if Class._satisfied_by(x): return True
    return False
  
class And(LogicalClassConstruct):
  _owl_op = owl_intersectionof
  _char   = " & "
  
  def __and__ (self, b):
    return And([*self.Classes, b])
  
  def _satisfied_by(self, x):
    for Class in self.Classes:
      if not Class._satisfied_by(x): return False
    return True


_qualified_2_non_qualified = {
  EXACTLY : owl_cardinality,
  MIN     : owl_min_cardinality,
  MAX     : owl_max_cardinality,
}
_restriction_type_2_label = {
  SOME    : "some",
  ONLY    : "only",
  VALUE   : "value",
  HAS_SELF: "has_self",
  EXACTLY : "exactly",
  MIN     : "min",
  MAX     : "max",
  }

class Restriction(ClassConstruct):
  def __init__(self, Property, type, cardinality = None, value = None, ontology = None, bnode = None):
    self.__dict__["property"]    = Property
    self.__dict__["type"]        = type
    self.__dict__["cardinality"] = cardinality
    if (not value is None) or (not bnode):
      self.__dict__["value"]     = value
      
    super().__init__(ontology, bnode)

  def __eq__(self, other):
    return isinstance(other, Restriction) and (self.type is other.type) and (self.property is other.property) and (self.value == other.value) and (self.cardinality == other.cardinality)
  
  __hash__ = object.__hash__
  
  def __repr__(self):
    if (self.type == SOME) or (self.type == ONLY) or (self.type == VALUE) or (self.type == HAS_SELF):
      return """%s.%s(%s)""" % (self.property, _restriction_type_2_label[self.type], self.value)
    else:
      return """%s.%s(%s, %s)""" % (self.property, _restriction_type_2_label[self.type], self.cardinality, self.value)
    
  def _set_ontology(self, ontology):
    if isinstance(self.property, ClassConstruct): self.property._set_ontology(ontology)
    if isinstance(self.value,    ClassConstruct): self.value   ._set_ontology(ontology)
    super()._set_ontology(ontology)
    
  def _create_triples(self, ontology):
    ClassConstruct._create_triples(self, ontology)
    ontology._add_obj_triple_spo(self.storid, rdf_type, owl_restriction)
    ontology._add_obj_triple_spo(self.storid, owl_onproperty, self.property.storid)
    if (self.type == SOME) or (self.type == ONLY) or (self.type == VALUE) or (self.type == HAS_SELF):
      o, d = ontology.world._to_rdf(self.value)
      if d is None: ontology._add_obj_triple_spo  (self.storid, self.type, o)
      else:         ontology._add_data_triple_spoddd(self.storid, self.type, o, d)
    else:
      if self.value is None:
        if not self.cardinality is None: ontology._add_data_triple_spoddd(self.storid, _qualified_2_non_qualified[self.type], self.cardinality, _non_negative_integer)
      else:
        if not self.cardinality is None: ontology._add_data_triple_spoddd(self.storid, self.type, self.cardinality, _non_negative_integer)
        o, d = ontology.world._to_rdf(self.value)
        if self.value in _universal_datatype_2_abbrev:
          ontology._add_obj_triple_spo(self.storid, owl_ondatarange, o)
        else:
          ontology._add_obj_triple_spo(self.storid, owl_onclass, o)
          
  def __getattr__(self, attr):
    if attr == "value":
      if (self.type == SOME) or (self.type == ONLY) or (self.type == HAS_SELF):
        v = self.ontology._get_obj_triple_sp_o(self.storid, self.type)
        v = self.__dict__["value"] = self.ontology.world._to_python(v, None, default_to_none = True)
      elif self.type == VALUE:
        v, d = self.ontology._get_triple_sp_od(self.storid, self.type)
        v = self.__dict__["value"] = self.ontology.world._to_python(v, d, default_to_none = True)
      else:
        v = self.ontology._get_obj_triple_sp_o(self.storid, owl_onclass) or self.ontology._get_obj_triple_sp_o(self.storid, owl_ondatarange)
        if v is None:
          v = self.__dict__["value"] = None
        else:
          v = self.__dict__["value"] = self.ontology.world._to_python(v, default_to_none = True)
      return v
    return super().__getattribute__(attr)
  
  def __setattr__(self, attr, v):
    super().__setattr__(attr, v)
    if ((attr == "property") or (attr == "type") or (attr == "cardinality") or (attr == "value")) and self.ontology:
      self._destroy_triples(self.ontology)
      self._create_triples (self.ontology)
      
  def _satisfied_by(self, x):
    if isinstance(x, EntityClass): return True # XXX not doable on classes
    
    values = self.property[x]
    if   self.type == SOME:
      for obj in values:
        if self.value._satisfied_by(obj): return True
      return False
    
    elif self.type == ONLY:
      for obj in values:
        if not self.value._satisfied_by(obj): return False
      return True
    
    elif self.type == VALUE:
      for obj in values:
        if obj is self.value: return True
      return False
    
    elif self.type == HAS_SELF:
      return x in values
      
    else:
      nb = 0
      for obj in values:
        if self.value._satisfied_by(obj): nb += 1
      if   self.type == MIN:     return nb >= self.cardinality
      elif self.type == MAX:     return nb <= self.cardinality
      elif self.type == EXACTLY: return nb == self.cardinality
      
      
class OneOf(ClassConstruct):
  def __init__(self, instances, ontology = None, bnode = None):
    if isinstance(instances, int):
      self._list_bnode = instances
    else:
      self._list_bnode = None
      self.instances = CallbackList(instances, self, OneOf._callback)
    ClassConstruct.__init__(self, ontology, bnode)
    
  def __eq__(self, other):
    return isinstance(other, OneOf) and (self.instances == other.instances)
  
  __hash__ = object.__hash__
  
  def __getattr__(self, attr):
    if attr == "instances":
      self.instances = CallbackList(self.ontology._parse_list(self._list_bnode), self, OneOf._callback)
      return self.instances
    return super().__getattribute__(attr)
  
  def _invalidate_list(self):
    try: del self.instances
    except: pass
    
  def _callback(self, old):
    if self.ontology:
      self._destroy_triples(self.ontology)
      self._create_triples (self.ontology)
      
  def _destroy_triples(self, ontology):
    ClassConstruct._destroy_triples(self, ontology)
    ontology._del_list(self._list_bnode)
    
  def _create_triples(self, ontology):
    if ontology and (self._list_bnode is None): self._list_bnode = ontology.world.new_blank_node()
    ClassConstruct._create_triples(self, ontology)
    if self.instances and (not hasattr(self.instances[0], "storid")):
      ontology._set_obj_triple_spo(self.storid, rdf_type, rdfs_datatype)
    else:
      ontology._set_obj_triple_spo(self.storid, rdf_type, owl_class)
    ontology._set_obj_triple_spo(self.storid, owl_oneof, self._list_bnode)
    ontology._set_list(self._list_bnode, self.instances)
    
  def _satisfied_by(self, x): return x in self.instances
  
  def __repr__(self): return "OneOf([%s])" % ", ".join(repr(x) for x in self.instances) 

  
_PY_FACETS   = {}
_RDFS_FACETS = {}
def _facets(py_name, rdfs_name, value_datatype, value_datatype_abbrev):
  _PY_FACETS  [py_name  ] = (rdfs_name, value_datatype, value_datatype_abbrev)
  _RDFS_FACETS[rdfs_name] = (py_name  , value_datatype, value_datatype_abbrev)
  
_facets("length", xmls_length, int, _universal_iri_2_abbrev["http://www.w3.org/2001/XMLSchema#nonNegativeInteger"])
_facets("min_length", xmls_minlength, int, _universal_iri_2_abbrev["http://www.w3.org/2001/XMLSchema#nonNegativeInteger"])
_facets("max_length", xmls_maxlength, int, _universal_iri_2_abbrev["http://www.w3.org/2001/XMLSchema#nonNegativeInteger"])
_facets("pattern", xmls_pattern, str, _universal_iri_2_abbrev["http://www.w3.org/2001/XMLSchema#string"])
_facets("white_space", xmls_whitespace, str, "")
_facets("max_inclusive", xmls_maxinclusive, int, "__datatype__")
_facets("max_exclusive", xmls_maxexclusive, int, "__datatype__")
_facets("min_inclusive", xmls_mininclusive, int, "__datatype__")
_facets("min_exclusive", xmls_minexclusive, int, "__datatype__")
_facets("total_digits", xmls_totaldigits, int, _universal_iri_2_abbrev["http://www.w3.org/2001/XMLSchema#positiveInteger"])
_facets("fraction_digits", xmls_fractiondigits, int, _universal_iri_2_abbrev["http://www.w3.org/2001/XMLSchema#nonNegativeInteger"])

class ConstrainedDatatype(ClassConstruct):
  def __init__(self, base_datatype, ontology = None, bnode = None, list_bnode = None, **kargs):
    ClassConstruct.__init__(self, ontology, bnode)
    self.__dict__["base_datatype"] = base_datatype
    self._list_bnode               = list_bnode
    
    if list_bnode:
      l = ontology._parse_list_as_rdf(list_bnode)
      for bn, dropit in l:
        for p,o,d in ontology._get_data_triples_s_pod(bn):
          if p in _RDFS_FACETS:
            py_name, value_datatype, value_datatype_abbrev = _RDFS_FACETS[p]
            self.__dict__[py_name] = from_literal(o, d)
    else:
      for k, v in kargs.items():
        if not k in _PY_FACETS: raise ValueError("No facet '%s'!" % k)
        self.__dict__[k] = v
        
  def __setattr__(self, attr, value):
    self.__dict__[attr] = value
    if (not LOADING) and self.ontology and ((attr in _PY_FACETS) or (attr == "base_datatype")):
      self._destroy_triples(self.ontology)
      self._create_triples (self.ontology)
      
  def __repr__(self):
    s = []
    for k in _PY_FACETS:
      v = getattr(self, k, None)
      if not v is None:
        s.append("%s = %s" % (k, v))
    return "ConstrainedDatatype(%s, %s)" % (self.base_datatype.__name__, ", ".join(s))
  
  def _destroy_triples(self, ontology):
    ClassConstruct._destroy_triples(self, ontology)
    ontology._del_list(self._list_bnode)
    
  def _create_triples (self, ontology):
    ClassConstruct._create_triples(self, ontology)
    if self._list_bnode is None: self._list_bnode = ontology.world.new_blank_node()
    ontology._set_obj_triple_spo(self.storid, rdf_type, rdfs_datatype)
    ontology._set_obj_triple_spo(self.storid, owl_ondatatype, _universal_datatype_2_abbrev[self.base_datatype])
    ontology._set_obj_triple_spo(self.storid, owl_withrestrictions, self._list_bnode)
    l = []
    for k, (rdfs_name, value_datatype, value_datatype_abbrev) in _PY_FACETS.items():
      v = getattr(self, k, None)
      if not v is None:
        if value_datatype_abbrev == "__datatype__":
          value_datatype_abbrev = _universal_datatype_2_abbrev[self.base_datatype]
        bn = ontology.world.new_blank_node()
        ontology._set_data_triple_spoddd(bn, rdfs_name, v, value_datatype_abbrev)
        l.append((bn, None))
    ontology._set_list_as_rdf(self._list_bnode, l)
    
