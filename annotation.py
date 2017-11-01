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

from owlready2.namespace import *
from owlready2.prop      import *
from owlready2.prop      import _CLASS_PROPS


class AnnotList(CallbackListWithLanguage):
  __slots__ = ["_property", "_target", "_annot"]
  def __init__(self, l, source, property, target, annot):
    list.__init__(self, l)
    self._obj      = source
    self._property = property
    self._target   = target
    self._annot    = annot
    
  def _callback(self, obj, old):
    old = set(old)
    new = set(self)
    
    if not new:
      obj.namespace.ontology.del_annotation_axiom(obj.storid, self._property, self._target)
      return
    
    # Add before, in order to avoid destroying the axiom and then recreating, if all annotations are modified
    for added in new - old:
      obj.namespace.ontology.add_annotation_axiom(obj.storid, self._property, self._target, self._annot, obj.namespace.ontology._to_rdf(added))
      
    for removed in old - new:
      obj.namespace.ontology.del_annotation_axiom(obj.storid, self._property, self._target, self._annot, obj.namespace.ontology._to_rdf(removed))
    
    
class AnnotationPropertyClass(PropertyClass):
  _owl_type = owl_annotation_property
  inverse_property = inverse = None
  
  def __getitem__(Annot, index):
    if isinstance(index, tuple):
      source, property, target = index
      world = source.namespace.world # if Annot is in owl_world (e.g. comment), use the world of the source
      if hasattr(source,   "storid"):
        source_orig = source
        source      = source.storid
      if hasattr(property, "storid"): property = property.storid
      target = world._to_rdf(target)
      l = []
      for bnode in world.get_annotation_axioms(source, property, target):
        for o in world.get_triples_sp(bnode, Annot.storid):
          l.append(world._to_python(o))
      return AnnotList(l, source_orig, property, target, Annot.storid)
    
    else:
      return getattr(index, Annot.python_name)
    
  def __setitem__(Annot, index, values):
    if not isinstance(values, list): values = [values]
    if isinstance(index, tuple):
      source, property, target = index; lang = None
      ontology = source.namespace.ontology # if Annot is in owl_world (e.g. comment), use the world of the source
      source   = source.storid
      if hasattr(property, "storid"): property = property.storid
      target = ontology._to_rdf(target)
      values = [ontology._to_rdf(value) for value in values]
      ontology.set_annotation_axiom(source, property, target, Annot.storid, values)
      
    else:
      return setattr(index, Annot.python_name, values)
    
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

