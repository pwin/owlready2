# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2019 Jean-Baptiste LAMY
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

from owlready2 import *

UMLS          = get_ontology("http://UMLS/")
UMLS.model    = UMLS.get_namespace("http://UMLS/model/")
UMLS._src     = UMLS.get_namespace("http://UMLS/SRC/")

class UMLSOntology(Ontology):
  def get_terminology(self, name): return self._src["%s" % name]
  def get_unified_concept(self, cui): return 
  __getitem__ = get_terminology
UMLS.__class__ = UMLSOntology

#class UMLSConceptNamespace(Namespace):
#  pass
#UMLS.CUI.__class__ = UMLSConceptNamespace

def _sort_by_name(x): return x.name

class MetaConcept(ThingClass):
  def __new__(MetaClass, name, superclasses, obj_dict):
    #if superclasses == (Thing,): return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    #else:                        return type.__new__(MetaClass, name, superclasses, obj_dict)
    if LOADING:
      return type.__new__(MetaClass, name, superclasses, obj_dict)
    else:
      return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
      
    
  def __repr__(Class):
    terminology = Class.terminology
    if not terminology: return ThingClass.__repr__(Class)
    return """%s["%s"] # %s\n""" % (terminology.name, Class.name, Class.label.first())
  
  def __getattr__(Class, attr):
    attr2 = "__%s" % attr
    r = Class.__dict__.get(attr2, Ellipsis)
    if not r is Ellipsis: return r
    
    if   attr == "children":
      r = list(Class.subclasses())
      r.sort(key = _sort_by_name)
      type.__setattr__(Class, "__children", r)
      return r
    
    elif attr == "parents":
      r = [i for i in Class.is_a if isinstance(i, ThingClass)]
      r.sort(key = _sort_by_name)
      type.__setattr__(Class, "__parents", r)
      return r
    
    elif attr == "terminology":
      r = Class.namespace.world._get_obj_triple_sp_o(Class.storid, UMLS.model.terminology.storid)
      r = Class.namespace.world._get_by_storid(r)
      type.__setattr__(Class, "__terminology", r)
      return r
    
    return ThingClass.__getattr__(Class, attr)
  
  def __getitem__(Class, code):
    if Class.terminology.name == "SRC":
      return Class.namespace.world["http://UMLS/%s/%s" % (Class.name, code)]
    else:
      return Class.namespace.world["http://UMLS/%s/%s" % (Class.terminology.name, code)]
  
  def full_code(Class):
    return u"%s:%s" % (Class.terminology.name, Class.name)

  def has_concept(Class, code):
    return not Class[code] is None
  
  def ancestor_concepts(Class, include_self = True, no_double = True):
    l = []
    Class._fill_ancestor_concepts(l, { OriginalConcept }, include_self, no_double)
    return l
  
  def _fill_ancestor_concepts(Class, l, s, include_self, no_double):
    if include_self and (not Class in s):
        l.append(Class)
        if no_double: s.add(Class)
        for equivalent in Class.equivalent_to.indirect():
          if isinstance(equivalent, MetaOriginalConcept) and not equivalent in s:
            equivalent._fill_ancestor_concepts(l, s, True, no_double)
    for parent in Class.parents:
      parent._fill_ancestor_concepts(l, s, True, no_double)
      
  def descendant_concepts(Class, include_self = True, no_double = True):
    l = []
    Class._fill_descendant_concepts(l, set(), include_self, no_double)
    return l
  
  def _fill_descendant_concepts(Class, l, s, include_self, no_double):
    if include_self:
      l.append(Class)
      if no_double: s.add(Class)
      for equivalent in Class.equivalent_to.indirect():
        if isinstance(equivalent, Class.__class__) and not equivalent in s:
          equivalent._fill_descendant_concepts(l, s, True, no_double)
          
    for child in Class.children:
      if not child in s: child._fill_descendant_concepts(l, s, True, no_double)
        
              
  def __rshift__(Class, destination_terminology):
    if Class.terminology.name == "SRC": # Property creation
      return ThingClass.__rshift__(Class, destination_terminology)
    
    return Class._map(_get_mapper(Class.terminology, destination_terminology))
  
  def _map(Class, mapper):
    r = [ Class.namespace.world._get_by_storid(i) for i in mapper(Class.storid) ]
    if r: return r
    return [ i for parent in Class.parents for i in parent._map(mapper) ]
  

_MAPPERS = {}
def _get_mapper(source, dest):
  mapper = _MAPPERS.get((source, dest))
  if not mapper:
    if   source is dest: mapper = _no_op_mapper
    elif source is _CUI: mapper = _create_from_cui_mapper(dest)
    elif dest   is _CUI: mapper = _to_cui_mapper
    else:                mapper = _create_cui_mapper(source, dest)
    _MAPPERS[source, dest] = mapper
  return mapper

def _no_op_mapper(storid):
  yield storid
  
def _create_from_cui_mapper(dest):
  def _from_cui_mapper(storid, dest_storid = dest.storid):
    for (i,) in UMLS.world.graph.execute(
"""SELECT DISTINCT to3.o FROM objs to1, objs to2, objs to3
WHERE to1.s=? AND to1.p=?
AND to2.s=to1.o AND to2.p=? AND to2.o=?
AND to3.s=to1.o AND to3.p=?
""", (
  storid, rdfs_subclassof,
  owl_onproperty, UMLS.model.originals.storid,
  SOME,
  )):
      if UMLS.world._get_obj_triple_sp_o(i, UMLS.model.terminology.storid) == dest_storid:
        yield i
  return _from_cui_mapper
  
def _to_cui_mapper(storid):
  for (i,) in UMLS.world.graph.execute(
"""SELECT DISTINCT tu2.o FROM objs t, objs tu1, objs tu2
WHERE t.s=? AND t.p=?
AND tu1.s=t.o AND tu1.p=? AND tu1.o=?
AND tu2.s=t.o AND tu2.p=?
""", (
  storid, rdfs_subclassof,
  owl_onproperty, UMLS.model.unifieds.storid,
  SOME,
  )):
    yield i
      
def _create_cui_mapper(source, dest):
  def _cui_mapper(storid, dest_storid = dest.storid):
    for (i,) in UMLS.world.graph.execute(
"""SELECT DISTINCT to3.o FROM objs t, objs tu1, objs tu2, objs to1, objs to2, objs to3
WHERE t.s=? AND t.p=?
AND tu1.s=t.o AND tu1.p=? AND tu1.o=?
AND tu2.s=t.o AND tu2.p=?
AND to1.s=tu2.o AND to1.p=?
AND to2.s=to1.o AND to2.p=? AND to2.o=?
AND to3.s=to1.o AND to3.p=?
""", (
  storid, rdfs_subclassof,
  owl_onproperty, UMLS.model.unifieds.storid,
  SOME,
  rdfs_subclassof,
  owl_onproperty, UMLS.model.originals.storid,
  SOME,
  )):
      if UMLS.world._get_obj_triple_sp_o(i, UMLS.model.terminology.storid) == dest_storid:
        yield i
  return _cui_mapper


class MetaGroup(ThingClass):
  def __new__(MetaClass, name, superclasses, obj_dict):
    if superclasses == (Thing,): return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    else:                        return type.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __repr__(Class):
    return """<Group %s> # %s\n""" % (Class.name, " ; ".join("%s=%s" % (prop.label.first() or prop.name, ",".join(v.label.first() for v in prop[Class])) for prop in Class.get_class_properties()))
    
    
with UMLS.model:
  class Concept(Thing, metaclass = MetaConcept):
    pass
  type.__setattr__(Concept, "__terminology", None)
  type.__setattr__(Concept, "__children", [])
  type.__setattr__(Concept, "__parents" , [])

  class Group(Thing, metaclass = MetaGroup):
    pass
      

def Concepts(x): return set(x)

_CUI = UMLS["CUI"]
