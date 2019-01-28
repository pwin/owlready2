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

umls = get_ontology("http://umls/")
umls.model    = umls.get_namespace("http://umls/model/")
umls.CUI      = umls.get_namespace("http://umls/CUI/")
umls._src     = umls.get_namespace("http://umls/SRC/")

class UMLSOntology(Ontology):
  def get_terminology(self, name): return self._src["V-%s" % name]
  def get_unified_concept(self, cui): return 
  __getitem__ = get_terminology
umls.__class__ = UMLSOntology
  
class UMLSConceptNamespace(Namespace):
  pass
umls.CUI.__class__ = UMLSConceptNamespace

def _sort_by_name(x): return x.name

class MetaOriginalConcept(ThingClass):
  def __new__(MetaClass, name, superclasses, obj_dict):
    if superclasses == (Thing,): return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    else:                        return type.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __repr__(Class):
    terminology = Class.terminology
    if not terminology: return ThingClass.__repr__(Class)
    return """%s["%s"] # %s\n""" % (terminology.name[2:], Class.name, Class.label.first())
  
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
      r = Class.namespace.world._get_data_triple_sp_od(Class.storid, umls.model.terminology.storid)[0]
      r = IRIS["http://umls/SRC/V-%s" % r]
      type.__setattr__(Class, "__terminology", r)
      return r
      return None
    
    return ThingClass.__getattr__(Class, attr)
  
  def __getitem__(Class, code):
    if Class.terminology.name == "V-SRC":
      return Class.namespace.world["http://umls/%s/%s" % (Class.name[2:], code)]
    else:
      return Class.namespace.world["http://umls/%s/%s" % (Class.terminology.name[2:], code)]
  
  def full_code(Class):
    return u"%s:%s" % (Class.terminology.name[2:], Class.name)

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
    if destination_terminology is Class.terminology: return Concepts([Class])
    if destination_terminology is umls.concepts: return Class.unifieds
    
    if Class.terminology.name == "V-SRC":
      return ThingClass.__rshift__(Class, destination_terminology)
    dest = destination_terminology.name[2:]
    
    return Concepts([
      Class.namespace.world._get_by_storid(i)
      for (i,) in Class.namespace.world.graph.execute(
"""SELECT DISTINCT to3.o FROM objs t, objs tu1, objs tu2, objs to1, objs to2, objs to3
WHERE t.s=? AND t.p=?
AND tu1.s = t.o AND tu1.p=? AND tu1.o=?
AND tu2.s = t.o AND tu2.p=?
AND to1.s = tu2.o AND to1.p=?
AND to2.s = to1.o AND to2.p=? AND to2.o=?
AND to3.s = to1.o AND to3.p=?
""", (
  Class.storid, rdfs_subclassof,
  owl_onproperty, umls.model.unifieds.storid,
  SOME,
  rdfs_subclassof,
  owl_onproperty, umls.model.originals.storid,
  SOME,
  ))
      if default_world._get_data_triple_sp_od(i, umls.model.terminology.storid)[0] == dest
    ])
  
  
class MetaUnifiedConcept(ThingClass):
  def __new__(MetaClass, name, superclasses, obj_dict):
    if superclasses == (Thing,): return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    else:                        return type.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __repr__(Class):
    return """CUI["%s"] # %s\n""" % (Class.name, Class.label.first())


class MetaGroup(ThingClass):
  def __new__(MetaClass, name, superclasses, obj_dict):
    if superclasses == (Thing,): return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    else:                        return type.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __repr__(Class):
    return """<Group %s> # %s\n""" % (Class.name, " ; ".join("%s=%s" % (prop.label.first() or prop.name, ",".join(v.label.first() for v in prop[Class])) for prop in Class.get_class_properties()))
    
    
with umls.model:
  class OriginalConcept(Thing, metaclass = MetaOriginalConcept):
    pass
  type.__setattr__(OriginalConcept, "__terminology", None)
  type.__setattr__(OriginalConcept, "__children", [])
  type.__setattr__(OriginalConcept, "__parents" , [])
  
  class UnifiedConcept(Thing, metaclass = MetaUnifiedConcept):
    pass
  type.__setattr__(UnifiedConcept, "terminology", "CUI")

  class Group(Thing, metaclass = MetaGroup):
    pass
      

def Concepts(x): return set(x)

