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

import owlready2
from owlready2.base      import *
from owlready2.namespace import *



class _EquivalentToList(CallbackList):
  __slots__ = ["_indirect"]
  def __init__(self, l, obj, callback):
    CallbackList.__init__(self, l, obj, callback)
    self._obj      = obj
    self._indirect = None
    
  def transitive_symmetric(self):
    if self._indirect is None:
      n = self._obj.namespace
      self._indirect = set( n.ontology._to_python(o, main_type = self._obj.__class__)
                            for o in n.world._get_obj_triples_transitive_sym(self._obj.storid, self._obj._owl_equivalent)
                            if o != self._obj.storid )
      #self._indirect = set( n.ontology._to_python(o, main_type = self._obj.__class__)
      #                      for o in n.world.get_equivs_s_o(self._obj.storid)
      #                      if o != self._obj.storid )
      
    yield from self._indirect
    
  indirect = transitive_symmetric
  
  
class EntityClass(type):
  namespace = owlready
  
  def get_name(Class): return Class._name
  def set_name(Class, name):
    Class._name = name
    Class.namespace.world._refactor(Class.storid, "%s%s" % (Class.namespace.base_iri, name))
  name = property(get_name, set_name)
  
  def get_iri(Class): return "%s%s" % (Class.namespace.base_iri, Class._name)
  def set_iri(Class, new_iri):
    splitted = new_iri.rsplit("#", 1)
    if len(splitted) == 2:
      Class.namespace = Class.namespace.ontology.get_namespace("%s#" % splitted[0])
    else:
      splitted = new_iri.rsplit("/", 1)
      Class.namespace = Class.namespace.ontology.get_namespace("%s/" % splitted[0])
    Class._name = splitted[1]
    Class.namespace.world._refactor(Class.storid, new_iri)
  iri = property(get_iri, set_iri)
  
  
  _owl_type         = owl_class
  _rdfs_is_a        = rdfs_subclassof
  _owl_equivalent   = owl_equivalentclass
  _owl_disjointwith = owl_disjointwith
  _owl_alldisjoint  = owl_alldisjointclasses
  
  @staticmethod
  def _find_base_classes(is_a):
    bases = tuple(Class for Class in is_a if not isinstance(Class, ClassConstruct))
    if len(bases) > 1:
      # Must use sorted() and not sort(), because bases is accessed during the sort
      return tuple(sorted(bases, key = lambda Class: sum(issubclass_python(Other, Class) for Other in bases)))
    return bases
  
  def mro(Class):
    try: return type.mro(Class)
    except TypeError:
      mro = [Class]
      for base in Class.__bases__:
        for base_mro in base.__mro__:
          if base_mro in mro: mro.remove(base_mro)
          mro.append(base_mro)
      return mro
    
  def __new__(MetaClass, name, superclasses, obj_dict):
    namespace = obj_dict.get("namespace") or CURRENT_NAMESPACES[-1] or superclasses[0].namespace
    storid    = obj_dict.get("storid")    or namespace.world._abbreviate("%s%s" % (namespace.base_iri, name))
    
    if "is_a" in obj_dict:
      _is_a = [*superclasses, *obj_dict["is_a"]]
      superclasses = MetaClass._find_base_classes(_is_a) or (Thing,)
    else:
      if len(superclasses) > 1:
        _is_a = superclasses = MetaClass._find_base_classes(superclasses) or (Thing,)
      else:
        _is_a = superclasses
        
    if LOADING:
      Class = namespace.world._entities.get (storid)
    else:
      for base in _is_a:
        if isinstance(base, ClassConstruct): base._set_ontology(namespace.ontology)
      Class = namespace.world._get_by_storid(storid)
      
    equivalent_to = obj_dict.pop("equivalent_to", None)
      
    if Class is None:
      _is_a = CallbackList(_is_a, None, MetaClass._class_is_a_changed)
      obj_dict.update(
        _name          = name,
        namespace      = namespace,
        storid         = storid,
        is_a           = _is_a,
        _equivalent_to = None,
      )

      Class = namespace.world._entities[storid] = _is_a._obj = type.__new__(MetaClass, name, superclasses, obj_dict)
          
      if not LOADING:
        namespace.ontology._add_obj_triple_spo(storid, rdf_type, MetaClass._owl_type)
        for parent in _is_a: Class._add_is_a_triple(parent)
        
    else:
      if Class.is_a != _is_a: Class.is_a.extend([i for i in _is_a if not i in Class.is_a])
      
    if equivalent_to:
      if isinstance(equivalent_to, list): Class.equivalent_to.extend(equivalent_to)
      
    return Class
  
  def _add_is_a_triple(Class, base):
    Class.namespace.ontology._add_obj_triple_spo(Class.storid, Class._rdfs_is_a, base.storid)
    
  def _del_is_a_triple(Class, base):
    Class.namespace.ontology._del_obj_triple_spod(Class.storid, Class._rdfs_is_a, base.storid)
    
  def __init__(Class, name, bases, obj_dict):
    for k, v in obj_dict.items():
      if k in SPECIAL_ATTRS: continue
      Prop = Class.namespace.world._props.get(k)
      if Prop is None:
        type.__setattr__(Class, k, v)
      else:
        try: delattr(Class, k) # Remove the value initially stored by obj_dict in __new__
        except: pass
        setattr(Class, k, v)
        
  def get_equivalent_to(Class):
    if Class._equivalent_to is None:
      Class._equivalent_to = _EquivalentToList(
          [Class.namespace.world._to_python(o, main_type = Class.__class__, default_to_none = True)
           for o in Class.namespace.world._get_obj_triples_sp_o(Class.storid, Class._owl_equivalent)
          ], Class, Class.__class__._class_equivalent_to_changed)
    return Class._equivalent_to
  
  def set_equivalent_to(Class, value): Class.equivalent_to.reinit(value)
  
  equivalent_to = property(get_equivalent_to, set_equivalent_to)
  
  def _class_equivalent_to_changed(Class, old):
    for Subclass in Class.descendants(True, True):
      _FUNCTIONAL_FOR_CACHE.pop(Subclass, None)
      
    new = frozenset(Class._equivalent_to)
    old = frozenset(old)
    
    for x in old - new:
      Class.namespace.ontology._del_obj_triple_spod(Class.storid, Class._owl_equivalent, x    .storid)
      if isinstance(x, ClassConstruct): x._set_ontology(None)
      else: # Invalidate it
        if x.equivalent_to._indirect:
          for x2 in x.equivalent_to._indirect: x2._equivalent_to._indirect = None
          x._equivalent_to._indirect = None
      
    for x in new - old:
      if isinstance(x, ClassConstruct): x._set_ontology(Class.namespace.ontology)
      else: # Invalidate it
        if x.equivalent_to._indirect:
          for x2 in x.equivalent_to._indirect: x2._equivalent_to._indirect = None
          x._equivalent_to._indirect = None
      Class.namespace.ontology._add_obj_triple_spo(Class.storid, Class._owl_equivalent, x.storid)
      
    Class._equivalent_to._indirect = None # Invalidate, because the addition / removal may add its own equivalent.
    
  def __setattr__(Class, attr, value):
    if attr == "is_a":
      old = Class.is_a
      type.__setattr__(Class, "is_a", CallbackList(value, Class, Class.__class__._class_is_a_changed))
      Class._class_is_a_changed(old)
    type.__setattr__(Class, attr, value)
    
  def _class_is_a_changed(Class, old):
    for Subclass in Class.descendants(True, True):
      _FUNCTIONAL_FOR_CACHE.pop(Subclass, None)
      
    new = frozenset(Class.is_a)
    old = frozenset(old)
    for base in old - new:
      if not LOADING: Class._del_is_a_triple(base)
      if isinstance(base, ClassConstruct): base._set_ontology(None)
      
    bases = Class._find_base_classes(Class.is_a)
    if bases:
      Class.__bases__ = bases
    else:
      if   isinstance(Class, ThingClass):
        Class.__bases__ = (Thing,)
        list.insert(Class.is_a, 0, Thing)
      elif isinstance(Class, ObjectPropertyClass):
        Class.__bases__ = (ObjectProperty,)
        list.insert(Class.is_a, 0, ObjectProperty)
      else:
        Class.__bases__ = (DataProperty,)
        list.insert(Class.is_a, 0, DataProperty)
        
    for base in new - old:
      if isinstance(base, ClassConstruct): base._set_ontology(Class.namespace.ontology)
      if not LOADING: Class._add_is_a_triple(base)
      
  def disjoints(Class):
    for c, s, p, o in Class.namespace.world._get_obj_triples_cspo_cspo(None, None, rdf_type, Class._owl_alldisjoint):
      onto = Class.namespace.world.graph.context_2_user_context(c)
      list_bnode = Class.namespace.world._get_obj_triple_sp_o(s, owl_members)
      storids = set(storid for storid, dropit in onto._parse_list_as_rdf(list_bnode))
      if Class.storid in storids: yield onto._parse_bnode(s)
      
    for c, s, p, o in Class.namespace.world._get_obj_triples_cspo_cspo(None, Class.storid, Class._owl_disjointwith, None):
      with LOADING: a = AllDisjoint((s, p, o), Class.namespace.world.graph.context_2_user_context(c), None)
      yield a # Must yield outside the with statement
      
    for c, s, p, o in Class.namespace.world._get_obj_triples_cspo_cspo(None, None, Class._owl_disjointwith, Class.storid):
      with LOADING: a = AllDisjoint((s, p, o), Class.namespace.world.graph.context_2_user_context(c), None)
      yield a
    
  def ancestors(Class, include_self = True):
    s = set()
    Class._fill_ancestors(s, include_self)
    return s
  
  def descendants(Class, include_self = True, only_loaded = False, world = None):
    if Class is Thing:
      if world is None:
        import owlready2
        world = owlready2.default_world
      s = set(world.classes())
      if include_self: s.add(Thing)
    else:
      s = set()
      Class._fill_descendants(s, include_self, only_loaded)
    return s
  
  def _fill_ancestors(Class, s, include_self):
    if include_self:
      if not Class in s:
        s.add(Class)
        for equivalent in Class.equivalent_to.indirect():
          if isinstance(equivalent, EntityClass):
            if not equivalent in s: equivalent._fill_ancestors(s, True)
    for parent in Class.__bases__:
      if isinstance(parent, EntityClass):
        if not parent in s:
          parent._fill_ancestors(s, True)
          
  def _fill_descendants(Class, s, include_self, only_loaded = False):
    if include_self:
      s.add(Class)
      for equivalent in Class.equivalent_to.indirect():
        if isinstance(equivalent, Class.__class__) and not equivalent in s:
          equivalent._fill_descendants(s, True)
          
    for x in Class.namespace.world._get_obj_triples_transitive_po(Class._rdfs_is_a, Class.storid):
      if not x < 0:
        if only_loaded:
          descendant = Class.namespace.world._entities.get(x)
          if descendant is None: continue
        else:
          descendant = Class.namespace.world._get_by_storid(x, None, Class.__class__, Class.namespace.ontology)
        if (descendant is Class): continue
        if not descendant in s:
          s.add(descendant)
          for equivalent in descendant.equivalent_to.indirect():
            if isinstance(equivalent, Class.__class__) and not equivalent in s:
              equivalent._fill_descendants(s, True)
              
  def subclasses(Class, only_loaded = False, world = None):
    if Class is Thing:
      if world is None:
        import owlready2
        world = owlready2.default_world
      r = []
      for x in world._get_obj_triples_po_s(rdf_type, owl_class):
        if x < 0: continue
        for y in world._get_obj_triples_sp_o(x, Class._rdfs_is_a):
          if (y == owl_thing) or y < 0: continue
          break
        else:
          if only_loaded:
            subclass = world._entities.get(x)
            if not subclass is None: yield subclass # r.append(subclass)
          else:
            yield world._get_by_storid(x, None, ThingClass)
            #r.append(world._get_by_storid(x, None, ThingClass))
      return r
    
    else:
      if only_loaded:
        #r = []
        for x in Class.namespace.world._get_obj_triples_po_s(Class._rdfs_is_a, Class.storid):
          if not x < 0:
            subclass = Class.namespace.world._entities.get(x)
            if not subclass is None: yield subclass #r.append(subclass)
        #return r
      
      else:
        #return [
        #  Class.namespace.world._get_by_storid(x, None, ThingClass, Class.namespace.ontology)
        #  for x in Class.namespace.world._get_obj_triples_po_s(Class._rdfs_is_a, Class.storid)
        #  if not x < 0
        #]
        for x in Class.namespace.world._get_obj_triples_po_s(Class._rdfs_is_a, Class.storid):
          if not x < 0:
            yield Class.namespace.world._get_by_storid(x, None, ThingClass, Class.namespace.ontology)
      
  def constructs(Class, Prop = None):
    def _top_bn(s):
      try:
        construct = onto._parse_bnode(s)
        return construct
      except:
        for relation in [rdf_first, rdf_rest, owl_complementof, owl_unionof, owl_intersectionof, owl_onclass]:
          s2 = Class.namespace.world._get_obj_triple_po_s(relation, s)
          if not s2 is None:
            return _top_bn(s2)
          
    if Prop: Prop = Prop.storid
    for c,s,p,o in Class.namespace.world._get_obj_triples_cspo_cspo(None, None, Prop, Class.storid):
      if s < 0:
        
        onto = Class.namespace.world.graph.context_2_user_context(c)
        construct = _top_bn(s)
        if not construct is None:
          yield construct
          
def issubclass_owlready(Class, Parent_or_tuple):
  if issubclass_python(Class, Parent_or_tuple): return True
  if isinstance(Class, EntityClass):
    if not isinstance(Parent_or_tuple, tuple): Parent_or_tuple = (Parent_or_tuple,)
    parent_storids = { Parent.storid for Parent in Parent_or_tuple }
    
    Class_parents = set(Class.namespace.world._get_obj_triples_transitive_sp(Class.storid, Class._rdfs_is_a))
    Class_parents.add(Class.storid)
    if not parent_storids.isdisjoint(Class_parents): return True
    
    equivalent_storids = { Equivalent.storid for Parent in Parent_or_tuple for Equivalent in Parent.equivalent_to.indirect() }
    if not equivalent_storids.isdisjoint(Class_parents): return True
    
  return False

issubclass = issubclass_owlready

class ThingClass(EntityClass):
  namespace = owlready
  
  def __instancecheck__(Class, instance):
    if not hasattr(instance, "storid"): return False
    if Class is Thing: return super().__instancecheck__(instance)
    for C in instance.is_a:
      if isinstance(C, EntityClass) and issubclass(C, Class): return True
    return False
  
  def _satisfied_by(Class, x):
    return (isinstance(x, EntityClass) and issubclass(x, Class)) or isinstance(x, Class)
  
  def _get_class_possible_relations(Class):
    for Prop in Class.namespace.world._reasoning_props.values():
      for domain in Prop.domains_indirect():
        if not domain._satisfied_by(Class): break
      else:
        yield Prop
        
  def instances(Class, world = None):
    if Class.namespace is owl:
      import owlready2
      return (world or owlready2.default_world).world.search(type = Class)
    return Class.namespace.world.search(type = Class)
  
  def direct_instances(Class, world = None):
    if Class.namespace is owl:
      import owlready2
      world = world or owlready2.default_world
      return [world._get_by_storid(s, None, Thing) for s in world._get_obj_triples_po_s(rdf_type, Class.storid)]
    return [Class.namespace.world._get_by_storid(s, None, Thing) for s in Class.namespace.world._get_obj_triples_po_s(rdf_type, Class.storid)]
  
  def get_class_properties(Class):
    for construct in itertools.chain(Class.is_a, Class.equivalent_to.indirect()):
      if isinstance(construct, Restriction) and construct.type == SOME:
        yield construct.property
        
  def __and__(a, b): return And([a, b])
  def __or__ (a, b): return Or ([a, b])
  def __invert__(a): return Not(a)
  
  def __rshift__(Domain, Range):
    import owlready2.prop
    owlready2.prop._next_domain_range = (Domain, Range)
    if isinstance(Range, ThingClass) or isinstance(Range, ClassConstruct):
      return owlready2.prop.ObjectProperty
    else:
      return owlready2.prop.DataProperty
    
  def __getattr__(Class, attr):
    Prop = Class.namespace.world._props.get(attr)
    if Prop is None: raise AttributeError("'%s' property is not defined." % attr)
    return Class._get_class_prop_value(Prop, attr)
  
  def _get_class_prop_value(Class, Prop, attr, force_list = False):
    if issubclass_python(Prop, AnnotationProperty):
      # Do NOT cache as such in __dict__, to avoid inheriting annotations
      attr = "__%s" % attr
      values = Class.__dict__.get(attr)
      if values is None:
        values = ValueList((Class.namespace.ontology._to_python(o, d) for o,d in Class.namespace.world._get_triples_sp_od(Class.storid, Prop.storid)), Class, Prop)
        type.__setattr__(Class, attr, values)
      return values
    
    else:
      if (not force_list) and Prop.is_functional_for(Class):
        for r in _inherited_property_value_restrictions(Class, Prop, set()):
          if (r.type == VALUE) or (r.type == SOME): return r.value
        return None
      else:
        return RoleFilerList(
          set(r.value for SuperClass in itertools.chain(Class.is_a, Class.equivalent_to.indirect()) for r in _property_value_restrictions(SuperClass, Prop, set()) if (r.type == VALUE) or (r.type == SOME)),
          Class, Prop)
          
  def inverse_restrictions(Class, Prop = None):
    for construct in Class.constructs():
      if isinstance(construct, Restriction) and ((Prop is None) or (construct.property is Prop)):
        yield from construct.subclasses()
        
  # Role-fillers as class properties
  
  #def _get_prop_for_self(self, attr):
  #  Prop = Class.namespace.world._reasoning_props.get(attr)
  #  if Prop is None: raise AttributeError("'%s' property is not defined." % attr)
  #  for domain in Prop.domain:
  #    if not domain._satisfied_by(self): raise AttributeError("'%s' property has incompatible domain for %s." % (attr, self))
  #  return Prop
  
  def _on_class_prop_changed(Class, Prop, old, new):
    old     = set(old)
    new     = set(new)
    removed = old - new
    inverse = Prop.inverse_property
    
    if removed:
      for r in list(_inherited_property_value_restrictions(Class, Prop, set())):
        if (r.value in removed) and (r in Class.is_a):
          Class.is_a.remove(r)
          if r.type == VALUE:
            if isinstance(Prop, ObjectPropertyClass):
              for r2 in r.value.is_a:
                if isinstance(r2, Restriction) and ((r2.property is inverse) or (isinstance(r2.property, Inverse) and (r2.property.property is Prop))) and (r2.type == SOME) and (r2.value is Class):
                  r.value.is_a.remove(r2)
                  break
                
    for v in new - old:
      if isinstance(v, EntityClass) or isinstance(v, ClassConstruct):
        Class.is_a.append(Prop.some(v))
      else:
        Class.is_a.append(Prop.value(v))
        if isinstance(Prop, ObjectPropertyClass):
          v.is_a.append(Inverse(Prop).some(Class))
        
  def __setattr__(Class, attr, value):
    if attr in SPECIAL_ATTRS:
      super().__setattr__(attr, value)
      return
    
    Prop = Class.namespace.world._props.get(attr)
    
    if Prop is None:
      raise AttributeError("'%s' property is not defined." % attr)
    
    if Prop.is_functional_for(Class):
      for r in _inherited_property_value_restrictions(Class, Prop, set()):
        if (r.type == VALUE): old = [r.value]; break
      else: old = []
      if value is None: Class._on_class_prop_changed(Prop, old, [])
      else:             Class._on_class_prop_changed(Prop, old, [value])
    else:
      if issubclass_python(Prop, AnnotationProperty):
        if   value is None:               value = []
        elif not isinstance(value, list): value = [value]
      getattr(Class, attr).reinit(value)
      

class RoleFilerList(CallbackListWithLanguage):
  __slots__ = ["_Prop"]
  def __init__(self, l, obj, Prop):
    list.__init__(self, l)
    self._obj  = obj
    self._Prop = Prop
    
  def _callback(self, obj, old): self._obj._on_class_prop_changed(self._Prop, old, self)
  
  def indirect(self):
    for r in _inherited_property_value_restrictions(self._obj, self._Prop, set()):
      if (r.type == VALUE) or (r.type == SOME):
        yield r.value
        

def _property_value_restrictions(x, Prop, already):
  if   isinstance(x, Restriction):
    if (Prop is None) or (x.property is Prop): yield x
    
  elif isinstance(x, And):
    for x2 in x.Classes:
      yield from _property_value_restrictions(x2, Prop, already)
      


def _inherited_property_value_restrictions(x, Prop, already):
  if   isinstance(x, Restriction):
    if (Prop is None) or (x.property is Prop): yield x
    
  elif isinstance(x, EntityClass) or isinstance(x, Thing):
    for parent in itertools.chain(x.is_a, x.equivalent_to.indirect()):
      if not parent in already:
        already.add(parent)
        yield from _inherited_property_value_restrictions(parent, Prop, already)
        
  elif isinstance(x, And):
    for x2 in x.Classes:
      yield from _inherited_property_value_restrictions(x2, Prop, already)
      

