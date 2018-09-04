# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2007-2018 Jean-Baptiste LAMY
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

__all__ = ["start_observing", "stop_observing", "observe", "unobserve", "isobserved", "send_event", "CollapsedListener", "scan_collapsed_changes"]

import weakref

from owlready2.base import rdf_type, rdfs_subclassof, owl_equivalentclass, owl_equivalentproperty, owl_equivalentindividual
from owlready2.namespace import Ontology
import editobj3.introsp

class ObservedOntology(Ontology):
  def _get_pred_value(self, subject, predicate):
    if   predicate == rdf_type:
      return list(filter(None, [self._to_python(o, default_to_none = True) for o in self.get_triples_sp(subject, predicate)]))
    else:
      return [self._to_python(o) for o in self.get_triples_sp(subject, predicate)]
    
  def _gen_triple_method(self, triple_method):
    def f(subject, predicate, object):
      observation = self.world._observations.get(subject)
        
      if (predicate == rdf_type) and _INSTANCES_OF_CLASS:
        Class = self.world._get_by_storid(object)
        l_2_old_instances = {}
        if not Class is None: # Else it is Thing
          for parent in Class.ancestors():
            for l in _INSTANCES_OF_CLASS.get(parent.storid, ()):
              l_2_old_instances[l] = l._get_old_value()
              
      if observation:
        old = self._get_pred_value(subject, predicate)
        triple_method(subject, predicate, object)
        new = self._get_pred_value(subject, predicate)
        Prop = self.world._get_by_storid(predicate)
        observation.call(self.world.graph.unabbreviate(predicate), new, old)
      else:
        triple_method(subject, predicate, object)
        
      if (predicate == rdf_type) and _INSTANCES_OF_CLASS and (not Class is None):
        for l, old_instances in l_2_old_instances.items():
          l._changed(old_instances)
          
    return f
  
  
def start_observing(onto):
  if not hasattr(onto.world, "_observations"): onto.world._observations = {}
  if onto.__class__ is ObservedOntology: return
  onto.__class__ = ObservedOntology
  onto._add_triple = onto._gen_triple_method(onto.graph._add_triple)
  onto._set_triple = onto._gen_triple_method(onto.graph._set_triple)
  onto._del_triple = onto._gen_triple_method(onto.graph._del_triple)
  
def stop_observing(onto):
  onto.__class__ = Ontology
  onto._add_triple = onto.graph._add_triple
  onto._set_triple = onto.graph._set_triple
  onto._del_triple = onto.graph._del_triple
  
  
  
_NON_EMPTY_COLLAPSED_LISTENERS = set()
class CollapsedListener(object):
  def __init__(self, listener = None):
    self.listener = listener
    self.collapsed_changes = {}
    
  def __eq__(self, other): return isinstance(other, CollapsedListener) and (self.listener == other.listener)
  
  def __hash__(self): return hash(self.listener)
  
  def __call__(self, obj, pred, new, old):
    l = self.collapsed_changes.get(obj)
    if l is None:
      if not self.collapsed_changes: _NON_EMPTY_COLLAPSED_LISTENERS.add(self)
      self.collapsed_changes[obj] = { pred : [new, old] }
    else:
      l2 = l.get(pred)
      if l2 is None: l[pred] = [new, old]
      else:          l2[0] = new
      
  def scan(self):
    for obj, l in self.collapsed_changes.items():
      self.listener(obj, [(pred, values[0], values[1]) for (pred, values) in l.items()])
    self.collapsed_changes.clear()
    
    
def scan_collapsed_changes():
  for collapsed_listener in _NON_EMPTY_COLLAPSED_LISTENERS: collapsed_listener.scan()
  _NON_EMPTY_COLLAPSED_LISTENERS.clear()
  

def observe(o, listener):
  if isinstance(o, editobj3.introsp.ObjectPack):
    for o2 in o.objects: observe(o2, listener)
    return
  
  observation = o.namespace.world._observations.get(o.storid)
  if observation: observation.listeners.append(listener)
  else:
    o.namespace.world._observations[o.storid] = Observation(o, [listener])
    
    
def isobserved(o, listener = None):
  if isinstance(o, editobj3.introsp.ObjectPack):
    for o2 in o.objects:
      if isobserved(o2, listener): return True
    return False
  
  observation = o.namespace.world._observations.get(o.storid)
  
  if listener: return observation and (listener in observation.listeners)
  else:        return observation and observation.listeners

def send_event(o, pred, new, old):
  observation = o.namespace.world._observations.get(o.storid)
  if observation: observation.call(pred, new, old)
    
def unobserve(o, listener = None):
  if isinstance(o, editobj3.introsp.ObjectPack):
    for o2 in o.objects: unobserve(o2, listener)
    return
    
  if listener:
    observation = o.namespace.world._observations.get(o.storid)
    if observation:
      try: observation.listeners.remove(listener)
      except ValueError: pass
      if not observation.listeners: del o.namespace.world._observations[o.storid]
      
  else:
    if o.storid in o.namespace.world._observations: del o.namespace.world._observations[o.storid]


class Observation(object):
  def __init__(self, o, listeners):
    self.listeners = listeners
    try:    self.object = weakref.ref(o)
    except: self.object = o
    
  def call(self, predicate, new, old):
    for listener in self.listeners: listener(self.object(), predicate, new, old)
    
    
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
      
    
class InstancesOfClass(StoridList):
  def __init__(self, Class, onto = None, order_by = "", lang = "", use_observe = False):
    self._Class = Class
    self._lang  = lang
    self._Class_storids = ",".join((["'%s'" % child.storid for child in Class.descendants()]))
    self.storid = "InstancesOfClass(%s)" % Class.storid # Fake storid
    
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
        self._storids = [x[0] for x in self.namespace.graph.execute("""SELECT s FROM quads WHERE p = ? AND o IN (%s) ORDER BY (select q2.o FROM quads q2 WHERE q2.s = quads.s AND q2.p = ? AND q2.o LIKE '%%@%s')""" % (self._Class_storids, self._lang), (rdf_type, self._order_by))]
      else:
        self._storids = [x[0] for x in self.namespace.graph.execute("""SELECT s FROM quads WHERE p = ? AND o IN (%s) ORDER BY (select q2.o FROM quads q2 WHERE q2.s = quads.s AND q2.p = ?)""" % self._Class_storids, (rdf_type, self._order_by))]
    else:
      self._storids = [x[0] for x in self.namespace.graph.execute("""SELECT s FROM quads WHERE p = ? AND o IN (%s)""" % self._Class_storids, (rdf_type)).fetchall()]
      
  def _get_old_value(self):
    if self._storids is None: self._update()
    return StoridList(self.namespace, self._storids)
  
  def _changed(self, old):
    observation = self.namespace.world._observations.get(self.storid)
    if observation:
      self._storids = None
      observation.call("Inverse(http://www.w3.org/1999/02/22-rdf-syntax-ns#type)", self, old)
    else:
      self._storids = None
    
  def add(self, o):
    if not self.Class in o.is_a: o.is_a.append(self.Class)
    self._changed()
  append = add
  
  def remove(self, o):
    destroy_entity(o)
    self._changed()
    
    
    
    
if __name__ == "__main__":
  from owlready2 import *
  
  onto = get_ontology("http://test.org/test.owl")
  start_observing(onto)
  
  with onto:
    class C(Thing): pass
    c1 = C()
    c2 = C()
    c2.label.en = "AAA ?"
    c2.label.fr = "Paracétamol"
    c3 = C()
    c3.label.en = "Asprine"
    c3.label.fr = "Asprin"
    class D(Thing): pass
    
  default_world.graph.dump()

  def listener(obj, p, new, old):
    print("changed!", obj, p, new, old)
  
  l = InstancesOfClass(C, order_by = "label", lang = "fr", use_observe = True)
  observe(l, listener)
  
  print(len(l))
  print(l[0])
  print(l[1])
  print(l[2])
  print(l[0:2])
  
  print(l)
  
  c3 = C()
  
  print(l)
  
  
  set_log_level(9)
