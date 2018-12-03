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
from owlready2.entity    import *
from owlready2.prop      import *


class AllDisjoint(object):
  def __init__(self, entities, ontology = None, bnode = None):
    if not CURRENT_NAMESPACES[-1] is None: self.ontology = CURRENT_NAMESPACES[-1].ontology
    else:                                  self.ontology = ontology or entities[0].namespace.ontology
    
    # For AllDisjoint, storid can be either:
    #   * a blank node, when at least 3 entities are involved
    #   * a triple, when only 2 entities, e.g. (entity1.storid, owl_disjointwith, entity2.storid)
    
    if   isinstance(entities, int):
      assert isinstance(bnode, int)
      self.storid      = bnode
      self._list_bnode = entities
    elif isinstance(entities, tuple):
      self.storid      = entities
    else:
      self.storid      = bnode
      self._list_bnode = None
      self.entities = self.Properties = self.individuals = CallbackList(entities, self, AllDisjoint._callback)
      
    if not LOADING: self._create_triples()
    
  def __getattr__(self, attr):
    if attr == "entities":
      if isinstance(self.storid, int):
        r = self.ontology._parse_list(self._list_bnode)
      else:
        r = [self.ontology.world._get_by_storid(self.storid[0]), self.ontology.world._get_by_storid(self.storid[2])]
      r = CallbackList(r, self, AllDisjoint._callback)
      setattr(self, attr,r)
      return r
    return super().__getattribute__(attr)
  
  def _callback(self, old):
    if self.ontology:
      self._destroy_triples()
      self._create_triples ()
      
  def _destroy_triples(self):
    if   isinstance(self.storid, int):
      self.ontology._del_obj_triple_spod(self.storid, None, None)
      self.ontology._del_list(self._list_bnode)
    elif isinstance(self.storid, tuple):
      self.ontology._del_obj_triple_spod(*self.storid)
      
  def destroy(self): self._destroy_triples()
  
  def _create_triples(self):
    if len(self.entities) == 2:
      if   isinstance(self.entities[0], ThingClass):
        self.storid = (self.entities[0].storid, owl_disjointwith, self.entities[1].storid)
        self.ontology._add_obj_triple_spo(*self.storid)
        return
      elif isinstance(self.entities[0], PropertyClass):
        self.storid = (self.entities[0].storid, owl_propdisjointwith, self.entities[1].storid)
        self.ontology._add_obj_triple_spo(*self.storid)
        return
      # It seems that there is no 1-1 relation for individuals
      # => continue
    
    if len(self.entities) >= 2:
      if not isinstance(self.storid, int): self.storid      = self.ontology.world.new_blank_node()
      if not self._list_bnode:             self._list_bnode = self.ontology.world.new_blank_node()
      
      if   isinstance(self.entities[0], ThingClass):
        self.ontology._add_obj_triple_spo(self.storid, rdf_type, owl_alldisjointclasses)
        self.ontology._add_obj_triple_spo(self.storid, owl_members, self._list_bnode)
        
      elif isinstance(self.entities[0], PropertyClass):
        self.ontology._add_obj_triple_spo(self.storid, rdf_type, owl_alldisjointproperties)
        self.ontology._add_obj_triple_spo(self.storid, owl_members, self._list_bnode)
        
      else: # Individuals
        self.ontology._add_obj_triple_spo(self.storid, rdf_type, owl_alldifferent)
        self.ontology._add_obj_triple_spo(self.storid, owl_distinctmembers, self._list_bnode)
        
      self.ontology._set_list(self._list_bnode, self.entities)
      
  def __repr__(self):
    if self.ontology != self.entities[0].namespace.ontology: onto = ", ontology = %s" % self.ontology
    else:                                                    onto = ""
    return "AllDisjoint([%s]%s)" % (", ".join(repr(Class) for Class in self.entities), onto)
    
AllDifferent = AllDisjoint


def partition(mother, children):
  mother.is_a.append(Or(children))
  AllDisjoint(children)
