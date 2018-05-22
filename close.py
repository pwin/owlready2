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

from owlready2.namespace       import *
from owlready2.entity          import *
from owlready2.entity          import _inherited_property_value_restrictions
from owlready2.prop            import *
from owlready2.individual      import *
from owlready2.class_construct import *


def close_world(self, Properties = None, close_instance_list = True, recursive = True):
  if isinstance(self, Thing): # An instance
    if Properties is None:
      Properties2 = (Prop for Prop in self._get_instance_possible_relations() if issubclass_python(Prop, ObjectProperty))
    else:
      Properties2 = Properties
    
    for Prop in Properties2:
      range_instances = list(Prop[self])
      range_classes   = []
      for r in _inherited_property_value_restrictions(self, Prop, set()):
        if   (r.type == SOME):  range_classes  .append(r.value)
        elif (r.type == VALUE): range_instances.append(r.value)
      if range_instances: range_classes.append(OneOf(range_instances))
      
      if not range_classes:                      self.is_a.append(Prop.only(Nothing))
      elif issubclass_python(Prop, FunctionalProperty): pass
      elif len(range_classes) == 1:              self.is_a.append(Prop.only(range_classes[0]))
      else:                                      self.is_a.append(Prop.only(Or(range_classes)))
      
  elif isinstance(self, ThingClass): # A class
    instances  = set(self.instances())
    subclasses = set(self.descendants())
    
    if close_instance_list:
      if instances: self.is_a.append(OneOf(list(instances)))
      
    if Properties is None:
      Properties2 = (Prop for Prop in self._get_class_possible_relations() if issubclass_python(Prop, ObjectProperty))
    else:
      Properties2 = Properties
      
    for Prop in Properties2:
      range_instances = []
      range_classes   = []
      for subclass in subclasses: # subclasses includes self
        for r in _inherited_property_value_restrictions(subclass, Prop, set()):
          if   r.type == VALUE:
            range_instances.append(r.value)
          elif (r.type == SOME) or ((r.type == EXACTLY) and r.cardinality >= 1) or ((r.type == MIN) and r.cardinality >= 1):
            if isinstance(r.value, OneOf): range_instances.extend(r.value.instances)
            else: range_classes.append(r.value)
            
      for instance in instances:
        range_instances.extend(Prop[instance])
        for r in _inherited_property_value_restrictions(instance, Prop, set()):
          if   (r.type == SOME):  range_classes  .append(r.value)
          elif (r.type == VALUE): range_instances.append(r.value)
      
      if range_instances: range_classes.append(OneOf(range_instances))
      if   len(range_classes) == 1: self.is_a.append(Prop.only(range_classes[0]))
      elif range_classes:           self.is_a.append(Prop.only(Or(range_classes)))
      else:                         self.is_a.append(Prop.only(Nothing))
      
    if recursive:
      subclasses.discard(self)
      for subclass in subclasses: close_world(subclass, Properties, close_instance_list, False)
      for instance in instances:  close_world(instance, Properties, close_instance_list, False)
      
      
  elif isinstance(self, Ontology):
    for individual in self.individuals():
      close_world(individual, Properties, close_instance_list, recursive)
      
    for Class in self.classes():
      close_world(Class, Properties, close_instance_list, recursive)
      
