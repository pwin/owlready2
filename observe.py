# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2007-2019 Jean-Baptiste LAMY
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

__all__ = ["start_observing", "stop_observing", "observe", "unobserve", "isobserved", "send_event", "scan_collapsed_changes",
           "InstancesOfClass"]

import weakref

from owlready2.base import rdf_type, rdfs_subclassof, owl_equivalentclass, owl_equivalentproperty, owl_equivalentindividual
from owlready2.namespace import Ontology
from owlready2 import Thing, ThingClass

class ObservedOntology(Ontology):
  def _get_pred_value_obj(self, subject, predicate):
    if   predicate == rdf_type:
      return list(filter(None, [self._to_python(o, default_to_none = True) for o in self._get_obj_triples_sp_o(subject, predicate)]))
    else:
      return [self._to_python(o) for o in self._get_obj_triples_sp_o(subject, predicate)]
    
  def _get_pred_value_data(self, subject, predicate):
    return [self._to_python(o, d) for o, d in self._get_data_triples_sp_od(subject, predicate)]
  
  def _gen_triple_method_obj(self, triple_method):
    def f(subject, predicate, object):
      observation = self.world._observations.get(subject)
      
      #if (predicate == rdf_type) and _INSTANCES_OF_CLASS:
      #  Class = self.world._get_by_storid(object)
      #  l_2_old_instances = {}
      #  if not Class is None: # Else it is Thing
      #    for parent in Class.ancestors():
      #      for l in _INSTANCES_OF_CLASS.get(parent.storid, ()):
      #        l_2_old_instances[l] = l._get_old_value()
              
      if observation:
        #old = self._get_pred_value_obj(subject, predicate)
        triple_method(subject, predicate, object)
        #new = self._get_pred_value_obj(subject, predicate)
        observation.call(predicate)
        
      else:
        triple_method(subject, predicate, object)
        
      observation = self.world._observations.get(object)
      if observation:
        Prop = self.world._entities.get(predicate)
        if Prop and Prop.inverse:
          observation.call(Prop._inverse_storid)
          
      #if (predicate == rdf_type) and _INSTANCES_OF_CLASS and (not Class is None):
      #  for l, old_instances in l_2_old_instances.items():
      #    l._changed()
          
      if (predicate == rdf_type) and _INSTANCES_OF_CLASS:
        Class = self.world._get_by_storid(object)
        if not Class is None: # Else it is Thing
          for parent in Class.ancestors():
            for l in _INSTANCES_OF_CLASS.get(parent.storid, ()):
              l._changed()
              
    return f
  
  def _gen_triple_method_data(self, triple_method):
    def f(subject, predicate, object, datatype):
      observation = self.world._observations.get(subject)
      
      if observation:
        #old = self._get_triples_sp_od(subject, predicate)
        triple_method(subject, predicate, object, datatype)
        #new = self._get_triples_sp_od(subject, predicate)
        observation.call(predicate) #, new, old)
      else:
        triple_method(subject, predicate, object, datatype)
        
    return f
  
  def _entity_destroyed(self, entity):
    if _INSTANCES_OF_CLASS and isinstance(entity, Thing):
      Classes   = [Class for Class in entity.is_a if isinstance(Class, ThingClass)]
      Ancestors = { Ancestor for Class in Classes for Ancestor in Class.ancestors() }
      for Ancestor in Ancestors:
        for l in _INSTANCES_OF_CLASS.get(Ancestor.storid, ()):
          l._changed()

    
  
def start_observing(onto):
  if not hasattr(onto.world, "_observations"): onto.world._observations = {}
  if not onto.__class__ is ObservedOntology:
    onto.__class__ = ObservedOntology
    onto._add_obj_triple_raw_spo   = onto._gen_triple_method_obj(onto.graph._add_obj_triple_raw_spo)
    onto._set_obj_triple_raw_spo   = onto._gen_triple_method_obj(onto.graph._set_obj_triple_raw_spo)
    onto._del_obj_triple_raw_spo   = onto._gen_triple_method_obj(onto.graph._del_obj_triple_raw_spo)
    onto._add_data_triple_raw_spod = onto._gen_triple_method_data(onto.graph._add_data_triple_raw_spod)
    onto._set_data_triple_raw_spod = onto._gen_triple_method_data(onto.graph._set_data_triple_raw_spod)
    onto._del_data_triple_raw_spod = onto._gen_triple_method_data(onto.graph._del_data_triple_raw_spod)
    
def stop_observing(onto):
  onto.__class__ = Ontology
  onto._add_obj_triple_raw_spo   = onto._add_obj_triple_raw_spo
  onto._set_obj_triple_raw_spo   = onto._set_obj_triple_raw_spo
  onto._del_obj_triple_raw_spo   = onto._del_obj_triple_raw_spo
  onto._add_data_triple_raw_spod = onto._add_data_triple_raw_spod
  onto._set_data_triple_raw_spod = onto._set_data_triple_raw_spod
  onto._del_data_triple_raw_spod = onto._del_data_triple_raw_spod
  
  

_NON_EMPTY_COLLAPSED_LISTENERS = set()
class Observation(object):
  def __init__(self, o):
    self.listeners           = []
    self.collapsed_listeners = []
    self.o                   = o
    self.collapsed_changes   = set()
    
  def call(self, predicate):
    for listener in self.listeners: listener(self.o, predicate)
    
  def add_listener(self, listener, collapsed):
    if collapsed:
      if not self.collapsed_listeners:
        self.listeners.append(self.collapser)
      self.collapsed_listeners.append(listener)
    else:
      self.listeners.append(listener)
      
  def remove_listener(self, listener):
    if   listener in self.collapsed_listeners:
      self.collapsed_listeners.remove(listener)
      if not self.collapsed_listeners:
        self.listeners.remove(self.collapser)
    elif listener in self.listeners:
      self.listeners.remove(listener)
    
  def collapser(self, o, predicate):
    if not self.collapsed_changes: _NON_EMPTY_COLLAPSED_LISTENERS.add(self)
    self.collapsed_changes.add(predicate)
    
  def scan(self):
    for listener in self.collapsed_listeners: listener(self.o, self.collapsed_changes)
    self.collapsed_changes.clear()
    
    

class ObjectPack(object):
  storid = 0 # Fake storid
  
  def __init__(self, objects):
    self._objects = objects

  def __repr__(self): return "<ObjectPack %s>" % self._objects
  
  
def scan_collapsed_changes():
  for collapsed_listener in _NON_EMPTY_COLLAPSED_LISTENERS: collapsed_listener.scan()
  _NON_EMPTY_COLLAPSED_LISTENERS.clear()
  

def observe(o, listener, collapsed = False, world = None):
  if isinstance(o, ObjectPack):
    for o2 in o._objects: observe(o2, listener, collapsed, world)
    return
  
  #print("OBSERVE", sum(len(obs.collapsed_listeners) for obs in (world or o.namespace.world)._observations.values()), o, listener)
  if world is None:
    world = o.namespace.world
    o = o.storid
    
  observation = world._observations.get(o)
  if not observation: observation = world._observations[o] = Observation(o)
  observation.add_listener(listener, collapsed)
  
    
def isobserved(o, listener = None, world = None):
  if isinstance(o, ObjectPack):
    for o2 in o._objects:
      if isobserved(o2, listener, world): return True
    return False
  
  if world is None:
    world = o.namespace.world
    o = o.storid
  
  observation = world._observations.get(o)
  if listener: return observation and ((listener in observation.listeners) or (listener in observation.collapsed_listeners))
  else:        return observation and observation.listeners

def send_event(o, pred, world = None):
  if isinstance(o, ObjectPack):
    for o2 in o._objects: send_event(o2, pred)
    return
  
  if world is None:
    world = o.namespace.world
    o = o.storid
    
  observation = world._observations.get(o)
  if observation: observation.call(pred)
  
def unobserve(o, listener = None, world = None):
  if isinstance(o, ObjectPack):
    for o2 in o._objects: unobserve(o2, listener, world)
    return
  
  #print("UNOBSERVE", sum(len(obs.collapsed_listeners) for obs in (world or o.namespace.world)._observations.values()), o, listener)
  if world is None:
    world = o.namespace.world
    o = o.storid
  
  if listener:
    observation = world._observations.get(o)
    if observation:
      observation.remove_listener(listener)
      if not observation.listeners: del world._observations[o]
      
  else:
    if o in world._observations: del world._observations[o]

    
_INSTANCES_OF_CLASS = {} #weakref.WeakValueDictionary()



class StoridList(object):
  def __init__(self, graph_manager, storids):
    self.namespace = graph_manager
    self._storids = storids
    
  def _update(self): pass
      
  def __len__(self):
    if self._storids is None: self._update()
    return len(self._storids)
  
  def __iter__(self):
    if self._storids is None: self._update()
    for i in self._storids: yield self.namespace._get_by_storid(i)
    
  def __getitem__(self, i):
    if self._storids is None: self._update()
    if isinstance(i, slice):
      return [self.namespace._get_by_storid(x) for x in self._storids.__getitem__(i)]
    else:
      return self.namespace._get_by_storid(self._storids[i])
    
  def __repr__(self):
    return """<StoridList: %s>""" % list(self)
  


from owlready2.util import FirstList
class InstancesOfClass(StoridList):
  storid = 0 # Fake storid
  
  def __init__(self, Class, onto = None, order_by = "", lang = "", use_observe = False):
    self._Class         = Class
    self._lang          = lang
    self._use_observe   = use_observe
    self._Class_storids = ",".join((["'%s'" % child.storid for child in Class.descendants()]))
    
    if use_observe:
      ws = _INSTANCES_OF_CLASS.get(Class.storid)
      if ws is None: ws = _INSTANCES_OF_CLASS[Class.storid] = weakref.WeakSet()
      ws.add(self)
      
    StoridList.__init__(self, onto or Class.namespace.world, None)
    
    if order_by:
      if   isinstance(order_by, str):
        self._order_by = self.namespace.world._props[order_by].storid
      elif order_by:
        self._order_by = order_by.storid
    else:
      self._order_by = ""
      
  def __repr__(self):
    return """<InstancesOfClass "%s": %s>""" % (self._Class, list(self))
  
  def _update(self):
    if self._order_by:
      if self._lang:
        self._storids = [x[0] for x in self.namespace.graph.execute("""SELECT s FROM objs WHERE p = ? AND o IN (%s) ORDER BY (select q2.o FROM quads q2 WHERE q2.s = objs.s AND q2.p = ? AND q2.d LIKE '@%s')""" % (self._Class_storids, self._lang), (rdf_type, self._order_by))]
      else:
        self._storids = [x[0] for x in self.namespace.graph.execute("""SELECT s FROM objs WHERE p = ? AND o IN (%s) ORDER BY (select q2.o FROM quads q2 WHERE q2.s = objs.s AND q2.p = ?)""" % self._Class_storids, (rdf_type, self._order_by))]
    else:
      self._storids = [x[0] for x in self.namespace.graph.execute("""SELECT s FROM objs WHERE p = ? AND o IN (%s)""" % self._Class_storids, (rdf_type,)).fetchall()]
      
  def _get_storids(self):
    if self._storids is None: self._update()
    return self._storids
    
  def _get_old_value(self):
    if self._storids is None: self._update()
    return StoridList(self.namespace, self._storids)
  
  def _changed(self):
    observation = self.namespace.world._observations.get(self.storid)
    self._storids = None
    if observation:
      observation.call("Inverse(http://www.w3.org/1999/02/22-rdf-syntax-ns#type)")
      
  def add(self, o):
    if not self.Class in o.is_a: o.is_a.append(self.Class)
    #if not self._use_observe: self._changed()
  append = add
  
  def remove(self, o):
    destroy_entity(o)
    #self._changed()
    
