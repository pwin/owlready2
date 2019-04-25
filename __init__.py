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

VERSION = "0.16"

JAVA_EXE = "java"

from owlready2.base            import *
#_render_func = default_render_func

from owlready2.namespace       import *
from owlready2.entity          import *
from owlready2.prop            import *
from owlready2.prop            import _FUNCTIONAL_FOR_CACHE
from owlready2.individual      import *
from owlready2.class_construct import *
from owlready2.disjoint        import *
from owlready2.annotation      import *
from owlready2.reasoning       import *
from owlready2.reasoning       import _keep_most_specific
from owlready2.close           import *

import owlready2.namespace, owlready2.entity, owlready2.prop, owlready2.class_construct, owlready2.triplelite
owlready2.triplelite.Or                     = Or
owlready2.namespace.EntityClass             = EntityClass
owlready2.namespace.ThingClass              = ThingClass
owlready2.namespace.PropertyClass           = PropertyClass
owlready2.namespace.AnnotationPropertyClass = AnnotationPropertyClass
owlready2.namespace.ObjectPropertyClass     = ObjectPropertyClass
owlready2.namespace.DataPropertyClass       = DataPropertyClass
owlready2.namespace.ObjectProperty          = ObjectProperty
owlready2.namespace.DataProperty            = DataProperty
owlready2.namespace.AnnotationProperty      = AnnotationProperty
owlready2.namespace.Thing                   = Thing
owlready2.namespace.Property                = Property
owlready2.namespace.Or                      = Or
owlready2.namespace.And                     = And
owlready2.namespace.Not                     = Not
owlready2.namespace.Restriction             = Restriction
owlready2.namespace.OneOf                   = OneOf
owlready2.namespace.FusionClass             = FusionClass
owlready2.namespace.AllDisjoint             = AllDisjoint
owlready2.namespace.ConstrainedDatatype     = ConstrainedDatatype
owlready2.namespace.Inverse                 = Inverse
owlready2.namespace.IndividualValueList     = IndividualValueList
owlready2.entity.Thing              = Thing
owlready2.entity.Nothing            = Nothing
owlready2.entity.ClassConstruct     = ClassConstruct
owlready2.entity.And                = And
owlready2.entity.Or                 = Or
owlready2.entity.Not                = Not
owlready2.entity.OneOf              = OneOf
owlready2.entity.Restriction        = Restriction
owlready2.entity.ObjectPropertyClass= ObjectPropertyClass
owlready2.entity.ObjectProperty     = ObjectProperty
owlready2.entity.DataProperty       = DataProperty
owlready2.entity.AnnotationProperty = AnnotationProperty
owlready2.entity.ReasoningPropertyClass = ReasoningPropertyClass
owlready2.entity.FunctionalProperty = FunctionalProperty
#owlready2.entity.ValueList          = ValueList
owlready2.entity.AllDisjoint        = AllDisjoint
owlready2.entity.Inverse            = Inverse
owlready2.entity._FUNCTIONAL_FOR_CACHE = _FUNCTIONAL_FOR_CACHE
owlready2.entity._property_value_restrictions = owlready2.prop._property_value_restrictions
owlready2.entity._inherited_properties_value_restrictions = owlready2.prop._inherited_properties_value_restrictions
owlready2.disjoint.Or = Or
owlready2.prop.Restriction             = Restriction
owlready2.prop.ConstrainedDatatype     = ConstrainedDatatype
owlready2.prop.ClassConstruct          = ClassConstruct
owlready2.prop.AnnotationProperty      = AnnotationProperty
owlready2.prop.Thing                   = Thing
#owlready2.prop.ValueList               = ValueList
owlready2.prop._check_superclasses     = True

owlready2.prop.ThingClass              = ThingClass
owlready2.prop.And                     = And
owlready2.prop.Or                      = Or
owlready2.prop.OneOf                   = OneOf
owlready2.annotation.ClassConstruct    = ClassConstruct

owlready2.individual._keep_most_specific = _keep_most_specific
owlready2.individual.ClassConstruct      = ClassConstruct
owlready2.individual.TransitiveProperty  = TransitiveProperty
owlready2.individual.SymmetricProperty   = SymmetricProperty
owlready2.individual.ReflexiveProperty   = ReflexiveProperty
owlready2.individual.AnnotationPropertyClass = AnnotationPropertyClass
owlready2.class_construct.Thing       = Thing
owlready2.class_construct.ThingClass  = ThingClass
owlready2.class_construct.EntityClass = EntityClass
del owlready2


LOADING.__exit__()

# Not real property
del owl_world._props["Property"]
del owl_world._props["ObjectProperty"]
del owl_world._props["DatatypeProperty"]
del owl_world._props["FunctionalProperty"]
del owl_world._props["InverseFunctionalProperty"]
del owl_world._props["TransitiveProperty"]
del owl_world._props["SymmetricProperty"]
del owl_world._props["AsymmetricProperty"]
del owl_world._props["ReflexiveProperty"]
del owl_world._props["IrreflexiveProperty"]
del owl_world._props["AnnotationProperty"]

default_world = IRIS = World()
get_ontology  = default_world.get_ontology
get_namespace = default_world.get_namespace


def default_render_func(entity):
  if isinstance(entity.storid, int) and (entity.storid < 0): return "_:%s" % (-entity.storid)
  return "%s.%s" % (entity.namespace.name, entity.name)

def set_render_func(func):
  type.__setattr__(EntityClass, "__repr__", func)
  type.__setattr__(Thing      , "__repr__", func)
  
set_render_func(default_render_func)
