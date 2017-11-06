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

import sys, os, os.path, sqlite3, time, datetime, re, multiprocessing
from functools import lru_cache
from collections import defaultdict

from owlready2.driver import *
from owlready2.util import _int_base_62
from owlready2.base import _universal_abbrev_2_iri

import owlready2.rdfxml_2_ntriples
import owlready2.owlxml_2_ntriples

class Graph(BaseGraph):
  def __init__(self, filename, clone = None):
    exists        = os.path.exists(filename) and os.path.getsize(filename)
    self.db       = sqlite3.connect(filename, check_same_thread = False)
    
    self.db.execute("""PRAGMA locking_mode = EXCLUSIVE""")
    
    self.sql      = self.db.cursor()
    self.execute  = self.sql.execute
    self.fetchone = self.sql.fetchone
    self.fetchall = self.sql.fetchall
    self.c_2_onto          = {}
    self.onto_2_subgraph   = {}
    self.last_numbered_iri = {}
    
    if (clone is None) and ((filename == ":memory:") or (not exists)):
      self.current_blank    = 0
      self.current_resource = 300 # 300 first values are reserved
      
      self.execute("""CREATE TABLE store (version INTEGER, current_blank INTEGER, current_resource INTEGER)""")
      self.execute("""INSERT INTO store VALUES (2, 0, 300)""")
      self.execute("""CREATE TABLE quads (c INTEGER, s TEXT, p TEXT, o TEXT)""")
      self.execute("""CREATE TABLE ontologies (c INTEGER PRIMARY KEY, iri TEXT, last_update DOUBLE)""")
      self.execute("""CREATE TABLE ontology_alias (iri TEXT, alias TEXT)""")
      self.execute("""CREATE TABLE resources (storid TEXT PRIMARY KEY, iri TEXT) WITHOUT ROWID""")
      self.sql.executemany("INSERT INTO resources VALUES (?,?)", _universal_abbrev_2_iri.items())
      #self.execute("""CREATE INDEX index_resources_storid ON resources(storid)""") # Not needed because declared as primary key
      self.execute("""CREATE INDEX index_resources_iri ON resources(iri)""")
      self.execute("""CREATE INDEX index_quads_s ON quads(s)""")
      self.execute("""CREATE INDEX index_quads_o ON quads(o)""")
      self.db.commit()
      
    else:
      if clone:
        s = "\n".join(clone.db.iterdump())
        self.sql.executescript(s)
        
      self.execute("SELECT version, current_blank, current_resource FROM store")
      version, self.current_blank, self.current_resource = self.fetchone()
      if version == 1:
        self.execute("""CREATE TABLE ontology_alias (iri TEXT, alias TEXT)""")
        self.execute("""UPDATE store SET version=2""")
        
        
    self.current_changes = self.db.total_changes

  def ontologies_iris(self):
    self.execute("SELECT iri FROM ontologies")
    for (iri,) in self.fetchall():
      yield iri
      
  def abbreviate(self, iri):
    r = self.execute("SELECT storid FROM resources WHERE iri=? LIMIT 1", (iri,)).fetchone()
    if r: return r[0]
    self.current_resource += 1
    storid = _int_base_62(self.current_resource)
    self.execute("INSERT INTO resources VALUES (?,?)", (storid, iri))
    return storid
  
  def unabbreviate(self, storid):
    return self.execute("SELECT iri FROM resources WHERE storid=? LIMIT 1", (storid,)).fetchone()[0]
  
  def get_storid_dict(self):
    return dict(self.execute("SELECT storid, iri FROM resources").fetchall())
  
  def new_numbered_iri(self, prefix):
    if prefix in self.last_numbered_iri:
      i = self.last_numbered_iri[prefix] = self.last_numbered_iri[prefix] + 1
      return "%s%s" % (prefix, i)
    else:
      self.execute("SELECT iri FROM resources WHERE iri GLOB ? ORDER BY LENGTH(iri) DESC, iri DESC", ("%s*" % prefix,))
      while True:
        iri = self.fetchone()
        if not iri: break
        num = iri[0][len(prefix):]
        if num.isdigit():
          self.last_numbered_iri[prefix] = i = int(num) + 1
          return "%s%s" % (prefix, i)
        
    self.last_numbered_iri[prefix] = 1
    return "%s1" % prefix
  
  def refactor(self, storid, new_iri):
    self.execute("UPDATE resources SET iri=? WHERE storid=?", (new_iri, storid,))
    
  def sub_graph(self, onto):
    new_in_quadstore = False
    self.execute("SELECT c FROM ontologies WHERE iri=?", (onto.base_iri,))
    c = self.fetchone()
    if c is None:
      self.execute("SELECT ontologies.c FROM ontologies, ontology_alias WHERE ontology_alias.alias=? AND ontologies.iri=ontology_alias.iri", (onto.base_iri,))
      c = self.fetchone()
      if c is None:
        new_in_quadstore = True
        self.execute("INSERT INTO ontologies VALUES (NULL, ?, 0)", (onto.base_iri,))
        self.execute("SELECT c FROM ontologies WHERE iri=?", (onto.base_iri,))
        c = self.fetchone()
    c = c[0]
    self.c_2_onto[c] = onto
    
    return SubGraph(self, onto, c, self.db, self.sql), new_in_quadstore
  
  def context_2_user_context(self, c): return self.c_2_onto[c]
  
  def parse(self, f): raise NotImplementedError
  
  def save(self, f, format = "rdfxml", **kargs):
    _save(f, format, self, **kargs)
    
  def new_blank_node(self):
    self.current_blank += 1
    return "_%s" % _int_base_62(self.current_blank)
  
  def commit(self):
    if self.current_changes != self.db.total_changes:
      self.current_changes = self.db.total_changes
      self.execute("UPDATE store SET current_blank=?, current_resource=?", (self.current_blank, self.current_resource))
      self.db.commit()
      
  def get_triples(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: self.execute("SELECT s,p,o FROM quads")
        else:         self.execute("SELECT s,p,o FROM quads WHERE o=?", (o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE p=?", (p,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE p=? AND o=?", (p, o,))
    else:
      if p is None:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE s=?", (s,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE s=? AND o=?", (s, o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE s=? AND p=?", (s, p,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE s=? AND p=? AND o=?", (s, p, o,))
    return self.fetchall()
    
  def get_quads(self, s, p, o, c):
    if c is None:
      if s is None:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads")
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE o=?", (o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE p=?", (p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE p=? AND o=?", (p, o,))
      else:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE s=?", (s,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE s=? AND o=?", (s, o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE s=? AND p=?", (s, p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE s=? AND p=? AND o=?", (s, p, o,))
    else:
      if s is None:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=?", (c,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND o=?", (c, o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND p=?", (c, p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND p=? AND o=?", (c, p, o,))
      else:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=?", (c, s,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=? AND o=?", (c, s, o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=? AND p=?", (c, s, p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=? AND s=? AND p=? AND o=?", (c, s, p, o,))
    return self.fetchall()
  
  def get_quads_sp(self, s, p):
    return self.execute("SELECT o,c FROM quads WHERE s=? AND p=?", (s, p,)).fetchall()
  
  def get_pred(self, s):
    for (x,) in self.execute("SELECT DISTINCT p FROM quads WHERE s=?", (s,)).fetchall(): yield x
    
  def get_triples_s(self, s):
    return self.execute("SELECT p,o FROM quads WHERE s=?", (s,)).fetchall()
  
  def get_triples_sp(self, s, p):
    for (x,) in self.execute("SELECT o FROM quads WHERE s=? AND p=?", (s, p,)).fetchall(): yield x
    
  def get_triples_po(self, p, o):
    for (x,) in self.execute("SELECT s FROM quads WHERE p=? AND o=?", (p, o,)).fetchall(): yield x
    
  def get_triple_sp(self, s = None, p = None):
    r = self.execute("SELECT o FROM quads WHERE s=? AND p=? LIMIT 1", (s, p,)).fetchone()
    if r: return r[0]
    return None
  
  def get_triple_po(self, p = None, o = None):
    r = self.execute("SELECT s FROM quads WHERE p=? AND o=? LIMIT 1", (p, o,)).fetchone()
    if r: return r[0]
    return None
  
#   def get_transitive_po(self, p, o):
#     for (x,) in self.execute("""
# WITH RECURSIVE transit(x)
# AS (      SELECT ?
# UNION ALL SELECT quads.s FROM quads, transit WHERE quads.p=? AND quads.o=transit.x)
# SELECT DISTINCT x FROM transit""", (o, p)).fetchall(): yield x
  
#   def get_transitive_sp(self, s, p):
#     for (x,) in self.execute("""
# WITH RECURSIVE transit(x)
# AS (      SELECT ?
# UNION ALL SELECT quads.o FROM quads, transit WHERE quads.s=transit.x AND quads.p=?)
# SELECT DISTINCT x FROM transit""", (s, p)).fetchall(): yield x

  def get_transitive_sp(self, s, p):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT o FROM quads WHERE s=? AND p=?
UNION ALL SELECT quads.o FROM quads, transit WHERE quads.s=transit.x AND quads.p=?)
SELECT DISTINCT x FROM transit""", (s, p, p)).fetchall(): yield x

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
    
    
  def has_triple(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads LIMIT 1")
        else:         self.execute("SELECT s FROM quads WHERE o=? LIMIT 1", (o,))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE p=? LIMIT 1", (p,))
        else:         self.execute("SELECT s FROM quads WHERE p=? AND o=? LIMIT 1", (p, o,))
    else:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads WHERE s=? LIMIT 1", (s,))
        else:         self.execute("SELECT s FROM quads WHERE s=? AND o=? LIMIT 1", (s, o,))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE s=? AND p=? LIMIT 1", (s, p,))
        else:         self.execute("SELECT s FROM quads WHERE s=? AND p=? AND o=? LIMIT 1", (s, p, o,))
    return not self.fetchone() is None
  
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
    tables     = []
    conditions = []
    params     = []
    excepts    = []
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
        
      if   k == "iri":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        tables    .append("resources")
        conditions.append("resources.storid = q%s.s" % i)
        if "*" in v: conditions.append("resources.iri GLOB ?")
        else:        conditions.append("resources.iri = ?")
        params.append(v)
        
      elif k == "is_a":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("(q%s.p = '%s' OR q%s.p = '%s') AND q%s.o IN (%s)" % (i, rdf_type, i, rdfs_subclassof, i, ",".join("?" for i in v)))
        params    .extend(v)
        
      elif k == "type":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("q%s.p = '%s' AND q%s.o IN (%s)" % (i, rdf_type, i, ",".join("?" for i in v)))
        params    .extend(v)
        
      elif k == "subclass_of":
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
          params.extend([k[0], k[1]])
        else:
          cond1 = "q%s.s = q1.s AND q%s.p = ? AND q%s.o = ?" % (i, i, i)
          cond2 = "q%s.o = q1.s AND q%s.p = ? AND q%s.s = ?" % (i, i, i)
          params.extend([k[0], v, k[1], v])
        conditions  .append("((%s) OR (%s))" % (cond1, cond2))
        
      else: # Prop without inverse
        if i > 1: conditions.append("q%s.s = q1.s" % i)
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

    #print(req)
    #print(params)
      
    self.execute(req, params)
    return self.fetchall()

  def _punned_entities(self):
    from owlready2.base import rdf_type, owl_class, owl_named_individual
    self.execute("SELECT q1.s FROM quads q1, quads q2 WHERE q1.s=q2.s AND q1.p=? AND q2.p=? AND q1.o=? AND q2.o=?", (rdf_type, rdf_type, owl_class, owl_named_individual))
    return [storid for (storid,) in self.fetchall()]
  
  def __len__(self):
    return self.execute("SELECT COUNT() FROM quads").fetchone()[0]

  def dump(self):
    import io
    s = io.BytesIO()
    self.save(s, "ntriples")
    print(s.getvalue().decode("utf8"))
    
    
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
        
    for (c, blank_using) in list(self.execute("""SELECT c, s FROM quads WHERE o=? AND p=%s AND substr(s, 1, 1)='_'""" % (
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
      
    self.execute("SELECT s FROM quads WHERE o=? LIMIT 1", (root,))
    list_user = self.fetchone()
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
  
  
class SubGraph(BaseGraph):
  def __init__(self, parent, onto, c, db, sql):
    self.parent = parent
    self.onto   = onto
    self.c      = c
    self.db     = db
    self.sql    = sql
    self.execute  = self.sql.execute
    self.fetchone = self.sql.fetchone
    self.fetchall = self.sql.fetchall
    self.abbreviate       = parent.abbreviate
    self.unabbreviate     = parent.unabbreviate
    self.new_numbered_iri = parent.new_numbered_iri
    
    self.parent.onto_2_subgraph[onto] = self
    
  def context_2_user_context(self, c): return self.parent.c_2_onto[c]
  

  def create_parse_func(self, filename = None, delete_existing_triples = True, datatype_attr = "http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype"):
    values       = []
    abbrevs      = {}
    new_abbrevs  = []
    def abbreviate(iri): # Re-implement for speed
      storid = abbrevs.get(iri)
      if not storid is None: return storid
      r = self.execute("SELECT storid FROM resources WHERE iri=? LIMIT 1", (iri,)).fetchone()
      if r:
        abbrevs[iri] = r[0]
        return r[0]
      self.parent.current_resource += 1
      storid = _int_base_62(self.parent.current_resource)
      new_abbrevs.append((storid, iri))
      abbrevs[iri] = storid
      return storid
    
    def on_prepare_triple(s, p, o):
      if not s.startswith("_"): s = abbreviate(s)
      p = abbreviate(p)
      if not (o.startswith("_") or o.startswith('"')): o = abbreviate(o)
      
      values.append((s,p,o))
      
    def new_literal(value, attrs):
      lang = attrs.get("http://www.w3.org/XML/1998/namespacelang")
      if lang: return '"%s"@%s' % (value, lang)
      datatype = attrs.get(datatype_attr)
      if datatype: return '"%s"%s' % (value, abbreviate(datatype))
      return '"%s"' % (value)
    
    def on_finish():
      if filename: date = os.path.getmtime(filename)
      else:        date = time.time()
      
      if delete_existing_triples: self.execute("DELETE FROM quads WHERE c=?", (self.c,))
      
      if len(self.parent) < 100000:
        self.execute("""DROP INDEX index_resources_iri""")
        self.execute("""DROP INDEX index_quads_s""")
        self.execute("""DROP INDEX index_quads_o""")
        reindex = True
      else:
        reindex = False
        
      if owlready2.namespace._LOG_LEVEL: print("* OwlReady2 * Importing %s triples from ontology %s ..." % (len(values), self.onto.base_iri), file = sys.stderr)
      self.sql.executemany("INSERT INTO resources VALUES (?,?)", new_abbrevs)
      self.sql.executemany("INSERT INTO quads VALUES (%s,?,?,?)" % self.c, values)
      
      if reindex:
        self.execute("""CREATE INDEX index_resources_iri ON resources(iri)""")
        self.execute("""CREATE INDEX index_quads_s ON quads(s)""")
        self.execute("""CREATE INDEX index_quads_o ON quads(o)""")
        
      
      onto_base_iri = self.execute("SELECT resources.iri FROM quads, resources WHERE quads.c=? AND quads.o=? AND resources.storid=quads.s LIMIT 1", (self.c, owl_ontology)).fetchone()
      
      if onto_base_iri:
        onto_base_iri = onto_base_iri[0]
        use_hash = self.execute("SELECT resources.iri FROM quads, resources WHERE quads.c=? AND resources.storid=quads.s AND resources.iri LIKE ? LIMIT 1", (self.c, onto_base_iri + "#%")).fetchone()
        if use_hash: onto_base_iri = onto_base_iri + "#"
        else:
          use_slash = self.execute("SELECT resources.iri FROM quads, resources WHERE quads.c=? AND resources.storid=quads.s AND resources.iri LIKE ? LIMIT 1", (self.c, onto_base_iri + "/%")).fetchone()
          if use_slash: onto_base_iri = onto_base_iri + "/"
          else:         onto_base_iri = onto_base_iri + "#"
        self.execute("UPDATE ontologies SET last_update=?,iri=? WHERE c=?", (date, onto_base_iri, self.c,))
      else:
        self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (date, self.c,))
        
      return onto_base_iri
      
    return on_prepare_triple, self.parent.new_blank_node, new_literal, abbreviate, on_finish
  
  
  def parse(self, f, format = None, delete_existing_triples = True, default_base = ""):
    format = format or _guess_format(f)
    
    if   format == "ntriples":
      on_prepare_triple, new_blank, new_literal, abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples)
      
      try:
        splitter = re.compile("\s")
        bn_src_2_sql = {}
        
        line = f.readline().decode("utf8")
        current_line = 0
        while line:
          current_line += 1
          if not line.startswith("#"):
            s,p,o = splitter.split(line[:-3], 2)
            
            if   s.startswith("<"): s = s[1:-1]
            elif s.startswith("_"):
              bn = bn_src_2_sql.get(s)
              if bn is None: bn = bn_src_2_sql[s] = new_blank()
              s = bn
              
            p = p[1:-1]
            
            if   o.startswith("<"): o = o[1:-1]
            elif o.startswith("_"):
              bn = bn_src_2_sql.get(o)
              if bn is None: bn = bn_src_2_sql[o] = new_blank()
              o = bn
            elif o.startswith('"'):
              v, l = o.rsplit('"', 1)
              v = v[1:].encode("raw-unicode-escape").decode("unicode-escape")
              if   l.startswith("^"): o = new_literal(v, { "http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype" : l[3:-1] })
              elif l.startswith("@"): o = new_literal(v, { "http://www.w3.org/XML/1998/namespacelang" : l[1:] })
              else:                   o = new_literal(v, {})
              
            on_prepare_triple(s, p, o)
            
          line = f.readline().decode("utf8")
          
        onto_base_iri = on_finish()
        
      except Exception as e:
        raise OwlReadyOntologyParsingError("NTriples parsing error in file %s, line %s." % (getattr(f, "name", "???"), current_line)) from e
      
    elif format == "rdfxml":
      on_prepare_triple, new_blank, new_literal, abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples)
      owlready2.rdfxml_2_ntriples.parse(f, None, on_prepare_triple, new_blank, new_literal, default_base)
      onto_base_iri = on_finish()
      
    elif format == "owlxml":
      on_prepare_triple, new_blank, new_literal, abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples, "datatypeIRI")
      owlready2.owlxml_2_ntriples.parse(f, None, on_prepare_triple, new_blank, new_literal)
      onto_base_iri = on_finish()
      
    else:
      raise ValueError("Unsupported format %s." % format)
    
    return onto_base_iri
      


  def add_ontology_alias(self, iri, alias):
    self.execute("INSERT into ontology_alias VALUES (?,?)", (iri, alias))

  def get_last_update_time(self):
    return self.execute("SELECT last_update FROM ontologies WHERE c=?", (self.c,)).fetchone()[0]
  
  def save(self, f, format = "rdfxml", **kargs):
    self.parent.commit()
    _save(f, format, self, self.c, **kargs)
    
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
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=?", (self.c,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=? AND o=?", (self.c, o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=? AND p=?", (self.c, p,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=? AND p=? AND o=?", (self.c, p, o,))
    else:
      if p is None:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=?", (self.c, s,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=? AND o=?", (self.c, s, o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o,))
    return self.fetchall()
  
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
  
#   def get_transitive_po(self, p, o):
#     for (x,) in self.execute("""
# WITH RECURSIVE transit(x)
# AS (      SELECT ?
# UNION ALL SELECT quads.s FROM quads, transit WHERE quads.c=? AND quads.p=? AND quads.o=transit.x)
# SELECT DISTINCT x FROM transit""", (o, c, p)).fetchall(): yield x
  
#   def get_transitive_sp(self, s, p):
#     for (x,) in self.execute("""
# WITH RECURSIVE transit(x)
# AS (      SELECT ?
# UNION ALL SELECT quads.o FROM quads, transit WHERE quads.c=? AND quads.s=transit.x AND quads.p=?)
# SELECT DISTINCT x FROM transit""", (s, c, p)).fetchall(): yield x
  
  def get_transitive_sp(self, s, p):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT o FROM quads WHERE c=? AND s=? AND p=?
UNION ALL SELECT quads.o FROM quads, transit WHERE quads.c=? AND quads.s=transit.x AND quads.p=?)
SELECT DISTINCT x FROM transit""", (self.c, s, p, self.c, p)).fetchall(): yield x
  
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
    
  def get_pred(self, s):
    for (x,) in self.execute("SELECT DISTINCT p FROM quads WHERE c=? AND s=?", (self.c, s,)).fetchall(): yield x
    
  def has_triple(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads WHERE c=? LIMIT 1", (self.c,))
        else:         self.execute("SELECT s FROM quads WHERE c=? AND o=? LIMIT 1", (self.c, o,))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE c=? AND p=? LIMIT 1", (self.c, p,))
        else:         self.execute("SELECT s FROM quads WHERE c=? AND p=? AND o=? LIMIT 1", (self.c, p, o,))
    else:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads WHERE c=? AND s=? LIMIT 1", (self.c, s,))
        else:         self.execute("SELECT s FROM quads WHERE c=? AND s=? AND o=? LIMIT 1", (self.c, s, o,))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,))
        else:         self.execute("SELECT s FROM quads WHERE c=? AND s=? AND p=? AND o=? LIMIT 1", (self.c, s, p, o,))
    return not self.fetchone() is None
  
  def get_quads(self, s, p, o, c):
    return [(s, p, o, self.c) for (s, p, o) in self.get_triples(s, p, o)]
  
  def search(self, prop_vals, c = None): return self.parent.search(prop_vals, self.c)
  
  def __len__(self):
    return self.execute("SELECT COUNT() FROM quads WHERE c=?", (self.c,)).fetchone()[0]

  def dump(self):
    import io
    s = io.BytesIO()
    self.save(s, "ntriples")
    print(s.getvalue().decode("utf8"))
  
  
def _save(f, format, graph, c = None):
  if   format == "ntriples":
    unabbreviate = lru_cache(None)(graph.unabbreviate)
    
    if c is None: graph.sql.execute("SELECT s,p,o FROM quads")
    else:         graph.sql.execute("SELECT s,p,o FROM quads WHERE c=?", (c,))
    for s,p,o in graph.sql.fetchall():
      if   s.startswith("_"): s = "_:%s" % s[1:]
      else:                   s = "<%s>" % unabbreviate(s)
      p = "<%s>" % unabbreviate(p)
      if   o.startswith("_"): o = "_:%s" % o[1:]
      elif o.startswith('"'):
        v, l = o.rsplit('"', 1)
        v = v[1:].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        if   l.startswith("@"): o = '"%s"%s' % (v, l)
        elif l:                 o = '"%s"^^<%s>' % (v, unabbreviate(l)) # Unabbreviate datatype's iri
        else:                   o = '"%s"' % v
        
      else: o = "<%s>" % unabbreviate(o)
      f.write(("%s %s %s .\n" % (s, p, o)).encode("utf8"))
      
  elif format == "rdfxml":
    @lru_cache(None)
    def unabbreviate(storid):
      return graph.unabbreviate(storid).replace("&", "&amp;")
    
    base_iri = graph.sql.execute("SELECT iri FROM ontologies WHERE c=?", (c,)).fetchone()[0]
    
    #dup_blanks = { bn for (bn,) in graph.sql.execute("SELECT o FROM quads WHERE c=? AND substr(o, 1, 1)='_' GROUP BY o HAVING COUNT(o) > 1", (c,)) }
    
    if c is None: graph.sql.execute("SELECT s,p,o FROM quads ORDER BY s")
    else:         graph.sql.execute("SELECT s,p,o FROM quads WHERE c=? ORDER BY s", (c,))
    
    xmlns = {
      base_iri[:-1] : "",
      base_iri : "#",
      "http://www.w3.org/1999/02/22-rdf-syntax-ns#" : "rdf:",
      "http://www.w3.org/2001/XMLSchema#" : "xsd:",
      "http://www.w3.org/2000/01/rdf-schema#" : "rdfs:",
      "http://www.w3.org/2002/07/owl#" : "owl:",
    }
    xmlns_abbbrevs = set(xmlns.values())
    @lru_cache(None)
    def abbrev(x):
      splitted   = x.rsplit("#", 1)
      splitted_s = x.rsplit("/", 1)
      if   (len(splitted  ) == 2) and (len(splitted[1]) < len(splitted_s[1])):
        left = splitted[0] + "#"
      elif (len(splitted_s) == 2):
        splitted = splitted_s
        left = splitted[0] + "/"
      else: return x
      
      #splitted = x.rsplit("#", 1)
      #if len(splitted) == 2: left = splitted[0] + "#"
      #else:
      #  splitted = x.rsplit("/", 1)
      #  if len(splitted) == 1: return x
      #  left = splitted[0] + "/"
      xmln = xmlns.get(left)
      if not xmln:
        xmln0 = splitted[0].rsplit("/", 1)[1][:4]
        if not xmln0[0] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ": xmln0 = "x_" + xmln0
        xmln  = xmln0 + ":"
        i = 2
        while xmln in xmlns_abbbrevs:  xmln = "%s%s:" % (xmln0, i) ; i += 1
          
        #print("NEW XMLN", left, xmln0, xmln, "   ", x, xmlns_abbbrevs)
        xmlns[left] = xmln = xmln
        xmlns_abbbrevs.add(xmln)
        
      return xmln + splitted[1]
    
    lines  = []
    liness = {}
    for type in [
        "owl:Ontology",
        "owl:ObjectProperty",
        "owl:DataProperty",
        "owl:AnnotationProperty",
        "owl:AllDisjointProperties",
        "owl:Class",
        "owl:AllDisjointClasses",
        "owl:NamedIndividual",
        "owl:AllDifferent",
        "", ]:
      liness[type] = l = []
      lines.append(l)
    
    bn_2_inner_list = defaultdict(list)
    inner_lists_used = set()
    
    tags_with_list = {
      "owl:intersectionOf",
      "owl:unionOf",
      "owl:members",
      "owl:distinctMembers",
      }
    bad_types = {
      "rdf:Description",
      "owl:FunctionalProperty",
      "owl:InverseFunctionalProperty",
      "owl:TransitiveProperty",
      "owl:SymmetricProperty",
      "owl:ReflexiveProperty",
      "owl:IrreflexiveProperty",
      "owl:NamedIndividual",
      }
    
    def parse_list(bn):
      inner_lists_used.add(id(bn_2_inner_list[bn]))
      while bn and (bn != rdf_nil):
        first = graph.get_triple_sp(bn, rdf_first)
        if first != rdf_nil: yield first
        bn = graph.get_triple_sp(bn, rdf_rest)
        
    def purge():
      nonlocal s_lines, current_s, type
      
      #if current_s.startswith("_") and (not current_s in dup_blanks):
      if current_s.startswith("_"):
        l = bn_2_inner_list[current_s]
        current_s = ""
      else:
        l = liness.get(type) or lines[-1]
        
      if s_lines:
        if current_s.startswith("_"):
          l.append("""<%s rdf:nodeID="%s">""" % (type, current_s))
          
        elif current_s:
          current_s = unabbreviate(current_s)
          if current_s.startswith(base_iri): current_s = current_s[len(base_iri)-1 :]
          l.append("""<%s rdf:about="%s">""" % (type, current_s))
          
        else:
          l.append("""<%s>""" % type)
          
        l.extend(s_lines)
        s_lines = []
        
        l.append("""</%s>""" % type)
        
      else:
        if current_s.startswith("_"):
          l.append("""<%s rdf:nodeID="%s"/>""" % (type, current_s))
          
        elif current_s:
          current_s = unabbreviate(current_s)
          if current_s.startswith(base_iri): current_s = current_s[len(base_iri)-1 :]
          l.append("""<%s rdf:about="%s"/>""" % (type, current_s))
          
        else:
          l.append("""<%s/>""" % type)

      if current_s: l.append("")
      
      
    type      = "rdf:Description"
    s_lines   = []
    current_s = ""
    for s,p,o in graph.sql.fetchall():
      if s != current_s:
        if current_s: purge()
        current_s = s
        type = "rdf:Description"
        
      if (p == rdf_type) and (type == "rdf:Description") and (not o.startswith("_")):
        t = abbrev(unabbreviate(o))
        if not t in bad_types:
          type = t
          if type.startswith("#"): type = type[1:]
          continue
        
      p = abbrev(unabbreviate(p))
      if p.startswith("#"): p = p[1:]
      
      if   o.startswith('"'):
        v, l = o.rsplit('"', 1)
        v = v[1:].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if   l.startswith("@"): s_lines.append("""  <%s xml:lang="%s">%s</%s>""" % (p, l[1:], v, p))
        elif l:                 s_lines.append("""  <%s rdf:datatype="%s">%s</%s>""" % (p, unabbreviate(l), v, p))
        else:                   s_lines.append("""  <%s>%s</%s>""" % (p, v, p))
        
      elif o.startswith('_'):
        #if o in dup_blanks:
        #  s_lines.append("""  <%s rdf:nodeID="%s"/>""" % (p, o))
        #  
        #else:
          if p in tags_with_list:
            s_lines.append("""  <%s rdf:parseType="Collection">""" % p)
            for i in parse_list(o):
              if i.startswith("_"):
                l = bn_2_inner_list[i]
                inner_lists_used.add(id(l))
                s_lines.append(l)
              elif i.startswith('"'):
                pass
              else:
                i = unabbreviate(i)
                if i.startswith(base_iri): i = i[len(base_iri)-1 :]
                s_lines.append("""    <rdf:Description rdf:about="%s"/>""" % i)
          else:
            l = bn_2_inner_list[o]
            inner_lists_used.add(id(l))
            s_lines.append("""  <%s>""" % p)
            s_lines.append(l)
          s_lines.append("""  </%s>""" % p)
          
      else:
        o = unabbreviate(o)
        if o.startswith(base_iri): o = o[len(base_iri)-1 :]
        s_lines.append("""  <%s rdf:resource="%s"/>""" % (p, o))
        
    purge()
    
    lines.append([])
    for l in bn_2_inner_list.values():
      if not id(l) in inner_lists_used:
        lines[-1].extend(l)
        lines[-1].append("")
        
    def flatten(l, deep = ""):
      for i in l:
        if isinstance(i, list): yield from flatten(i, deep + "    ")
        else:                   yield deep + i
        
    decls = []
    for iri, abbrev in xmlns.items():
      if   abbrev == "":  decls.append('xml:base="%s"' % iri)
      elif abbrev == "#": decls.append('xmlns="%s"' % iri)
      else:               decls.append('xmlns:%s="%s"' % (abbrev[:-1], iri))
      
    f.write(b"""<?xml version="1.0"?>\n""")
    f.write(("""<rdf:RDF %s>\n\n""" % "\n         ".join(decls)).encode("utf8"))
    f.write( """\n""".join(flatten(sum(lines, []))).encode("utf8"))
    f.write(b"""\n\n</rdf:RDF>\n""")
    
    
def _guess_format(f):
  if f.seekable():
    s = f.read(1000)
    f.seek(0)
  else:
    s = f.peek(1000).lstrip()

  if isinstance(s, str): s = s.encode("utf8")
  
  if not s.startswith(b"<"): return "ntriples"
  if s[s.find(b"\n") -1] == b".": return "ntriples"
  if s.split(b"\n", 1)[0].endswith(b"."): return "ntriples"
  
  if (b"<!DOCTYPE Ontology" in s) or (b"<!DOCTYPE owl:Ontology" in s) or (b"<Ontology xmlns=" in s): return "owlxml"
  
  return "rdfxml"

