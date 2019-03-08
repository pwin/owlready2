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

from collections import defaultdict
from functools import reduce

import editobj3, editobj3.introsp as introsp, editobj3.field as field, editobj3.editor as editor

from owlready2 import *
from owlready2.base     import _universal_datatype_2_abbrev
from owlready2.prop     import _CLASS_PROPS, _TYPE_PROPS


IGNORE_DOMAINLESS_PROPERTY = False

introsp.def_attr("topObjectProperty", field.HiddenField)

def _keep_most_generic(s):
  r = set()
  for i in s:
    for parent in i.is_a:
      if parent in s: break
    else: r.add(i)
  return r

#def _available_ontologies(o):
#  return sorted(o.ontology.indirectly_imported_ontologies(), key = lambda x: x.name)

def _available_classes():
  #r = set()
  #for ontology in o.ontology.indirectly_imported_ontologies():
  #  r.update(ontology.classes)
  r = default_world.search(subclass_of = Thing)
  return sorted(_keep_most_generic(r), key = lambda x: str(x))

#def _available_properties(o):
#  r = set()
#  for ontology in o.ontology.indirectly_imported_ontologies():
#    r.update(ontology.properties)
#  return sorted(_keep_most_generic(r), key = lambda x: str(x))

#def _available_properties_and_types(o):
#  return [FunctionalProperty, InverseFunctionalProperty, TransitiveProperty, SymmetricProperty, AsymmetricProperty, ReflexiveProperty, IrreflexiveProperty] + _available_properties(o)

#def _available_classes_and_datatypes(o):
#  r = set()
#  for ontology in o.ontology.indirectly_imported_ontologies():
#    r.update(ontology.classes)
#  r = _keep_most_generic(r)
#  r.update(owlready._PYTHON_2_DATATYPES.keys())
#  return sorted(r, key = lambda x: str(x))

def _get_label(o): return str(o).replace("_", " ")

#descr = introsp.description(EntityClass)
#descr.def_attr("ontology"   , field.HiddenField)

#descr = introsp.description_for_type(Thing)
##descr.def_attr("ontology"     , field.ObjectSelectorField, addable_values = _available_ontologies)
#descr.def_attr("namespace"    , field.HiddenField)
#descr.def_attr("name"         , field.StringField)
#descr.def_attr("python_name"  , field.StringField)
#descr.def_attr("is_a"         , field.HierarchyAndObjectListField, addable_values = _available_classes)
#descr.def_attr("equivalent_to", field.HierarchyAndObjectListField, addable_values = _available_classes)
#descr.set_label(_get_label)
#descr.set_icon_filename(os.path.join(os.path.dirname(__file__), "icons", "owl_class.svg"))

#descr = introsp.description_for_type(Property)
##descr.def_attr("ontology"        , field.ObjectSelectorField, addable_values = _available_ontologies)
#descr.def_attr("namespace"    , field.HiddenField)
#descr.def_attr("name"            , field.StringField)
#descr.def_attr("python_name"     , field.StringField)
#descr.def_attr("is_a"            , field.HierarchyAndObjectListField, addable_values = _available_properties_and_types)
#descr.def_attr("domain"          , field.HierarchyAndObjectListField, addable_values = _available_classes              , reorder_method = None)
#descr.def_attr("range"           , field.HierarchyAndObjectListField, addable_values = _available_classes_and_datatypes, reorder_method = None)
#descr.def_attr("inverse_property", field.ObjectSelectorField        , addable_values = lambda o: [None] + _available_properties(o))
#descr.def_attr("equivalent_to"   , field.HierarchyAndObjectListField, addable_values = _available_properties_and_types)
#descr.set_label(_get_label)
#descr.set_icon_filename(os.path.join(os.path.dirname(__file__), "icons", "owl_property.svg"))

descr = introsp.description(Thing)
descr.def_attr("iri"               , field.StringField)
descr.def_attr("namespace"         , field.HiddenField)
descr.def_attr("is_a"              , field.HiddenField)
descr.def_attr("is_instance_of"    , field.HiddenField)
descr.def_attr("name"              , field.HiddenField)
descr.def_attr("storid"            , field.HiddenField)
descr.def_attr("equivalent_to"     , field.HiddenField)
descr.def_attr("properties"        , field.HiddenField)
descr.def_attr("inverse_properties", field.HiddenField)
descr.set_label(_get_label)
descr.set_icon_filename(os.path.join(os.path.dirname(__file__), "icons", "owl_instance.svg"))
descr.set_constructor(introsp.Constructor(lambda Class, parent: Class(namespace = parent.namespace)))


introsp.MAX_NUMBER_OF_ATTRIBUTE_FOR_EMBEDDING = 0

def _get_priority(Prop):
  return Prop.editobj_priority.first()

def _intersect_reduce(s):
  if not s: return set()
  if len(s) == 1: return s[0]
  return reduce(set.intersection, s)

def _flattened_or(Classes):
  if Classes: yield from _flattened_or_iteration(Classes)
  else:       yield Thing

def _flattened_or_iteration(Classes):
  for Class in Classes:
    if   isinstance(Class, ThingClass): yield Class
    elif isinstance(Class, Or): yield from _flattened_or_iteration(Class.Classes)
    
def _get_class_one_of(Class):
  if isinstance(Class, OneOf): return Class.instances
  if isinstance(Class, ThingClass):
    s = []
    for ancestor in Class.ancestors():
      for superclass in ancestor.is_a + ancestor.equivalent_to:
        if isinstance(superclass, OneOf): s.append(superclass.instances)
    return _intersect_reduce(s)
  
def _prop_use_children_group(Prop, domain):
  for superprop in Prop.mro():
    if (superprop in _CLASS_PROPS) or (superprop in _TYPE_PROPS): continue
    if isinstance(superprop, PropertyClass) and not superprop.is_functional_for(domain): return True
  for range in _flattened_or(Prop.range):
    if isinstance(range, ThingClass) and _has_object_property(range): return True
  return False

def _has_object_property(Class):
  for Prop in Class._get_class_possible_relations():
    if not isinstance(Prop, DataPropertyClass): return True
  return False

def _is_abstract_class(Class):
  for superclass in Class.is_a + list(Class.equivalent_to.indirect()):
    if isinstance(superclass, Or):
      for or_class in superclass.Classes:
        if not isinstance(or_class, ThingClass): break
      else: return True

def configure_editobj_from_ontology(onto):
  introsp._init_for_owlready2()
  
  for Prop in onto.properties():
    if len(Prop.range) != 1: continue
    if isinstance(Prop, DataPropertyClass): ranges = [Prop.range[0]]
    else:                                   ranges = list(_flattened_or(Prop.range))
    if not ranges: continue
    
    priority = _get_priority(Prop)
    for domain in _flattened_or(Prop.domain):
      if isinstance(domain, ThingClass):
        if len(ranges) == 1: one_of = _get_class_one_of(ranges[0])
        else:                one_of = None
        if one_of: RangeInstanceOnly(Prop, domain, one_of)
        else:      RangeClassOnly   (Prop, domain, ranges)
        
  for Class in onto.classes():
    for superclass in Class.is_a:                     _configure_class_restriction(Class, superclass)
    for superclass in Class.equivalent_to.indirect(): _configure_class_restriction(Class, superclass)

  for prop_children_group in PROP_CHILDREN_GROUPS.values():
    if prop_children_group.changed: prop_children_group.define_children_groups()
  
    
def _configure_class_restriction(Class, restriction):
  if   isinstance(restriction, And):
    for sub_restriction in restriction.Classes:
      _configure_class_restriction(Class, sub_restriction)
      
  elif isinstance(restriction, Restriction):
    if   restriction.type == "VALUE":
      introsp.description(Class).def_attr(restriction.Prop.python_name, field.LabelField, priority = _get_priority(restriction.Prop))
      
    elif restriction.type == "ONLY":
      if isinstance(restriction.Prop, ObjectPropertyClass):
        if   isinstance(restriction.Class, ThingClass):
          ranges = [restriction.Class]
        elif isinstance(restriction.Class, LogicalClassConstruct):
          ranges = list(_flattened_or(restriction.Class.Classes))
        else: return
        if len(ranges) == 1: one_of = _get_class_one_of(ranges[0])
        else:                one_of = None
        if one_of: RangeInstanceOnly(restriction.Prop, Class, one_of)
        else:      RangeClassOnly   (restriction.Prop, Class, ranges)
        
    elif (restriction.type == "EXACTLY") or (restriction.type == "MAX"):
      # These restrictions can make the Property functional for the given Class
      # => Force the redefinition of the field type by creating an empty range restriction list
      if restriction.cardinality == 1:
        for subprop in restriction.Prop.descendants(include_self = False):
          prop_children_group = get_prop_children_group(subprop)
          prop_children_group.range_restrictions[Class] # Create the list if not already existent
          prop_children_group.changed = True
          
  elif isinstance(restriction, Not):
    for sub_restriction in _flattened_or([restriction.Class]):
      if isinstance(sub_restriction, Restriction):
        if sub_restriction.type == SOME and isinstance(sub_restriction.Prop, ObjectPropertyClass):
          ranges = list(_flattened_or([sub_restriction.Class]))
          if len(ranges) == 1: one_of = _get_class_one_of(ranges[0])
          else:                one_of = None
          if one_of: RangeInstanceExclusion(sub_restriction.Prop, Class, one_of)
          else:      RangeClassExclusion   (sub_restriction.Prop, Class, ranges)
          
          
PROP_CHILDREN_GROUPS = {}
def get_prop_children_group(Prop): return PROP_CHILDREN_GROUPS.get(Prop) or PropChildrenGroup(Prop)


class PropChildrenGroup(object):
  def __init__(self, Prop):
    self.Prop = Prop
    self.range_restrictions = defaultdict(list)
    self.changed = False
    PROP_CHILDREN_GROUPS[Prop] = self
    
  def define_children_groups(self):
    self.changed = False
    
    priority = _get_priority(self.Prop)
    
    for domain in set(self.range_restrictions):
      descr              = introsp.description(domain)
      functional         = self.Prop.is_functional_for(domain)
      range_restrictions = set()
      for superclass in domain.mro():
        s = self.range_restrictions.get(superclass)
        if s: range_restrictions.update(s)
        
      range_instance_onlys = { range_restriction for range_restriction in range_restrictions if isinstance(range_restriction, RangeInstanceOnly) }
      
      if range_instance_onlys:
        instances = _intersect_reduce([i.ranges for i in range_instance_onlys])
        d         = { instance.name : instance for instance in instances }
        if functional:
          d["None"] = None
          descr.def_attr(self.Prop.python_name, field.EnumField(d), priority = priority, optional = False)
        else:
          descr.def_attr(self.Prop.python_name, field.EnumListField(d), priority = priority, optional = False)
          
      else:
        if isinstance(self.Prop, DataPropertyClass):
          datatype = None
          for range_restriction in range_restrictions:
            if isinstance(range_restriction, RangeClassOnly):
              for range in range_restriction.ranges:
                if range in _universal_datatype_2_abbrev:
                  datatype = range
                  break
          
          if datatype:
            if   datatype is int:
              if functional: descr.def_attr(self.Prop.python_name, field.IntField       , allow_none = True, optional = False, priority = priority)
              else:          descr.def_attr(self.Prop.python_name, field.IntListField   , optional = False, priority = priority)
            elif datatype is float:
              if functional: descr.def_attr(self.Prop.python_name, field.FloatField     , allow_none = True, optional = False, priority = priority)
              else:          descr.def_attr(self.Prop.python_name, field.FloatListField , optional = False, priority = priority)
            elif datatype is normstr:
              if functional: descr.def_attr(self.Prop.python_name, field.StringField    , allow_none = True, optional = False, priority = priority)
              else:          descr.def_attr(self.Prop.python_name, field.StringListField, optional = False, priority = priority)
            elif datatype is str:
              if functional: descr.def_attr(self.Prop.python_name, field.TextField      , allow_none = True, optional = False, priority = priority)
              else:          descr.def_attr(self.Prop.python_name, field.StringListField, optional = False, priority = priority)
            elif datatype is bool:
              if functional: descr.def_attr(self.Prop.python_name, field.BoolField      , optional = False, priority = priority)
            else:
              if functional: descr.def_attr(self.Prop.python_name, field.EntryField     , allow_none = True, optional = False, priority = priority)
              else:          descr.def_attr(self.Prop.python_name, field.EntryListField , optional = False, priority = priority)
              
        else:
          values_lister = ValuesLister(self.Prop, domain, range_restrictions)
          if _prop_use_children_group(self.Prop, domain) or values_lister.values_have_children():
            if self.Prop.inverse: inverse_attr = self.Prop.inverse.python_name
            else:                 inverse_attr = ""
            if functional:        field_class  = field.HierarchyOrObjectSelectorField
            else:                 field_class  = field.HierarchyOrObjectListField
            
            descr.def_attr(self.Prop.python_name,
                           field_class,
                           addable_values = values_lister.available_values,
                           inverse_attr = inverse_attr,
                           priority = priority)
          else:
            descr.def_attr(self.Prop.python_name,
                           field.ObjectSelectorField,
                           addable_values = values_lister.available_values,
                           priority = priority)
          
class RangeRestriction(object):
  def __init__(self, Prop, domain, ranges):
    self.domain = domain
    self.ranges = ranges
    
    for subprop in Prop.descendants(include_self = True):
      prop_children_group = get_prop_children_group(subprop)
      prop_children_group.range_restrictions[domain].append(self)
      prop_children_group.changed = True
      
  def __repr__(self): return "<%s %s %s>" % (self.__class__.__name__, self.domain, self.ranges)
  
  def get_classes(self):
    available_classes = set()
    for range in self.ranges:
      for subrange in range.descendants(): available_classes.add(subrange)
    return available_classes
  
class RangeClassOnly        (RangeRestriction): pass
class RangeClassExclusion   (RangeRestriction): pass
class RangeInstanceOnly     (RangeRestriction): pass
class RangeInstanceExclusion(RangeRestriction): pass

VALUES_LISTERS = {}

class ValuesLister(object):
  def __init__(self, Prop, domain, range_restrictions):
    self.Prop               = Prop
    self.domain             = domain
    self.range_restrictions = range_restrictions
    VALUES_LISTERS[Prop, domain] = self
    
  def values_have_children(self):
    for range_restriction in self.range_restrictions:
      if isinstance(range_restriction, RangeClassOnly):
        for range in range_restriction.ranges:
          for subrange in range.descendants():
            for attribute in introsp.description(subrange).attributes.values():
              try:    return issubclass(attribute.field_class, FieldInHierarchyPane)
              except: return False # attribute.field_class if a func and not a class
              
  def available_values(self, subject):
    available_classes = []
    excluded_classes  = set()
    for range_restriction in self.range_restrictions:
      if   isinstance(range_restriction, RangeClassOnly):
        available_classes.append(range_restriction.get_classes())
      elif isinstance(range_restriction, RangeClassExclusion):
        excluded_classes.update(range_restriction.get_classes())
        
    available_classes = _intersect_reduce(available_classes)
    available_classes.difference_update(excluded_classes)
    available_classes = sorted(available_classes, key = lambda Class: Class.name)
    
    new_instances_of = [introsp.NewInstanceOf(Class) for Class in available_classes if (not _get_class_one_of(Class)) and (not _is_abstract_class(Class))]
    existent_values  = set()
    for Class in available_classes:
      existent_values.update(default_world.search(type = Class))
    if excluded_classes:
      excluded_classes = tuple(excluded_classes)
      existent_values = [o for o in existent_values if not isinstance(o, excluded_classes)]
      
    # For InverseFunctional props, remove values already used.
    if issubclass(self.Prop, InverseFunctionalProperty) and self.Prop.inverse_property:
      existent_values = { value for value in existent_values
                          if not getattr(value, self.Prop.inverse_property.python_name) }
    existent_values = sorted(existent_values, key = lambda obj: obj.name)
    
    return new_instances_of + existent_values
  
  def range_match_classes(self, classes):
    classes = tuple(classes)
    for range_restriction in self.range_restrictions:
      if isinstance(range_restriction, RangeClassOnly):
        for range in range_restriction.ranges:
          if issubclass(range, classes): return True
          
