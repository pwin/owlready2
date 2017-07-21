# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2017 Jean-Baptiste LAMY
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

from owlready2.base import *

class BaseGraph(object):
  READ_METHODS  = ["refactor", "new_numbered_iri", "abbreviate", "unabbreviate", "get_triple_sp", "get_triple_po", "get_transitive_sp", "get_transitive_po", "get_transitive_sym", "get_transitive_sp_indirect", "get_triples", "get_triples_s", "get_triples_sp", "get_triples_po", "get_pred", "get_quads", "get_quads_sp", "has_triple", "_del_triple"]
  WRITE_METHODS = ["_add_triple", "_set_triple"]
  
  def sub_graph(self, user_context): return self.__class__(self, user_context)
  
  def context_2_user_context(self, context): raise NotImplementedError
  
  def parse(self, f): raise NotImplementedError
    
  def save(self, f, format = "pretty-xml"): raise NotImplementedError
  
  def abbreviate  (self, iri): return iri
  def unabbreviate(self, iri): return iri
  
  def has_triple(self, subject = None, predicate = None, object = None):
    for s,p,o in self.get_triples(subject, predicate, object):
      return True
    return False
    
  def get_triple_sp(self, subject, predicate):
    for o in self.get_triples_sp(subject, predicate): return o
    return None
  
  def get_triple_po(self, predicate, object):
    for s in self.get_triples_po(predicate, object): return s
    return None
  
  #def get_transitive_po(self, predicate, object, already = None):
  #  if already is None: already = set()
  #  if not object in already:
  #    already.add(object)
  #    for s in self.get_triples_po(predicate, object):
  #      self.get_transitive_po(predicate, s, already)
  #  return already
  
  #def get_transitive_sp(self, subject, predicate, already = None):
  #  if already is None: already = set()
  #  if not subject in already:
  #    already.add(subject)
  #    for o in self.get_triples_sp(subject, predicate):
  #      self.get_transitive_sp(o, predicate, already)
  #  return already
  
  #def get_transitive_sym(self, subject, predicate, already = None):
  #  if already is None: already = set()
  #  if not subject in already:
  #    already.add(subject)
  #    for s in self.get_triples_po(predicate, subject): self.get_transitive_sym(s, predicate, already)
  #    for s in self.get_triples_sp(subject, predicate): self.get_transitive_sym(s, predicate, already)
  #  return already
  
  #def get_transitive_sp_indirect(self, subject, predicates_inverses, already = None):
  #  if already is None: already = set()
  #  if not subject in already:
  #    already.add(subject)
  #    for (predicate, inverse) in predicates_inverses:
  #      for o in self.get_triples_sp(subject, predicate): self.get_transitive_sp_indirect(o, predicates_inverses, already)
  #      if inverse:
  #        for o in self.get_triples_po(inverse, subject): self.get_transitive_sp_indirect(o, predicates_inverses, already)
  #  return already

  def get_transitive_sp(self, subject, predicate, already = None):
    if already is None: already = set()
    else:
      if subject in already: return already
      already.add(subject)
    for o in self.get_triples_sp(subject, predicate):
      self.get_transitive_sp(o, predicate, already)
    return already
  
  def get_transitive_po(self, predicate, object, already = None):
    if already is None: already = set()
    else:
      if object in already: return already
      already.add(object)
    for s in self.get_triples_po(predicate, object):
      self.get_transitive_po(predicate, s, already)
    return already
  
  def get_transitive_sym(self, subject, predicate, already = None):
    if already is None: already = set()
    else:
      if subject in already: return already
      already.add(subject)
    for s in self.get_triples_po(predicate, subject): self.get_transitive_sym(s, predicate, already)
    for s in self.get_triples_sp(subject, predicate): self.get_transitive_sym(s, predicate, already)
    return already
  
  def get_transitive_sp_indirect(self, subject, predicates_inverses, already = None):
    if already is None: already = set()
    else:
      if subject in already: return already
      already.add(subject)
    for (predicate, inverse) in predicates_inverses:
      for o in self.get_triples_sp(subject, predicate): self.get_transitive_sp_indirect(o, predicates_inverses, already)
      if inverse:
        for o in self.get_triples_po(inverse, subject): self.get_transitive_sp_indirect(o, predicates_inverses, already)
    return already
  
    
  def get_triples(self, subject = None, predicate = None, object = None):
    for s,p,o,c in self.get_quads(subject, predicate, object, None):
      yield s,p,o
      
  def get_triples_s(self, subject):
    return [(p,o) for s,p,o in self.get_triples(subject, None, None)]
  
  def get_triples_sp(self, subject, predicate):
    return [o for s,p,o in self.get_triples(subject, predicate, None)]
  
  def get_triples_po(self, predicate, object):
    return [s for s,p,o in self.get_triples(None, predicate, object)]
  
  def get_quads(self, subject = None, predicate = None, object = None, ontology_graph = None):
    raise NotImplementedError
  
  def get_quads_sp(self, subject, predicate):
    return [(o,c) for s,p,o,c in self.get_quads(subject, predicate)]
  
  def __len__(self): raise NotImplementedError
  
  def _add_triple(self, subject, predicate, object):
    raise NotImplementedError
  
  def _del_triple(self, subject, predicate, object):
    raise NotImplementedError
  
  def _set_triple(self, subject, predicate, object):
    self._del_triple(subject, predicate, None)
    self._add_triple(subject, predicate, object)
    
  def refactor(self, storid, new_iri):
    raise NotImplementedError
    
