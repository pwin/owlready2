# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2017-2018 Jean-Baptiste LAMY
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

import sys, os, os.path, sqlite3, time, re
from collections import defaultdict

import owlready2
from owlready2.base import *
from owlready2.driver import BaseMainGraph, BaseSubGraph
from owlready2.driver import _guess_format, _save
from owlready2.util import _int_base_62, FTS
from owlready2.base import _universal_abbrev_2_iri

def all_combinations(l):
  """returns all the combinations of the sublist in the given list (i.e. l[0] x l[1] x ... x l[n])."""
  if len(l) == 0: return ()
  if len(l) == 1: return [(a,) for a in l[0]]
  r = []
  for a in l[0]: r.extend((a,) + b for b in all_combinations(l[1:]))
  return r

class Graph(BaseMainGraph):
  _SUPPORT_CLONING = True
  def __init__(self, filename, clone = None, exclusive = True, world = None):
    exists        = os.path.exists(filename) and os.path.getsize(filename) # BEFORE creating db!
    initialize_db = (clone is None) and ((filename == ":memory:") or (not exists))
    
    self.db = sqlite3.connect(filename, check_same_thread = False)
    if exclusive: self.db.execute("""PRAGMA locking_mode = EXCLUSIVE""")
    else:         self.db.execute("""PRAGMA locking_mode = NORMAL""")
    
    self.execute  = self.db.execute
    self.c_2_onto          = {}
    self.onto_2_subgraph   = {}
    self.last_numbered_iri = {}
    self.world             = world
    self.c                 = None
    
    if initialize_db:
      self.current_blank    = 0
      self.current_resource = 300 # 300 first values are reserved
      self.prop_fts         = {}
      
      self.execute("""CREATE TABLE store (version INTEGER, current_blank INTEGER, current_resource INTEGER)""")
      self.execute("""INSERT INTO store VALUES (3, 0, 300)""")
      self.execute("""CREATE TABLE quads (c INTEGER, s TEXT, p TEXT, o TEXT)""")
      self.execute("""CREATE TABLE ontologies (c INTEGER PRIMARY KEY, iri TEXT, last_update DOUBLE)""")
      self.execute("""CREATE TABLE ontology_alias (iri TEXT, alias TEXT)""")
      self.execute("""CREATE TABLE prop_fts (fts INTEGER PRIMARY KEY, storid TEXT)""")
      try:
        self.execute("""CREATE TABLE resources (storid TEXT PRIMARY KEY, iri TEXT) WITHOUT ROWID""")
      except sqlite3.OperationalError: # Old SQLite3 does not support WITHOUT ROWID -- here it is just an optimization
        self.execute("""CREATE TABLE resources (storid TEXT PRIMARY KEY, iri TEXT)""")
      self.db.executemany("INSERT INTO resources VALUES (?,?)", _universal_abbrev_2_iri.items())
      self.execute("""CREATE UNIQUE INDEX index_resources_iri ON resources(iri)""")
      self.execute("""CREATE INDEX index_quads_s ON quads(s)""")
      self.execute("""CREATE INDEX index_quads_o ON quads(o)""")
      self.db.commit()
      
    else:
      if clone:
        s = "\n".join(clone.db.iterdump())
        self.db.cursor().executescript(s)
        
      
      version, self.current_blank, self.current_resource = self.execute("SELECT version, current_blank, current_resource FROM store").fetchone()
      if version == 1:
        self.execute("""CREATE TABLE ontology_alias (iri TEXT, alias TEXT)""")
        self.execute("""UPDATE store SET version=2""")
        self.db.commit()
      if version == 2:
        self.execute("""CREATE TABLE prop_fts (fts INTEGER PRIMARY KEY, storid TEXT)""")
        self.execute("""UPDATE store SET version=3""")
        self.db.commit()
      self.prop_fts = { storid : fts for (fts, storid) in self.execute("""SELECT * FROM prop_fts;""") }
      
    self.current_changes = self.db.total_changes
    self.select_abbreviate_method()

  def close(self):
    self.db.close()
    
  def select_abbreviate_method(self):
    nb = self.execute("SELECT count(*) FROM resources").fetchone()[0]
    if nb < 100000:
      iri_storid = self.execute("SELECT iri, storid FROM resources").fetchall()
      self.  abbreviate_d = dict(iri_storid)
      self.unabbreviate_d = dict((storid, iri) for (iri, storid) in  iri_storid)
      self.abbreviate   = self.abbreviate_dict
      self.unabbreviate = self.unabbreviate_dict
      self.refactor     = self.refactor_dict
    else:
      self.  abbreviate_d = None
      self.unabbreviate_d = None
      self.abbreviate   = self.abbreviate_sql
      self.unabbreviate = self.unabbreviate_sql
      self.refactor     = self.refactor_sql
    if self.world:
      self.world.abbreviate   = self.abbreviate
      self.world.unabbreviate = self.unabbreviate
    for subgraph in self.onto_2_subgraph.values():
      subgraph.onto.abbreviate   = subgraph.abbreviate   = self.abbreviate
      subgraph.onto.unabbreviate = subgraph.unabbreviate = self.unabbreviate
      
  # def fix_base_iri(self, base_iri, c = None):
  #   if base_iri.endswith("#") or base_iri.endswith("/"): return base_iri
    
  #   if c is None:
  #     use_hash = self.execute("SELECT resources.iri FROM quads, resources WHERE resources.storid=quads.s AND resources.iri LIKE ? LIMIT 1", (base_iri + "#%",)).fetchone()
  #   else:
  #     use_hash = self.execute("SELECT resources.iri FROM quads, resources WHERE quads.c=? AND resources.storid=quads.s AND resources.iri LIKE ? LIMIT 1", (c, base_iri + "#%")).fetchone()
  #   if use_hash: return "%s#" % base_iri
  #   else:
  #     if c is None:
  #       use_slash = self.execute("SELECT resources.iri FROM quads, resources WHERE resources.storid=quads.s AND resources.iri LIKE ? LIMIT 1", (base_iri + "/%",)).fetchone()
  #     else:
  #       use_slash = self.execute("SELECT resources.iri FROM quads, resources WHERE quads.c=? AND resources.storid=quads.s AND resources.iri LIKE ? LIMIT 1", (c, base_iri + "/%")).fetchone()
  #     if use_slash: return "%s/" % base_iri
  #     else:         return "%s#" % base_iri
      
  #   return "%s#" % base_iri
    
  def fix_base_iri(self, base_iri, c = None):
    if base_iri.endswith("#") or base_iri.endswith("/"): return base_iri
    use_slash = self.execute("SELECT resources.iri FROM resources WHERE SUBSTR(resources.iri, 1, ?)=? LIMIT 1", (len(base_iri) + 1, base_iri + "/",)).fetchone()
    if use_slash: return "%s/" % base_iri
    else:         return "%s#" % base_iri
    
  def sub_graph(self, onto):
    new_in_quadstore = False
    c = self.execute("SELECT c FROM ontologies WHERE iri=?", (onto.base_iri,)).fetchone()
    if c is None:
      c = self.execute("SELECT ontologies.c FROM ontologies, ontology_alias WHERE ontology_alias.alias=? AND ontologies.iri=ontology_alias.iri", (onto.base_iri,)).fetchone()
      if c is None:
        new_in_quadstore = True
        self.execute("INSERT INTO ontologies VALUES (NULL, ?, 0)", (onto.base_iri,))
        c = self.execute("SELECT c FROM ontologies WHERE iri=?", (onto.base_iri,)).fetchone()
    c = c[0]
    self.c_2_onto[c] = onto
    
    return SubGraph(self, onto, c, self.db), new_in_quadstore
  
  def ontologies_iris(self):
    for (iri,) in self.execute("SELECT iri FROM ontologies").fetchall(): yield iri
      
  def abbreviate_sql(self, iri):
    r = self.execute("SELECT storid FROM resources WHERE iri=? LIMIT 1", (iri,)).fetchone()
    if r: return r[0]
    self.current_resource += 1
    storid = _int_base_62(self.current_resource)
    self.execute("INSERT INTO resources VALUES (?,?)", (storid, iri))
    return storid
  
  def unabbreviate_sql(self, storid):
    return self.execute("SELECT iri FROM resources WHERE storid=? LIMIT 1", (storid,)).fetchone()[0]
  
  def abbreviate_dict(self, iri):
    storid = self.abbreviate_d.get(iri)
    if storid is None:
      self.current_resource += 1
      storid = self.abbreviate_d[iri] = _int_base_62(self.current_resource)
      self.unabbreviate_d[storid] = iri
      self.execute("INSERT INTO resources VALUES (?,?)", (storid, iri))
    return storid
  
  def unabbreviate_dict(self, storid):
    return self.unabbreviate_d[storid]
  
  def get_storid_dict(self):
    return dict(self.execute("SELECT storid, iri FROM resources").fetchall())
  
  def new_numbered_iri(self, prefix):
    if prefix in self.last_numbered_iri:
      i = self.last_numbered_iri[prefix] = self.last_numbered_iri[prefix] + 1
      return "%s%s" % (prefix, i)
    else:
      cur = self.execute("SELECT iri FROM resources WHERE iri GLOB ? ORDER BY LENGTH(iri) DESC, iri DESC", ("%s*" % prefix,))
      while True:
        iri = cur.fetchone()
        if not iri: break
        num = iri[0][len(prefix):]
        if num.isdigit():
          self.last_numbered_iri[prefix] = i = int(num) + 1
          return "%s%s" % (prefix, i)
        
    self.last_numbered_iri[prefix] = 1
    return "%s1" % prefix
  
  def refactor_sql(self, storid, new_iri):
    self.execute("UPDATE resources SET iri=? WHERE storid=?", (new_iri, storid,))

  def refactor_dict(self, storid, new_iri):
    self.execute("UPDATE resources SET iri=? WHERE storid=?", (new_iri, storid,))
    del self.abbreviate_d[self.unabbreviate_d[storid]]
    self.  abbreviate_d[new_iri] = storid
    self.unabbreviate_d[storid]  = new_iri
    
  def commit(self):
    if self.current_changes != self.db.total_changes:
      self.current_changes = self.db.total_changes
      self.execute("UPDATE store SET current_blank=?, current_resource=?", (self.current_blank, self.current_resource))
      self.db.commit()



  def context_2_user_context(self, c): return self.c_2_onto[c]

  def new_blank_node(self):
    self.current_blank += 1
    return "_%s" % _int_base_62(self.current_blank)
  
  def get_triples(self, s, p, o, ignore_missing_datatype = False):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads")
        else:
          if ignore_missing_datatype and o.endswith('"'):
            cur = self.execute("SELECT s,p,o FROM quads WHERE SUBSTR(o,1,?)=?", (len(o), o,))
          else:
            cur = self.execute("SELECT s,p,o FROM quads WHERE o=?", (o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads WHERE p=?", (p,))
        else:
          if ignore_missing_datatype and o.endswith('"'):
            cur = self.execute("SELECT s,p,o FROM quads WHERE p=? AND SUBSTR(o,1,?)=?", (p, len(o), o,))
          else:
            cur = self.execute("SELECT s,p,o FROM quads WHERE p=? AND o=?", (p, o,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads WHERE s=?", (s,))
        else:
          if ignore_missing_datatype and o.endswith('"'):
            cur = self.execute("SELECT s,p,o FROM quads WHERE s=? AND SUBSTR(o,1,?)=?", (s, len(o), o,))
          else:
            cur = self.execute("SELECT s,p,o FROM quads WHERE s=? AND o=?", (s, o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads WHERE s=? AND p=?", (s, p,))
        else:
          if ignore_missing_datatype and o.endswith('"'):
            cur = self.execute("SELECT s,p,o FROM quads WHERE s=? AND p=? AND SUBSTR(o,1,?)=?", (s, p, len(o), o))
          else:
            cur = self.execute("SELECT s,p,o FROM quads WHERE s=? AND p=? AND o=?", (s, p, o,))
    return cur.fetchall()
    
  def get_quads(self, s, p, o, c):
    if c is None:
      if s is None:
        if p is None:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads")
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE o=?", (o,))
        else:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads WHERE p=?", (p,))
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE p=? AND o=?", (p, o,))
      else:
        if p is None:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads WHERE s=?", (s,))
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE s=? AND o=?", (s, o,))
        else:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads WHERE s=? AND p=?", (s, p,))
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE s=? AND p=? AND o=?", (s, p, o,))
    else:
      if s is None:
        if p is None:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=?", (c,))
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND o=?", (c, o,))
        else:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND p=?", (c, p,))
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND p=? AND o=?", (c, p, o,))
      else:
        if p is None:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=?", (c, s,))
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=? AND o=?", (c, s, o,))
        else:
          if o is None: cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=? AND p=?", (c, s, p,))
          else:         cur = self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=? AND p=? AND o=?", (c, s, p, o,))
    return cur.fetchall()
  
  def get_quads_sp(self, s, p):
    return self.execute("SELECT o,c FROM quads WHERE s=? AND p=?", (s, p)).fetchall()
  
  def get_pred(self, s):
    for (x,) in self.execute("SELECT DISTINCT p FROM quads WHERE s=?", (s,)).fetchall(): yield x
    
  def get_triples_s(self, s):
    return self.execute("SELECT p,o FROM quads WHERE s=?", (s,)).fetchall()
  
  def get_triples_sp(self, s, p):
    for (x,) in self.execute("SELECT o FROM quads WHERE s=? AND p=?", (s, p)).fetchall(): yield x
    
  def get_triples_po(self, p, o):
    for (x,) in self.execute("SELECT s FROM quads WHERE p=? AND o=?", (p, o)).fetchall(): yield x
    
  def get_triple_sp(self, s = None, p = None):
    r = self.execute("SELECT o FROM quads WHERE s=? AND p=? LIMIT 1", (s, p)).fetchone()
    if r: return r[0]
    return None
     
  def get_triple_po(self, p = None, o = None):
    r = self.execute("SELECT s FROM quads WHERE p=? AND o=? LIMIT 1", (p, o)).fetchone()
    if r: return r[0]
    return None
  
  def has_triple(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM quads LIMIT 1")
        else:         cur = self.execute("SELECT s FROM quads WHERE o=? LIMIT 1", (o,))
      else:
        if o is None: cur = self.execute("SELECT s FROM quads WHERE p=? LIMIT 1", (p,))
        else:         cur = self.execute("SELECT s FROM quads WHERE p=? AND o=? LIMIT 1", (p, o))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM quads WHERE s=? LIMIT 1", (s,))
        else:         cur = self.execute("SELECT s FROM quads WHERE s=? AND o=? LIMIT 1", (s, o))
      else:
        if o is None: cur = self.execute("SELECT s FROM quads WHERE s=? AND p=? LIMIT 1", (s, p))
        else:         cur = self.execute("SELECT s FROM quads WHERE s=? AND p=? AND o=? LIMIT 1", (s, p, o))
    return not cur.fetchone() is None
  
  def _del_triple(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: self.execute("DELETE FROM quads")
        else:         self.execute("DELETE FROM quads WHERE o=?", (o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE p=?", (p,))
        else:         self.execute("DELETE FROM quads WHERE p=? AND o=?", (p, o,))
    else:
      if p is None:
        if o is None: self.execute("DELETE FROM quads WHERE s=?", (s,))
        else:         self.execute("DELETE FROM quads WHERE s=? AND o=?", (s, o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE s=? AND p=?", (s, p,))
        else:         self.execute("DELETE FROM quads WHERE s=? AND p=? AND o=?", (s, p, o,))
        
        
  def search(self, prop_vals, c = None):
    tables       = []
    conditions   = []
    params       = []
    alternatives = []
    excepts      = []
    i = 0
    
    for k, v in prop_vals:
      if v is None:
        excepts.append(k)
        continue
      
      i += 1
      tables.append("quads q%s" % i)
      if not c is None:
        conditions  .append("q%s.c = ?" % i)
        params      .append(c)
        
      if   k == " iri":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        tables    .append("resources")
        conditions.append("resources.storid = q%s.s" % i)
        if "*" in v: conditions.append("resources.iri GLOB ?")
        else:        conditions.append("resources.iri = ?")
        params.append(v)
        
      elif k == " is_a":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("(q%s.p = '%s' OR q%s.p = '%s') AND q%s.o IN (%s)" % (i, rdf_type, i, rdfs_subclassof, i, ",".join("?" for i in v)))
        params    .extend(v)
        
      elif k == " type":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("q%s.p = '%s' AND q%s.o IN (%s)" % (i, rdf_type, i, ",".join("?" for i in v)))
        params    .extend(v)
        
      elif k == " subclass_of":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("q%s.p = '%s' AND q%s.o IN (%s)" % (i, rdfs_subclassof, i, ",".join("?" for i in v)))
        params    .extend(v)
        
      elif isinstance(k, tuple): # Prop with inverse
        if i == 1: # Does not work if it is the FIRST => add a dumb first.
          i += 1
          tables.append("quads q%s" % i)
          if not c is None:
            conditions  .append("q%s.c = ?" % i)
            params      .append(c)
            
        if v.startswith('"*"'):
          cond1 = "q%s.s = q1.s AND q%s.p = ?" % (i, i)
          cond2 = "q%s.o = q1.s AND q%s.p = ?" % (i, i)
          params1 = [k[0]]
          params2 = [k[1]]
        else:
          cond1 = "q%s.s = q1.s AND q%s.p = ? AND q%s.o = ?" % (i, i, i)
          cond2 = "q%s.o = q1.s AND q%s.p = ? AND q%s.s = ?" % (i, i, i)
          params1 = [k[0], v]
          params2 = [k[1], v]
        alternatives.append(((cond1, params1), (cond2, params2)))
        
      else: # Prop without inverse
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        if isinstance(v, FTS):
          fts = self.prop_fts[k]
          tables    .append("fts_%s" % fts)
          conditions.append("q%s.rowid = fts_%s.rowid" % (i, fts))
          conditions.append("fts_%s MATCH ?" % fts)
          params    .append(v)
        else:
          conditions.append("q%s.p = ?" % i)
          params    .append(k)
          if "*" in v:
            if   v.startswith('"*"'):
              conditions.append("q%s.o GLOB '*'" % i)
            else:
              conditions.append("q%s.o GLOB ?" % i)
              params    .append(v)
          else:
            conditions.append("q%s.o = ?" % i)
            params    .append(v)
            
    if alternatives:
      conditions0 = conditions
      params0     = params
      params      = []
      reqs        = []
      for combination in all_combinations(alternatives):
        combination_conditions, combination_paramss = zip(*combination)
        req = "SELECT DISTINCT q1.s from %s WHERE %s" % (", ".join(tables), " AND ".join(conditions0 + list(combination_conditions)))
        reqs.append(req)
        params.extend(params0)
        for combination_params in combination_paramss: params.extend(combination_params)
      req = "SELECT DISTINCT * FROM (\n%s\n)" % "\nUNION\n".join(reqs)
      
    else:
      req = "SELECT DISTINCT q1.s from %s WHERE %s" % (", ".join(tables), " AND ".join(conditions))
      
      
    if excepts:
      conditions = []
      for except_p in excepts:
        if isinstance(except_p, tuple): # Prop with inverse
          conditions.append("quads.s = candidates.s AND quads.p = ?")
          params    .append(except_p[0])
          conditions.append("quads.o = candidates.s AND quads.p = ?")
          params    .append(except_p[1])
        else: # No inverse
          conditions.append("quads.s = candidates.s AND quads.p = ?")
          params    .append(except_p)
          
          
      req = """
WITH candidates(s) AS (%s)
SELECT s FROM candidates
EXCEPT SELECT candidates.s FROM candidates, quads WHERE (%s)""" % (req, ") OR (".join(conditions))
      
    #print(prop_vals)
    #print(req)
    #print(params)

    return self.execute(req, params).fetchall()
  
  def _punned_entities(self):
    from owlready2.base import rdf_type, owl_class, owl_named_individual
    cur = self.execute("SELECT q1.s FROM quads q1, quads q2 WHERE q1.s=q2.s AND q1.p=? AND q2.p=? AND q1.o=? AND q2.o=?", (rdf_type, rdf_type, owl_class, owl_named_individual))
    return [storid for (storid,) in cur.fetchall()]
  
    
  def __bool__(self): return True # Reimplemented to avoid calling __len__ in this case
  def __len__(self):
    return self.execute("SELECT COUNT() FROM quads").fetchone()[0]

  
  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_sp(self, s, p):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT o FROM quads WHERE s=? AND p=?
UNION ALL SELECT quads.o FROM quads, transit WHERE quads.s=transit.x AND quads.p=?)
SELECT DISTINCT x FROM transit""", (s, p, p)).fetchall(): yield x

  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_po(self, p, o):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT s FROM quads WHERE p=? AND o=?
UNION ALL SELECT quads.s FROM quads, transit WHERE quads.p=? AND quads.o=transit.x)
SELECT DISTINCT x FROM transit""", (p, o, p)).fetchall(): yield x

# Slower than Python implementation
#  def get_transitive_sym2(self, s, p):
#    r = { s }
#    for (s, o) in self.execute("""
#WITH RECURSIVE transit(s,o)
#AS (  SELECT s,o from quads WHERE (s=? OR o=?) AND (p=?)
#    UNION SELECT quads.s,quads.o FROM quads, transit WHERE (quads.s=transit.s OR quads.o=transit.o OR quads.s=transit.o OR quads.o=transit.s) AND quads.p=?)
#SELECT s, o FROM transit""", (s, s, p, p)):
#      r.add(s)
#      r.add(o)
#    yield from r
    

  def _destroy_collect_storids(self, destroyed_storids, modified_relations, storid):
    for (blank_using,) in list(self.execute("""SELECT s FROM quads WHERE o=? AND p IN (
    '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s') AND substr(s, 1, 1)='_'""" % (
      SOME,
      ONLY,
      VALUE,
      owl_onclass,
      owl_onproperty,
      owl_complementof,
      owl_inverse_property,
      owl_ondatarange,
      owl_annotatedsource,
      owl_annotatedproperty,
      owl_annotatedtarget,
    ), (storid,))):
      if not blank_using in destroyed_storids:
        destroyed_storids.add(blank_using)
        self._destroy_collect_storids(destroyed_storids, modified_relations, blank_using)
        
    for (c, blank_using) in list(self.execute("""SELECT c, s FROM quads WHERE o=? AND p='%s' AND substr(s, 1, 1)='_'""" % (
      rdf_first,
    ), (storid,))):
      list_user, root, previouss, nexts, length = self._rdf_list_analyze(blank_using)
      destroyed_storids.update(previouss)
      destroyed_storids.add   (blank_using)
      destroyed_storids.update(nexts)
      if not list_user in destroyed_storids:
        destroyed_storids.add(list_user)
        self._destroy_collect_storids(destroyed_storids, modified_relations, list_user)
        
  def _rdf_list_analyze(self, blank):
    previouss = []
    nexts     = []
    length    = 1
    #b         = next_ = self.get_triple_sp(blank, rdf_rest)
    b         = self.get_triple_sp(blank, rdf_rest)
    while b != rdf_nil:
      nexts.append(b)
      length += 1
      b       = self.get_triple_sp(b, rdf_rest)
      
    b         = self.get_triple_po(rdf_rest, blank)
    if b:
      while b:
        previouss.append(b)
        length += 1
        root    = b
        b       = self.get_triple_po(rdf_rest, b)
    else:
      root = blank
      
    list_user = self.execute("SELECT s FROM quads WHERE o=? LIMIT 1", (root,)).fetchone()
    if list_user: list_user = list_user[0]
    return list_user, root, previouss, nexts, length
  
  def destroy_entity(self, storid, destroyer, relation_updater):
    destroyed_storids   = { storid }
    modified_relations  = defaultdict(set)
    self._destroy_collect_storids(destroyed_storids, modified_relations, storid)
    
    for s,p in self.execute("SELECT DISTINCT s,p FROM quads WHERE o IN (%s)" % ",".join(["?" for i in destroyed_storids]), tuple(destroyed_storids)):
      if not s in destroyed_storids:
        modified_relations[s].add(p)
        
    # Two separate loops because high level destruction must be ended before removing from the quadstore (high level may need the quadstore)
    for storid in destroyed_storids:
      destroyer(storid)
      
    for storid in destroyed_storids:
      #self.execute("SELECT s,p,o FROM quads WHERE s=? OR o=?", (self.c, storid, storid))
      self.execute("DELETE FROM quads WHERE s=? OR o=?", (storid, storid))
      
    for s, ps in modified_relations.items():
      relation_updater(destroyed_storids, s, ps)
      
    return destroyed_storids
  
  def _iter_ontology_iri(self, c = None):
    if c:
      return self.execute("SELECT iri FROM ontologies WHERE c=?", (c,)).fetchone()[0]
    else:
      return self.execute("SELECT c, iri FROM ontologies").fetchall()
    
  def _iter_triples(self, quads = False, sort_by_s = False):
    cursor = self.db.cursor() # Use a new cursor => can iterate without laoding all data in a big list, while still being able to query the default cursor
    if quads:
      if sort_by_s: cursor.execute("SELECT c,s,p,o FROM quads ORDER BY s")
      else:         cursor.execute("SELECT c,s,p,o FROM quads")
    else:
      if sort_by_s: cursor.execute("SELECT s,p,o FROM quads ORDER BY s")
      else:         cursor.execute("SELECT s,p,o FROM quads")
    return cursor
  
  
  def get_fts_prop_storid(self): return self.prop_fts.keys()
  
  def enable_full_text_search(self, prop_storid):
    fts = 1
    while True:
      if not self.execute("""SELECT storid FROM prop_fts WHERE fts=?""", (str(fts),)).fetchall():
        fts = str(fts)
        break
      fts += 1
      
    self.prop_fts[prop_storid] = fts # = str(len(self.prop_fts) + 1)
    
    self.execute("""INSERT INTO prop_fts VALUES (?, ?)""", (fts, prop_storid));
    
    self.execute("""CREATE VIRTUAL TABLE fts_%s USING fts5(o, content=quads, content_rowid=rowid)""" % fts)
    self.execute("""INSERT INTO fts_%s(rowid, o) SELECT rowid, SUBSTR(o, 2, LENGTH(o) - 2) FROM quads WHERE p='%s'""" % (fts, prop_storid))
    
    self.db.cursor().executescript("""
CREATE TRIGGER fts_%s_after_insert AFTER INSERT ON quads BEGIN
  INSERT INTO fts_%s(rowid, o) VALUES (new.rowid, new.o);
END;
CREATE TRIGGER fts_%s_after_delete AFTER DELETE ON quads BEGIN
  INSERT INTO fts_%s(fts_%s, rowid, o) VALUES('delete', old.rowid, old.o);
END;
CREATE TRIGGER fts_%s_after_update AFTER UPDATE ON quads BEGIN
  INSERT INTO fts_%s(fts_%s, rowid, o) VALUES('delete', new.rowid, SUBSTR(new.o, 2, LENGTH(new.o) - 2));
  INSERT INTO fts_%s(rowid, o) VALUES (new.rowid, new.o);
END;""" % (fts, fts,   fts, fts, fts,   fts, fts, fts, fts))
  
  def disable_full_text_search(self, prop_storid):
    if not isinstance(prop_storid, str): prop_storid = prop_storid.storid
    fts = self.prop_fts[prop_storid]
    del self.prop_fts[prop_storid]
    
    self.execute("""DELETE FROM prop_fts WHERE fts = ?""", (fts,));
    self.execute("""DROP TABLE fts_%s""" % fts)
    self.execute("""DROP TRIGGER fts_%s_after_insert""" % fts)
    self.execute("""DROP TRIGGER fts_%s_after_delete""" % fts)
    self.execute("""DROP TRIGGER fts_%s_after_update""" % fts)
    
    
class SubGraph(BaseSubGraph):
  def __init__(self, parent, onto, c, db):
    BaseSubGraph.__init__(self, parent, onto)
    self.c      = c
    self.db     = db
    self.execute  = db.execute
    self.abbreviate       = parent.abbreviate
    self.unabbreviate     = parent.unabbreviate
    self.new_numbered_iri = parent.new_numbered_iri
    
    self.parent.onto_2_subgraph[onto] = self
    
  def create_parse_func(self, filename = None, delete_existing_triples = True, datatype_attr = "http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype"):
    values       = []
    new_abbrevs  = []
    
    cur = self.db.cursor()
    
    if delete_existing_triples:
      cur.execute("DELETE FROM quads WHERE c=?", (self.c,))
    
    if len(self.parent) < 100000:
      cur.execute("""DROP INDEX index_resources_iri""")
      cur.execute("""DROP INDEX index_quads_s""")
      cur.execute("""DROP INDEX index_quads_o""")
      reindex = True
    else:
      reindex = False
      
      
    # Re-implement abbreviate() for speed
    if self.parent.abbreviate_d is None:
      abbrevs = {}
      def abbreviate(iri):
        storid = abbrevs.get(iri)
        if not storid is None: return storid
        r = cur.execute("SELECT storid FROM resources WHERE iri=? LIMIT 1", (iri,)).fetchone()
        if r:
          abbrevs[iri] = r[0]
          return r[0]
        self.parent.current_resource += 1
        storid = _int_base_62(self.parent.current_resource)
        new_abbrevs.append((storid, iri))
        abbrevs[iri] = storid
        return storid
    else:
      abbrevs = self.parent.abbreviate_d
      def abbreviate(iri):
        storid = abbrevs.get(iri)
        if not storid is None: return storid
        
        self.parent.current_resource += 1
        storid = _int_base_62(self.parent.current_resource)
        new_abbrevs.append((storid, iri))
        abbrevs[iri] = storid
        return storid
      
    def insert_triples():
      nonlocal values, new_abbrevs
      if owlready2.namespace._LOG_LEVEL: print("* OwlReady2 * Importing %s triples from ontology %s ..." % (len(values), self.onto.base_iri), file = sys.stderr)
      cur.executemany("INSERT INTO resources VALUES (?,?)", new_abbrevs)
      cur.executemany("INSERT INTO quads VALUES (%s,?,?,?)" % self.c, values)
      values      *= 0
      new_abbrevs *= 0
      
    try:
      import rdfxml_2_ntriples_pyx
      on_prepare_triple, new_literal = rdfxml_2_ntriples_pyx._create_triplelite_func(abbreviate, values, insert_triples, datatype_attr)
    except:
      def on_prepare_triple(s, p, o):
        if not s.startswith("_"): s = abbreviate(s)
        p = abbreviate(p)
        if not (o.startswith("_") or o.startswith('"')): o = abbreviate(o)
        values.append((s,p,o))
        if len(values) > 1000000: insert_triples()
        
      def new_literal(value, attrs):
        lang = attrs.get("http://www.w3.org/XML/1998/namespacelang")
        if lang: return '"%s"@%s' % (value, lang)
        datatype = attrs.get(datatype_attr)
        if datatype: return '"%s"%s' % (value, abbreviate(datatype))
        return '"%s"' % (value)
      
      
    def on_finish():
      if filename: date = os.path.getmtime(filename)
      else:        date = time.time()
      
      insert_triples()
      
      if reindex:
        cur.execute("""CREATE UNIQUE INDEX index_resources_iri ON resources(iri)""")
        cur.execute("""CREATE INDEX index_quads_s ON quads(s)""")
        cur.execute("""CREATE INDEX index_quads_o ON quads(o)""")
        
      onto_base_iri = cur.execute("SELECT resources.iri FROM quads, resources WHERE quads.c=? AND quads.o=? AND resources.storid=quads.s LIMIT 1", (self.c, owl_ontology)).fetchone()
      if onto_base_iri: onto_base_iri = onto_base_iri[0]
      else:             onto_base_iri = ""
      
      if onto_base_iri.endswith("/"):
        cur.execute("UPDATE ontologies SET last_update=?,iri=? WHERE c=?", (date, onto_base_iri, self.c,))
      elif onto_base_iri:
        onto_base_iri = self.parent.fix_base_iri(onto_base_iri, self.c)
        cur.execute("UPDATE ontologies SET last_update=?,iri=? WHERE c=?", (date, onto_base_iri, self.c,))
      else:
        cur.execute("UPDATE ontologies SET last_update=? WHERE c=?", (date, self.c,))
        
      self.parent.select_abbreviate_method()
      
      return onto_base_iri
    
    
    return on_prepare_triple, self.parent.new_blank_node, new_literal, abbreviate, on_finish


  def context_2_user_context(self, c): return self.parent.c_2_onto[c]
 
  def add_ontology_alias(self, iri, alias):
    self.execute("INSERT into ontology_alias VALUES (?,?)", (iri, alias))
    
  def get_last_update_time(self):
    return self.execute("SELECT last_update FROM ontologies WHERE c=?", (self.c,)).fetchone()[0]
  
  def set_last_update_time(self, t):
    self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (t, self.c))
  
  def destroy(self):
    self.execute("DELETE FROM quads WHERE c=?",      (self.c,))
    self.execute("DELETE FROM ontologies WHERE c=?", (self.c,))
    
  def _set_triple(self, s, p, o):
    if (s is None) or (p is None) or (o is None): raise ValueError
    self.execute("DELETE FROM quads WHERE c=? AND s=? AND p=?", (self.c, s, p,))
    self.execute("INSERT INTO quads VALUES (?, ?, ?, ?)", (self.c, s, p, o))
    
  def _add_triple(self, s, p, o):
    if (s is None) or (p is None) or (o is None): raise ValueError
    self.execute("INSERT INTO quads VALUES (?, ?, ?, ?)", (self.c, s, p, o))
    
  def _del_triple(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: self.execute("DELETE FROM quads WHERE c=?", (self.c,))
        else:         self.execute("DELETE FROM quads WHERE c=? AND o=?", (self.c, o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE c=? AND p=?", (self.c, p,))
        else:         self.execute("DELETE FROM quads WHERE c=? AND p=? AND o=?", (self.c, p, o,))
    else:
      if p is None:
        if o is None: self.execute("DELETE FROM quads WHERE c=? AND s=?", (self.c, s,))
        else:         self.execute("DELETE FROM quads WHERE c=? AND s=? AND o=?", (self.c, s, o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        else:         self.execute("DELETE FROM quads WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o,))
        
  def get_triples(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads WHERE c=?", (self.c,))
        else:         cur = self.execute("SELECT s,p,o FROM quads WHERE c=? AND o=?", (self.c, o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads WHERE c=? AND p=?", (self.c, p,))
        else:         cur = self.execute("SELECT s,p,o FROM quads WHERE c=? AND p=? AND o=?", (self.c, p, o,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=?", (self.c, s,))
        else:         cur = self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=? AND o=?", (self.c, s, o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        else:         cur = self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o,))
    return cur.fetchall()
  
  def get_triples_s(self, s):
    return self.execute("SELECT p,o FROM quads WHERE c=? AND s=?", (self.c, s,)).fetchall()
  
  def get_triples_sp(self, s, p):
    for (x,) in self.execute("SELECT o FROM quads WHERE c=? AND s=? AND p=?", (self.c, s, p,)).fetchall(): yield x
    
  def get_triples_po(self, p, o):
    for (x,) in self.execute("SELECT s FROM quads WHERE c=? AND p=? AND o=?", (self.c, p, o,)).fetchall(): yield x
    
  def get_triple_sp(self, s, p):
    r = self.execute("SELECT o FROM quads WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,)).fetchone()
    if r: return r[0]
    return None
  
  def get_triple_po(self, p, o):
    r = self.execute("SELECT s FROM quads WHERE c=? AND p=? AND o=? LIMIT 1", (self.c, p, o,)).fetchone()
    if r: return r[0]
    return None
  
  def get_pred(self, s):
    for (x,) in self.execute("SELECT DISTINCT p FROM quads WHERE c=? AND s=?", (self.c, s,)).fetchall(): yield x
    
  def has_triple(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM quads WHERE c=? LIMIT 1", (self.c,))
        else:         cur = self.execute("SELECT s FROM quads WHERE c=? AND o=? LIMIT 1", (self.c, o,))
      else:
        if o is None: cur = self.execute("SELECT s FROM quads WHERE c=? AND p=? LIMIT 1", (self.c, p,))
        else:         cur = self.execute("SELECT s FROM quads WHERE c=? AND p=? AND o=? LIMIT 1", (self.c, p, o,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM quads WHERE c=? AND s=? LIMIT 1", (self.c, s,))
        else:         cur = self.execute("SELECT s FROM quads WHERE c=? AND s=? AND o=? LIMIT 1", (self.c, s, o,))
      else:
        if o is None: cur = self.execute("SELECT s FROM quads WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,))
        else:         cur = self.execute("SELECT s FROM quads WHERE c=? AND s=? AND p=? AND o=? LIMIT 1", (self.c, s, p, o,))
    return not cur.fetchone() is None
  
  def get_quads(self, s, p, o, c):
    return [(s, p, o, self.c) for (s, p, o) in self.get_triples(s, p, o)]
  
  def search(self, prop_vals, c = None): return self.parent.search(prop_vals, self.c)
  
  def __len__(self):
    return self.execute("SELECT COUNT() FROM quads WHERE c=?", (self.c,)).fetchone()[0]


  def _iter_ontology_iri(self, c = None):
    if c:
      return self.execute("SELECT iri FROM ontologies WHERE c=?", (c,)).fetchone()[0]
    else:
      return self.execute("SELECT c, iri FROM ontologies").fetchall()
    
  def _iter_triples(self, quads = False, sort_by_s = False):
    cursor = self.db.cursor() # Use a new cursor => can iterate without laoding all data in a big list, while still being able to query the default cursor
    if quads:
      if sort_by_s: cursor.execute("SELECT c,s,p,o FROM quads WHERE c=? ORDER BY s", (self.c,))
      else:         cursor.execute("SELECT c,s,p,o FROM quads WHERE c=?", (self.c,))
    else:
      if sort_by_s: cursor.execute("SELECT s,p,o FROM quads WHERE c=? ORDER BY s", (self.c,))
      else:         cursor.execute("SELECT s,p,o FROM quads WHERE c=?", (self.c,))
    return cursor

  
  
  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_sp(self, s, p):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT o FROM quads WHERE c=? AND s=? AND p=?
UNION ALL SELECT quads.o FROM quads, transit WHERE quads.c=? AND quads.s=transit.x AND quads.p=?)
SELECT DISTINCT x FROM transit""", (self.c, s, p, self.c, p)).fetchall(): yield x
  
  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_po(self, p, o):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT s FROM quads WHERE c=? AND p=? AND o=?
UNION ALL SELECT quads.s FROM quads, transit WHERE quads.c=? AND quads.p=? AND quads.o=transit.x)
SELECT DISTINCT x FROM transit""", (self.c, p, o, self.c, p)).fetchall(): yield x

#  def get_transitive_sym(self, s, p):
#    r = { s }
#    for (s, o) in self.execute("""
#WITH RECURSIVE transit(s,o)
#AS (  SELECT s,o from quads WHERE (s=? OR o=?) AND p=? AND c=?
#    UNION SELECT quads.s,quads.o FROM quads, transit WHERE (quads.s=transit.s OR quads.o=transit.o OR quads.s=transit.o OR quads.o=transit.s) AND quads.p=? AND quads.c=?)
#SELECT s, o FROM transit""", (s, s, p, self.c, p, self.c)):
#      r.add(s)
#      r.add(o)
#    yield from r
