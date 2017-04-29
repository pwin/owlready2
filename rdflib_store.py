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

import rdflib, rdflib.store
from rdflib import URIRef, BNode, Literal

class TripleLiteRDFlibStore(rdflib.store.Store):
  context_aware = True
  
  def __init__(self, world):
    self.world      = world
    self.triplelite = world.graph
    super().__init__()
    
    self.main_graph            = rdflib.Graph(store = self)
    self.main_graph.triplelite = self.triplelite
    
    self.context_graphs = {}
    for onto, triplelite in self.triplelite.onto_2_subgraph.items():
      graph            = rdflib.Graph(store = self, identifier = URIRef(onto.base_iri))
      graph.triplelite = triplelite
      self.context_graphs[onto] = graph
      
  def _2_python(self, x):
    if   isinstance(x, rdflib.term.URIRef ): return self.world[str(x)]
    elif isinstance(x, rdflib.term.BNode  ): return str(x)
    elif isinstance(x, rdflib.term.Literal): return x.toPython()
    
  def _rdflib_2_owlready(self, spo):
    s,p,o = spo
    if   isinstance(s, rdflib.term.URIRef ): s = self.triplelite.abbreviate(s)
    elif isinstance(s, rdflib.term.BNode  ): s = str(s)
    if   isinstance(p, rdflib.term.URIRef ): p = self.triplelite.abbreviate(p)
    if   isinstance(o, rdflib.term.URIRef ): o = self.triplelite.abbreviate(o)
    elif isinstance(o, rdflib.term.BNode  ): o = str(o)
    elif isinstance(o, rdflib.term.Literal):
      if o.language is None:
        if o.datatype:
          o = '"%s"%s' % (o.value, self.triplelite.abbreviate(o.datatype))
        else:
          o = '"%s"' % o.value
      else:
        o = '"%s"@%s' % (o.value, o.language)
    return s,p,o
  
  def _owlready_2_rdflib(self, s,p,o):
    if   s.startswith("_"): s = BNode(s)
    else:                   s = URIRef(self.triplelite.unabbreviate(s))
    p = URIRef(self.triplelite.unabbreviate(p))
    if   o.startswith("_"): o = BNode(o)
    elif o.startswith('"'):
      v, l = o.rsplit('"', 1)
      if   l.startswith("@"): o = Literal(v[1:], lang = l[1:])
      elif l == "":           o = Literal(v[1:])
      else:                   o = Literal(v[1:], datatype = URIRef(self.triplelite.unabbreviate(l)))
    else: o = URIRef(self.triplelite.unabbreviate(o))
    return s,p,o
  
  def add(self, xxx_todo_changeme, context, quoted = False):
    s,p,o = self._rdflib_2_owlready(xxx_todo_changeme)

    context.triplelite._add_triple(s,p,o)
    #super().add(xxx_todo_changeme, context, quoted)
    
  def remove(self, xxx_todo_changeme, context = None):
    s,p,o = self._rdflib_2_owlready(xxx_todo_changeme)
    context.triplelite._del_triple(s,p,o)
    #super().remove(xxx_todo_changeme, context, quoted)
    
  def triples(self, triple_pattern, context = None):
    s,p,o = self._rdflib_2_owlready(triple_pattern)
    
    #print(triple_pattern)
    #print(context, s,p,o)
    #print(context.triplelite.get_triples(s,p,o))
    #print()
    
    for s,p,o in context.triplelite.get_triples(s,p,o):
      yield self._owlready_2_rdflib(s,p,o), context
      
  def __len__(self, context = None):
    return len(context.triplelite)
  
  def contexts(self, triple = None):
    if triple is None:
      return self.context_graphs.values()
    else:
      triple = self._rdflib_2_owlready(triple)
      for graph in self.context_graphs.values():
        if graph.triplelite.has_triple(*triple): yield graph
    
  
