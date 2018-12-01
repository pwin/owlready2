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
from owlready2.prop      import *
from owlready2.prop      import _CLASS_PROPS

# import weakref
# _annot_axiom_cache = weakref.WeakValueDictionary()

# class _AnnotAxiom(object):
#   def __init__(self, source, property, target, target_d):
#     self.namespace = source.namespace.ontology
#     self.source    = source
#     self.property  = property
#     self.target    = target
#     self.target_d  = target_d
#     self.bnode     = self.search_bnode()
    
#   def search_bnode(self):
#     if self.target_d is None:
#       for bnode in self.namespace._get_obj_triples_po_s(rdf_type, owl_axiom):
#         for p, o in self._get_obj_triples_s_po(bnode):
#           if   (p == owl_annotatedsource)   and (o != self.source):   break
#           elif (p == owl_annotatedproperty) and (o != self.property): break
#           elif (p == owl_annotatedtarget)   and (o != self.target):   break
#       else:
#         return bnode
#     else:
#       for bnode in self.namespace._get_obj_triples_po_s(rdf_type, owl_axiom):
#         for p, o, d in self._get_triples_s_pod(bnode):
#           if   (p == owl_annotatedsource)   and (o != self.source):   break
#           elif (p == owl_annotatedproperty) and (o != self.property): break
#           elif (p == owl_annotatedtarget)   and (o != self.target):   break
#       else:
#         return bnode

class _AnnotList(CallbackListWithLanguage):
  __slots__ = ["_property", "_target", "_target_d", "_annot"]
  def __init__(self, l, source, property, target, target_d, annot):
    list.__init__(self, l)
    self._obj      = source
    self._property = property
    self._target   = target
    self._target_d = target_d
    self._annot    = annot
    
  def _callback(self, obj, old):
    old = set(old)
    new = set(self)
    
    # Add before, in order to avoid destroying the axiom and then recreating, if all annotations are modified
    for added in new - old:
      x = obj.namespace.ontology._add_annotation_axiom(obj.storid, self._property, self._target, self._target_d, self._annot, *obj.namespace.ontology._to_rdf(added))
      
    for removed in old - new:
      obj.namespace.ontology._del_annotation_axiom    (obj.storid, self._property, self._target, self._target_d, self._annot, *obj.namespace.ontology._to_rdf(removed))
    
    
class AnnotationPropertyClass(PropertyClass):
  _owl_type = owl_annotation_property
  inverse_property = inverse = None
  
  def __getitem__(Annot, index):
    if isinstance(index, tuple):
      source, property, target = index
      if hasattr(source,   "storid"):
        world = source.namespace.world # if Annot is in owl_world (e.g. comment), use the world of the source
        source_orig = source
        source      = source.storid
      else:
        world = self.namespace.world
      if hasattr(property, "storid"): property = property.storid
      target, target_d = world._to_rdf(target)
      l = []
      for bnode in world._get_annotation_axioms(source, property, target, target_d):
        for o, d in world._get_triples_sp_od(bnode, Annot.storid):
          l.append(world._to_python(o, d))
          
      return _AnnotList(l, source_orig, property, target, target_d, Annot.storid)
    
    else:
      return getattr(index, Annot.python_name)
    
  def __setitem__(Annot, index, values):
    if not isinstance(values, list): values = [values]
    
    if isinstance(index, tuple): Annot[index].reinit(values)
    else: return setattr(index, Annot.python_name, values)
    
  def __call__(Prop, type, c, *args):
    raise ValueError("Cannot create a property value restriction on an annotation property!")
  
#type.__setattr__(DataProperty, "inverse_property", None)

class AnnotationProperty(Property, metaclass = AnnotationPropertyClass):
  @classmethod
  def is_functional_for(Prop, o): return False


_CLASS_PROPS.add(AnnotationProperty)

  
class comment               (AnnotationProperty): namespace = rdfs
class label                 (AnnotationProperty): namespace = rdfs
class backwardCompatibleWith(AnnotationProperty): namespace = owl
class deprecated            (AnnotationProperty): namespace = owl
class incompatibleWith      (AnnotationProperty): namespace = owl
class isDefinedBy           (AnnotationProperty): namespace = rdfs
class priorVersion          (AnnotationProperty): namespace = owl
class seeAlso               (AnnotationProperty): namespace = rdfs
class versionInfo           (AnnotationProperty): namespace = owl

