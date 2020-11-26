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

import operator
from functools import reduce

from owlready2 import *
from owlready2.triplelite import _SearchList

PYM          = get_ontology("http://PYM/")
PYM._src     = PYM.get_namespace("http://PYM/SRC/")

class PYMOntology(Ontology):
  def get_terminology(self, name): return self._src["%s" % name]
  __getitem__ = get_terminology
  
  def search(self, keywords):
    keywords = FTS(keywords)
    return _SearchList(self.world, [(label.storid, keywords, '*'), (PYM.terminology.storid, '*', None)]) | _SearchList(self.world, [(PYM.synonyms.storid, keywords, '*'), (PYM.terminology.storid, '*', None)])
  
PYM.__class__ = PYMOntology

def _sort_by_name(x): return x.name



class MetaConcept(ThingClass):
  def __new__(MetaClass, name, superclasses, obj_dict):
    #if superclasses == (Thing,): return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    #else:                        return type.__new__(MetaClass, name, superclasses, obj_dict)
    if LOADING:
      return type.__new__(MetaClass, name, superclasses, obj_dict)
    else:
      return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __iter__(Class): raise ValueError # Avoid some suprizing behavior when calling list(concept)
  
  def __repr__(Class):
    terminology = Class.terminology
    if not terminology: return ThingClass.__repr__(Class)
    return """%s["%s"] # %s\n""" % ("PYM" if terminology.name == "SRC" else terminology.name, Class.name, Class.label.first())
  
  def __getattr__(Class, attr):
    attr2 = "__%s" % attr
    r = Class.__dict__.get(attr2, Ellipsis)
    if not r is Ellipsis: return r
    
    if   attr == "children":
      return sorted(Class.subclasses(), key = _sort_by_name)
    
    elif attr == "parents":
      terminology = Class.terminology
      r = [i for i in Class.is_a if isinstance(i, ThingClass) and i.terminology is terminology]
      r.sort(key = _sort_by_name)
      type.__setattr__(Class, "__parents", r)
      return r
    
    elif attr == "terminology":
      r = Class.namespace.world._get_obj_triple_sp_o(Class.storid, PYM.terminology.storid)
      r = Class.namespace.world._get_by_storid(r)
      type.__setattr__(Class, "__terminology", r)
      return r
    
    return ThingClass.__getattr__(Class, attr)
  
  def __getitem__(Class, code):
    if Class.terminology.name == "SRC":
      return Class.namespace.world["http://PYM/%s/%s" % (Class.name, code)]
    else:
      return Class.namespace.world["http://PYM/%s/%s" % (Class.terminology.name, code)]
    
  def imply(Class, other): return issubclass(Class, other)
  
  def search(Class, keywords, **kargs):
    return Class.namespace.world.search(label = FTS(keywords), terminology = Class, **kargs) | Class.namespace.world.search(synonyms = FTS(keywords), terminology = Class, **kargs)
  
  def full_code(Class):
    return u"%s:%s" % (Class.terminology.name, Class.name)

  def has_concept(Class, code):
    return not Class[code] is None
  
  def ancestor_concepts(Class, include_self = True, no_double = True):
    l = []
    Class._fill_ancestor_concepts(l, { Concept }, include_self, no_double)
    return l
  
  def _fill_ancestor_concepts(Class, l, s, include_self, no_double):
    if include_self and (not Class in s):
        l.append(Class)
        if no_double: s.add(Class)
        for equivalent in Class.equivalent_to.indirect():
          if isinstance(equivalent, MetaConcept) and not equivalent in s:
            equivalent._fill_ancestor_concepts(l, s, True, no_double)
    for parent in Class.parents:
      if parent.terminology is Class.terminology:
        parent._fill_ancestor_concepts(l, s, True, no_double)
      
  def descendant_concepts(Class, include_self = True, no_double = True):
    return _DescendantList(Class, include_self, no_double)
  
  def _generate_descendant_concepts(Class, s, include_self, no_double):
    if include_self:
      yield Class
      if no_double: s.add(Class)
      for equivalent in Class.equivalent_to.indirect():
        if isinstance(equivalent, Class.__class__) and not equivalent in s:
          yield from equivalent._generate_descendant_concepts(s, True, no_double)
          
    for child in sorted(Class.subclasses(), key = _sort_by_name):
      if not child in s: yield from child._generate_descendant_concepts(s, True, no_double)
      
      
  def __rshift__(Class, destination_terminology):
    if Class.terminology.name == "SRC": # Property creation
      return ThingClass.__rshift__(Class, destination_terminology)
    
    return Class._map(_get_mapper(Class.terminology, destination_terminology))
  
  def _map(Class, mapper):
    r = Concepts(mapper(Class))
    if r: return r
    return Concepts( i for parent in Class.parents for i in parent._map(mapper) )




from owlready2.util import _LazyListMixin

class _PopulatedDescendantList(FirstList):
  __slots__ = ["term", "include_self", "no_double"]
  

class _DescendantList(FirstList, _LazyListMixin):
  __slots__ = ["term", "include_self", "no_double"]
  _PopulatedClass = _PopulatedDescendantList
  
  def __init__(self, term, include_self = True, no_double = True):
    self.term         = term
    self.include_self = include_self
    self.no_double    = no_double
    
  def _get_content(self):
    return list(self.__iter__())
  
  def __iter__(self):
    return self.term._generate_descendant_concepts(set(), self.include_self, self.no_double)


_MAPPERS = {}
def _get_mapper(source, dest):
  mapper = _MAPPERS.get((source, dest))
  if not mapper:
    if   source is dest: mapper = _no_op_mapper
    elif source is _CUI: mapper = _create_from_cui_mapper(dest)
    elif dest   is _CUI: mapper = _to_cui_mapper
    elif (source.name == "CIM10") and (dest.name == "ICD10"): mapper = _create_icd10_french_atih_2_icd10_mapper(dest)
    elif (source.name == "ICD10") and (dest.name == "CIM10"): mapper = _create_icd10_2_icd10_french_atih_mapper(dest)
    elif (source.name == "CIM10"): mapper = _chain_mapper(_get_mapper(PYM["CIM10"], PYM["ICD10"]), _get_mapper(PYM["ICD10"], dest))
    elif (dest.name   == "CIM10"): mapper = _chain_mapper(_get_mapper(source, PYM["ICD10"]), _get_mapper(PYM["ICD10"], PYM["CIM10"]))
    else:                mapper = _create_cui_mapper(source, dest)
    _MAPPERS[source, dest] = mapper
  return mapper

def _no_op_mapper(storid):
  yield storid
  
def _chain_mapper(mapper1, mapper2):
  def _mapper(c):
    for i in mapper1(c):
      for j in mapper2(i):
        yield j
  return _mapper
  
def _create_from_cui_mapper(dest):
  def _from_cui_mapper(c, dest_storid = dest.storid):
    for (i,) in PYM.world.graph.execute(
"""SELECT to3.o FROM objs to1 INDEXED BY index_objs_sp, objs to2 INDEXED BY index_objs_sp, objs to3 INDEXED BY index_objs_sp
WHERE to1.s=? AND to1.p=?
AND to2.s=to1.o AND to2.p=? AND to2.o=?
AND to3.s=to1.o AND to3.p=?
""", (
  c.storid, rdfs_subclassof,
  owl_onproperty, PYM.originals.storid,
  SOME,
  )):
      if PYM.world._get_obj_triple_sp_o(i, PYM.terminology.storid) == dest_storid:
        yield c.namespace.world._get_by_storid(i)
  return _from_cui_mapper
  
def _to_cui_mapper(c):
  for (i,) in PYM.world.graph.execute(
"""SELECT tu2.o FROM objs t INDEXED BY index_objs_sp, objs tu1 INDEXED BY index_objs_sp, objs tu2 INDEXED BY index_objs_sp
WHERE t.s=? AND t.p=?
AND tu1.s=t.o AND tu1.p=? AND tu1.o=?
AND tu2.s=t.o AND tu2.p=?
""", (
  c.storid, rdfs_subclassof,
  owl_onproperty, PYM.unifieds.storid,
  SOME,
  )):
    yield c.namespace.world._get_by_storid(i)
      
def _create_cui_mapper(source, dest):
  def _cui_mapper(c, dest_storid = dest.storid):
    found = False

    for (i,) in PYM.world.graph.execute(
"""SELECT DISTINCT tm2.o FROM objs t INDEXED BY index_objs_sp, objs tm1 INDEXED BY index_objs_sp, objs tm2 INDEXED BY index_objs_sp, objs tt INDEXED BY index_objs_sp
WHERE t.s=? AND t.p=?
AND tm1.s=t.o AND tm1.p=? AND tm1.o=?
AND tm2.s=t.o AND tm2.p=?
AND tt.s=tm2.o AND tt.p=? AND tt.o=?
""", (
  c.storid, rdfs_subclassof,
  owl_onproperty, PYM.mapped_to.storid,
  SOME,
  PYM.terminology.storid, dest_storid
  )):
      yield c.namespace.world._get_by_storid(i)
      found = True
    if found: return

    cuis = [i for (i,) in PYM.world.graph.execute(
"""SELECT tu2.o FROM objs t INDEXED BY index_objs_sp, objs tu1 INDEXED BY index_objs_sp, objs tu2 INDEXED BY index_objs_sp
WHERE t.s=? AND t.p=?
AND tu1.s=t.o AND tu1.p=? AND tu1.o=?
AND tu2.s=t.o AND tu2.p=?
""", (
  c.storid, rdfs_subclassof,
  owl_onproperty, PYM.unifieds.storid,
  SOME,
  ))]
    if cuis:
      already = set()
      for (i,) in PYM.world.graph.execute(
"""SELECT to3.o FROM objs to1 INDEXED BY index_objs_sp, objs to2 INDEXED BY index_objs_sp, objs to3 INDEXED BY index_objs_sp
WHERE to1.s IN (%s) AND to1.p=?
AND to2.s=to1.o AND to2.p=? AND to2.o=?
AND to3.s=to1.o AND to3.p=?
""" % (", ".join(str(cui) for cui in cuis)), (
  rdfs_subclassof,
  owl_onproperty, PYM.originals.storid,
  SOME,
  )):
        if i in already: continue
        if PYM.world._get_obj_triple_sp_o(i, PYM.terminology.storid) == dest_storid:
          already.add(i)
          yield c.namespace.world._get_by_storid(i)
          
      
## Single request but can be very slow!
#     for (i,) in PYM.world.graph.execute(
# """SELECT DISTINCT to3.o FROM objs t, objs tu1, objs tu2, objs to1, objs to2, objs to3
# WHERE t.s=? AND t.p=?
# AND tu1.s=t.o AND tu1.p=? AND unlikely(tu1.o=?)
# AND tu2.s=t.o AND tu2.p=?
# AND to1.s=tu2.o AND to1.p=?
# AND to2.s=to1.o AND to2.p=? AND unlikely(to2.o=?)
# AND to3.s=to1.o AND to3.p=?
# """, (
#   c.storid, rdfs_subclassof,
#   owl_onproperty, PYM.unifieds.storid,
#   SOME,
#   rdfs_subclassof,
#   owl_onproperty, PYM.originals.storid,
#   SOME,
#   )):
#       if PYM.world._get_obj_triple_sp_o(i, PYM.terminology.storid) == dest_storid:
#         yield c.namespace.world._get_by_storid(i)
  return _cui_mapper

def _create_icd10_french_atih_2_icd10_mapper(dest):
  def _icd10_french_atih_2_icd10_mapper(c):
    code = c.name
    r = dest[code]
    if r: yield r
    else:
      r = dest["%s.9" % code]
      if r: yield r
      elif code == "B95-B98": yield dest["B95-B97.9"]
      elif code == "G10-G14": yield dest["G10-G13.9"]
      elif code == "J09-J18": yield dest["J10-J18.9"]
      elif code == "K55-K64": yield dest["K55-K63.9"]
      elif code == "O94-O99": yield dest["O95-O99.9"]
  return _icd10_french_atih_2_icd10_mapper

def _create_icd10_2_icd10_french_atih_mapper(dest):
  def _icd10_2_icd10_french_atih_mapper(c):
    code = c.name
    r = dest[code]
    if r: yield r
    elif code.endswith(".9"):
      r = dest[code[:-2]]
      if r: yield r
      elif code == "B95-B97.9": yield dest["B95-B98"]
      elif code == "G10-G13.9": yield dest["G10-G14"]
      elif code == "J10-J18.9": yield dest["J09-J18"]
      elif code == "K55-K63.9": yield dest["K55-K64"]
      elif code == "O95-O99.9": yield dest["O94-O99"]
  return _icd10_2_icd10_french_atih_mapper


class MetaGroup(ThingClass):
  def __new__(MetaClass, name, superclasses, obj_dict):
    if superclasses == (Thing,): return ThingClass.__new__(MetaClass, name, superclasses, obj_dict)
    else:                        return type.__new__(MetaClass, name, superclasses, obj_dict)
    
  def __repr__(Class):
    return """<Group %s> # %s\n""" % (Class.name, " ; ".join("%s=%s" % (prop.label.first() or prop.name, ",".join(v.label.first() for v in prop[Class])) for prop in Class.get_class_properties()))
    
    
with PYM:
  class Concept(Thing, metaclass = MetaConcept):
    pass
  type.__setattr__(Concept, "__terminology", None)
  type.__setattr__(Concept, "__children", [])
  type.__setattr__(Concept, "__parents" , [])

  class Group(Thing, metaclass = MetaGroup):
    pass

#  class unifieds(ObjectProperty):
#    @classmethod
#    def is_functional_for(Prop, Class): return False
    
#  class originals(ObjectProperty):
#    @classmethod
#    def is_functional_for(Prop, Class): return False
      
_CUI = PYM["CUI"]

def Concepts(x): return set(x)


class Concepts(set):
  """A set of concepts. The set can contain each concept only once, and it
inherits from Python's :class:`set` the methods for computing intersection, union, difference, ..., of two sets.

.. automethod:: __rshift__
"""
  def __repr__   (self): return u"%s([\n  %s])" % (self.__class__.__name__, ", ".join([repr(t) for t in self]))
  
  def __rshift__(self, destination):
    """Maps the set of concepts to the destination_terminology. See :doc:`tuto_en` for more info."""
    #terminology_2_concepts = defaultdict(list)
    #for concept in self: terminology_2_concepts[concept.terminology].append(concept)
    #r = Concepts()
    #for terminology, concepts in terminology_2_concepts.items():
    #  r.update((terminology >> destination).map_concepts(concepts))
    #return r
    r = Concepts( j for i in self for j in i >>  destination)
    return r
  
  def find(self, parent_concept):
    """returns the first concept of the set that is a descendant of parent_concept (including parent_concept itself)."""
    for c in self:
      if issubclass(c, parent_concept): return c
      
  #def find_graphically(self, concept):
  #  for c in self:
  #    if hasattr(c, "is_graphically_a"):
  #      if c.is_graphically_a(concept): return c
  #    else:
  #      if c.is_a(concept): return c
  
  def imply(self, other):
    """returns true if all concepts in the OTHER set are descendants of (at least) one of the concepts in this set."""
    for cb in other:
      for ca in self:
        if issubclass(ca, cb): break
      else:
        return False
    return True
  
  def is_semantic_subset(self, other):
    """returns true if all concepts in this set are descendants of (at least) one of the concept in the OTHER set."""
    for c1 in self:
      for c2 in other:
        if issubclass(c1, c2): break
      else:
        return False
    return True
  
  def is_semantic_superset(self, other):
    """returns true if all concepts in this set are ancestors of (at least) one of the concept in the OTHER set."""
    for c1 in self:
      for c2 in other:
        if issubclass(c2, c1): break
      else:
        return False
    return True
  
  def is_semantic_disjoint(self, other):
    """returns true if all concepts in this set are semantically disjoint from all concepts in the OTHER set."""
    for c1 in self:
      for c2 in other:
        if issubclass(c1, c2) or issubclass(c2, c1): return False
    return True
  
  def semantic_intersection(self, other):
    r = Concepts()
    for c1 in self:
      for c2 in other:
        if   issubclass(c1, c2): r.add(c1)
        elif issubclass(c2, c1): r.add(c2)
    return r
  
  def keep_most_specific(self, more_specific_than = None):
    """keeps only the most specific concepts, i.e. remove all concepts that are more general that another concept in the set."""
    clone = self.copy()
    for t1 in clone:
      for t2 in more_specific_than or clone:
        if (not t1 is t2) and issubclass(t1, t2): # t2 is more generic than t1 => we keep t1
          self.discard(t2)
          
  def keep_most_generic(self, more_generic_than = None):
    """keeps only the most general concepts, i.e. remove all concepts that are more specific that another concept in the set."""
    clone  = self.copy()
    clone2 = (more_generic_than or self).copy()
    for t1 in clone:
      for t2 in clone2:
        if (not t1 is t2) and issubclass(t1, t2): # t2 is more generic than t1 => we keep t2
          self  .discard(t1)
          clone2.discard(t1)
          break
          
  def extract(self, parent_concept):
    """returns all concepts of the set that are descendant of parent_concept (including parent_concept itself)."""
    return Concepts([c for c in self if issubclass(c, parent_concept)])
  
  def subtract(self, parent_concept):
    """returns a new set after removing all concepts that are descendant of parent_concept (including parent_concept itself)."""
    return Concepts([c for c in self if not issubclass(c, parent_concept)])
    
  def subtract_update(self, parent_concept):
    """same as `func`:subtract, but modify the set *in place*."""
    for c in set(self):
      if issubclass(c, parent_concept): self.discard(c)
      
  def remove_entire_families(self, only_family_with_more_than_one_child = True):
    modified = 1
    while modified:
      modified = 0
      clone = self.copy()
      if only_family_with_more_than_one_child:
        parents = set([p for i in self for p in i.parents if len(p.children) > 1])
      else:
        parents = set([p for i in self for p in i.parents])
        
      while parents:
        t = parents.pop()
        children = set(t.children)
        if children.issubset(clone):
          modified = 1
          for i in self.copy():
            if issubclass(i, t): self.remove(i)
          for i in parents.copy():
            if issubclass(i, t): parents.remove(i)
          self.add(t)
  
          
  def lowest_common_ancestors(self):
    """returns the lowest common ancestors between this set of concepts."""
    if len(self) == 0: return None
    if len(self) == 1: return Concepts(self)
    
    ancestors = [set(concept.ancestor_concepts()) for concept in self]
    common_ancestors = Concepts(reduce(operator.and_, ancestors))
    r = Concepts()
    common_ancestors.keep_most_specific()
    return common_ancestors
  
  def all_subsets(self):
    """returns all the subsets included in this set."""
    l = [Concepts()]
    for concept in self:
      for concepts in l[:]:
        l.append(concepts | set([concept]))
    return l
  
  def __and__             (s1, s2): return s1.__class__(set.__and__(s1, s2))
  def __or__              (s1, s2): return s1.__class__(set.__or__(s1, s2))
  def __sub__             (s1, s2): return s1.__class__(set.__sub__(s1, s2))
  def __xor__             (s1, s2): return s1.__class__(set.__xor__(s1, s2))
  def difference          (s1, s2): return s1.__class__(set.difference(s1, s2))
  def intersection        (s1, s2): return s1.__class__(set.intersection(s1, s2))
  def symmetric_difference(s1, s2): return s1.__class__(set.symmetric_difference(s1, s2))
  def union               (s1, s2): return s1.__class__(set.union(s1, s2))
  def copy                (s1):     return s1.__class__(s1)

PYM.Concepts = Concepts
