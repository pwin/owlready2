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

import sys, os, os.path, psycopg2, time, re
#from psycopg2.extras import execute_batch
from collections import defaultdict
from io import StringIO

import owlready2
from owlready2.base import *
from owlready2.driver import BaseMainGraph, BaseSubGraph
from owlready2.driver import _guess_format, _save
from owlready2.util import _int_base_62
from owlready2.base import _universal_abbrev_2_iri

DEFAULT_WORK_MEM = "64MB"
HIGH_WORK_MEM = "1GB"

class Graph(BaseMainGraph):
  _SUPPORT_CLONING = False
  def __init__(self, dbname = "owlready2_quadstore", new = False, clone = None, world = None, **kargs):
    #try:
    self.db = psycopg2.connect(dbname = dbname, **kargs)
    #except psycopg2.OperationalError:

    self.db.set_session(deferrable = True)
    
    self.cursor   = self.db.cursor
    self.sql      = self.db.cursor()
    self.execute  = self.sql.execute
    self.fetchone = self.sql.fetchone
    self.fetchall = self.sql.fetchall
    self.c_2_onto          = {}
    self.onto_2_subgraph   = {}
    self.last_numbered_iri = {}
    self.c                 = None
    
    self.sql.execute("""set maintenance_work_mem = %s""", (DEFAULT_WORK_MEM,))
    
    initialize_db = False
    try:
      self.execute("""SELECT * FROM quads LIMIT 1;""")
      self.fetchone()
      
    except psycopg2.ProgrammingError:
      initialize_db = True
      self.db.rollback()
      
    if initialize_db:
      self.current_blank    = 0
      self.current_resource = 300 # 300 first values are reserved
      
      self.execute("""CREATE TABLE store (version INTEGER, current_blank INTEGER, current_resource INTEGER)""")
      self.execute("""INSERT INTO store VALUES (2, 0, 300)""")
      self.execute("""CREATE TABLE quads (c INTEGER, s VARCHAR(20), p VARCHAR(20), o TEXT)""")
      self.execute("""CREATE TABLE ontologies (c SERIAL PRIMARY KEY DEFERRABLE INITIALLY DEFERRED, iri TEXT, last_update NUMERIC)""")
      self.execute("""CREATE TABLE ontology_alias (iri TEXT, alias TEXT)""")
      self.execute("""CREATE TABLE resources (storid VARCHAR(20) PRIMARY KEY DEFERRABLE INITIALLY DEFERRED, iri TEXT)""")
      self.sql.executemany("INSERT INTO resources VALUES (%s,%s)", _universal_abbrev_2_iri.items())
      self.execute("""CREATE UNIQUE INDEX index_resources_iri ON resources(iri)""")
      self.execute("""CREATE INDEX index_quads_s ON quads(s)""")
      self.execute("""CREATE INDEX index_quads_o ON quads(o)""")
      self.db.commit()
      
    else:
      if clone:
        s = "\n".join(clone.db.iterdump())
        self.db.cursor().executescript(s)
        
      self.execute("SELECT version, current_blank, current_resource FROM store")
      version, self.current_blank, self.current_resource = self.fetchone()
      
      
    self.execute("""PREPARE abbreviate1    AS SELECT storid FROM resources WHERE iri=$1 LIMIT 1;""")
    self.execute("""PREPARE abbreviate2    AS INSERT INTO resources VALUES ($1,$2);""")
    self.execute("""PREPARE unabbreviate   AS SELECT iri FROM resources WHERE storid=$1 LIMIT 1;""")
    self.execute("""PREPARE get_quads_sp   AS SELECT o,c FROM quads WHERE s=$1 AND p=$2;""")
    
    self.execute("""PREPARE get_triples_s  AS SELECT p,o FROM quads WHERE s=$1;""")
    self.execute("""PREPARE get_triples_sp AS SELECT o FROM quads WHERE s=$1 AND p=$2;""")
    self.execute("""PREPARE get_triples_po AS SELECT s FROM quads WHERE p=$1 AND o=$2;""")
    self.execute("""PREPARE get_triple_sp  AS SELECT o FROM quads WHERE s=$1 AND p=$2 LIMIT 1;""")
    self.execute("""PREPARE get_triple_po  AS SELECT s FROM quads WHERE p=$1 AND o=$2 LIMIT 1;""")
    self.execute("""PREPARE get_transitive_sp AS
WITH RECURSIVE transit(x)
AS (      SELECT o FROM quads WHERE s=$1 AND p=$2
UNION ALL SELECT quads.o FROM quads, transit WHERE quads.s=transit.x AND quads.p=$2)
SELECT DISTINCT x FROM transit;""")
    self.execute("""PREPARE get_transitive_po AS
WITH RECURSIVE transit(x)
AS (      SELECT s FROM quads WHERE p=$1 AND o=$2
UNION ALL SELECT quads.s FROM quads, transit WHERE quads.p=$1 AND quads.o=transit.x)
SELECT DISTINCT x FROM transit;""")

    self.execute("""PREPARE get_triples_sc  AS SELECT p,o FROM quads WHERE c=$1 AND s=$2;""")
    self.execute("""PREPARE get_triples_spc AS SELECT o FROM quads WHERE c=$1 AND s=$2 AND p=$3;""")
    self.execute("""PREPARE get_triples_poc AS SELECT s FROM quads WHERE c=$1 AND p=$2 AND o=$3;""")
    self.execute("""PREPARE get_triple_spc  AS SELECT o FROM quads WHERE c=$1 AND s=$2 AND p=$3 LIMIT 1;""")
    self.execute("""PREPARE get_triple_poc  AS SELECT s FROM quads WHERE c=$1 AND p=$2 AND o=$3 LIMIT 1;""")
    self.execute("""PREPARE get_transitive_spc AS
WITH RECURSIVE transit(x)
AS (      SELECT o FROM quads WHERE s=$1 AND p=$2 AND c=$3
UNION ALL SELECT quads.o FROM quads, transit WHERE quads.s=transit.x AND quads.p=$2 AND quads.c=$3)
SELECT DISTINCT x FROM transit;""")
    self.execute("""PREPARE get_transitive_poc AS
WITH RECURSIVE transit(x)
AS (      SELECT s FROM quads WHERE p=$1 AND o=$2 AND c=$3
UNION ALL SELECT quads.s FROM quads, transit WHERE quads.p=$1 AND quads.o=transit.x AND quads.c=$3)
SELECT DISTINCT x FROM transit;""")


  def fix_base_iri(self, base_iri, c = None):
    if base_iri.endswith("#") or base_iri.endswith("/"): return base_iri
    use_slash = self.execute("SELECT resources.iri FROM resources WHERE SUBSTR(resources.iri, 1, %s)=%s LIMIT 1", (len(base_iri) + 1, base_iri + "/",)).fetchone()
    if use_slash: return "%s/" % base_iri
    else:         return "%s#" % base_iri
    
    
   
  def sub_graph(self, onto):
    new_in_quadstore = False
    self.execute("SELECT c FROM ontologies WHERE iri=%s", (onto.base_iri,))
    c = self.fetchone()
    if c is None:
      self.execute("SELECT ontologies.c FROM ontologies, ontology_alias WHERE ontology_alias.alias=%s AND ontologies.iri=ontology_alias.iri", (onto.base_iri,))
      c = self.fetchone()
      if c is None:
        new_in_quadstore = True
        self.execute("INSERT INTO ontologies (iri, last_update) VALUES (%s, 0)", (onto.base_iri,))
        self.execute("SELECT c FROM ontologies WHERE iri=%s", (onto.base_iri,))
        c = self.fetchone()
    c = c[0]
    self.c_2_onto[c] = onto
    
    return SubGraph(self, onto, c, self.db, self.sql), new_in_quadstore
  
  def ontologies_iris(self):
    self.execute("SELECT iri FROM ontologies")
    for (iri,) in self.fetchall(): yield iri
   
  def get_storid_dict(self):
    self.execute("SELECT storid, iri FROM resources")
    return dict(self.fetchall())
     
  def get_iri_dict(self):
    self.execute("SELECT iri, storid FROM resources")
    return dict(self.fetchall())
     
  def abbreviate(self, iri):
    ##self.execute("SELECT storid FROM resources WHERE iri=%s LIMIT 1", (iri,))
    #self.execute("EXECUTE abbreviate1(%s)", (iri,))
    #r = self.fetchone()
    #if r: return r[0]
    #self.current_resource += 1
    #storid = _int_base_62(self.current_resource)
    ##self.execute("INSERT INTO resources VALUES (%s,%s)", (storid, iri))
    #self.execute("EXECUTE abbreviate2(%s,%s)", (storid, iri))
    #return storid
    
    with self.cursor() as cur:
      cur.execute("EXECUTE abbreviate1(%s)", (iri,))
      r = cur.fetchone()
      if r: return r[0]
      self.current_resource += 1
      storid = _int_base_62(self.current_resource)
      cur.execute("EXECUTE abbreviate2(%s,%s)", (storid, iri))
      return storid
    
  def unabbreviate(self, storid):
    #self.execute("SELECT iri FROM resources WHERE storid=%s LIMIT 1", (storid,))
    #self.execute("EXECUTE unabbreviate(%s)", (storid,))
    #return self.fetchone()[0]
    with self.cursor() as cur:
      cur.execute("EXECUTE unabbreviate(%s)", (storid,))
      return cur.fetchone()[0]
  
  def new_numbered_iri(self, prefix):
    if prefix in self.last_numbered_iri:
      i = self.last_numbered_iri[prefix] = self.last_numbered_iri[prefix] + 1
      return "%s%s" % (prefix, i)
    else:
      self.execute("SELECT iri FROM resources WHERE iri LIKE %s ORDER BY LENGTH(iri) DESC, iri DESC", ("%s%%" % prefix,))
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
    self.execute("UPDATE resources SET iri=%s WHERE storid=%s", (new_iri, storid,))
    
    
    
  def commit(self):
    self.execute("UPDATE store SET current_blank=%s, current_resource=%s", (self.current_blank, self.current_resource))
    self.db.commit()
    
  def get_fts_prop_storid(self): return []
  
  
  
  def context_2_user_context(self, c): return self.c_2_onto[c]

  def new_blank_node(self):
    self.current_blank += 1
    return "_%s" % _int_base_62(self.current_blank)
  
  def get_triples(self, s, p, o, ignore_missing_datatype = False):
    if s is None:
      if p is None:
        if o is None: self.execute("SELECT s,p,o FROM quads")
        else:
          if ignore_missing_datatype and o.endswith('"'):
            self.execute("SELECT s,p,o FROM quads WHERE SUBSTR(o,1,%s)=%s", (len(o), o,))
          else:
            self.execute("SELECT s,p,o FROM quads WHERE o=%s", (o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE p=%s", (p,))
        else:
          if ignore_missing_datatype and o.endswith('"'):
            self.execute("SELECT s,p,o FROM quads WHERE p=%s AND SUBSTR(o,1,%s)=%s", (p, len(o), o,))
          else:
            self.execute("SELECT s,p,o FROM quads WHERE p=%s AND o=%s", (p, o,))
    else:
      if p is None:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE s=%s", (s,))
        else:
          if ignore_missing_datatype and o.endswith('"'):
            self.execute("SELECT s,p,o FROM quads WHERE s=%s AND SUBSTR(o,1,%s)=%s", (s, len(o), o,))
          else:
            self.execute("SELECT s,p,o FROM quads WHERE s=%s AND o=%s", (s, o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE s=%s AND p=%s", (s, p,))
        else:
          if ignore_missing_datatype and o.endswith('"'):
            self.execute("SELECT s,p,o FROM quads WHERE s=%s AND p=%s AND SUBSTR(o,1,%s)=%s", (s, p, len(o), o,))
          else:
            self.execute("SELECT s,p,o FROM quads WHERE s=%s AND p=%s AND o=%s", (s, p, o,))
    return self.fetchall()
    
  def get_quads(self, s, p, o, c):
    if c is None:
      if s is None:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads")
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE o=%s", (o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE p=%s", (p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE p=%s AND o=%s", (p, o,))
      else:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE s=%s", (s,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE s=%s AND o=%s", (s, o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE s=%s AND p=%s", (s, p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE s=%s AND p=%s AND o=%s", (s, p, o,))
    else:
      if s is None:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=%s", (c,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=%s AND o=%s", (c, o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=%s AND p=%s", (c, p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=%s AND p=%s AND o=%s", (c, p, o,))
      else:
        if p is None:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=%s AND s=%s", (c, s,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=%s AND s=%s AND o=%s", (c, s, o,))
        else:
          if o is None: self.execute("SELECT s,p,o,c FROM quads WHERE c=%s AND s=%s AND p=%s", (c, s, p,))
          else:         self.execute("SELECT s,p,o,c FROM quads WHERE c=%s AND s=%s AND p=%s AND o=%s", (c, s, p, o,))
    return self.fetchall()
  
  def get_quads_sp(self, s, p):
    #self.execute("SELECT o,c FROM quads WHERE s=%s AND p=%s", (s, p))
    #self.execute("EXECUTE get_quads_sp(%s,%s)", (s, p))
    #return self.fetchall()
    with self.cursor() as cur:
      cur.execute("EXECUTE get_quads_sp(%s,%s)", (s, p))
      return cur.fetchall()
    
  def get_pred(self, s):
    self.execute("SELECT DISTINCT p FROM quads WHERE s=%s", (s,))
    for (x,) in self.fetchall(): yield x
    
  def get_triples_s(self, s):
    #self.execute("SELECT p,o FROM quads WHERE s=%s", (s,))
    #self.execute("EXECUTE get_triples_s(%s)", (s,))
    #return self.fetchall()
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triples_s(%s)", (s,))
      return cur.fetchall()
    
  def get_triples_sp(self, s, p):
    #self.execute("SELECT o FROM quads WHERE s=%s AND p=%s", (s, p))
    #self.execute("EXECUTE get_triples_sp(%s, %s)", (s, p))
    #for (x,) in self.fetchall(): yield x
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triples_sp(%s, %s)", (s, p))
      #cur.callproc("get_triples_sp", (s, p))
      #for (x,) in cur.fetchall(): yield x
      for (x,) in cur: yield x
    
  def get_triples_po(self, p, o):
    #self.execute("SELECT s FROM quads WHERE p=%s AND o=%s", (p, o))
    #self.execute("EXECUTE get_triples_po(%s, %s)", (p, o))
    #for (x,) in self.fetchall(): yield x
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triples_po(%s, %s)", (p, o))
      for (x,) in cur: yield x
      
  def get_triple_sp(self, s = None, p = None):
    #self.execute("SELECT o FROM quads WHERE s=%s AND p=%s LIMIT 1", (s, p))
    #self.execute("EXECUTE get_triple_sp(%s, %s)", (s, p))
    #r = self.fetchone()
    #if r: return r[0]
    #return None
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triple_sp(%s, %s)", (s, p))
      #cur.callproc("get_triples_sp", (s, p))
      r = cur.fetchone()
    if r: return r[0]
    return None
          
  def get_triple_po(self, p = None, o = None):
    #self.execute("SELECT s FROM quads WHERE p=%s AND o=%s LIMIT 1", (p, o))
    #self.execute("EXECUTE get_triple_po(%s, %s)", (p, o))
    #r = self.fetchone()
    #if r: return r[0]
    #return None
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triple_po(%s, %s)", (p, o))
      r = cur.fetchone()
    if r: return r[0]
    return None
  
  def has_triple(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads LIMIT 1")
        else:         self.execute("SELECT s FROM quads WHERE o=%s LIMIT 1", (o,))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE p=%s LIMIT 1", (p,))
        else:         self.execute("SELECT s FROM quads WHERE p=%s AND o=%s LIMIT 1", (p, o))
    else:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads WHERE s=%s LIMIT 1", (s,))
        else:         self.execute("SELECT s FROM quads WHERE s=%s AND o=%s LIMIT 1", (s, o))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE s=%s AND p=%s LIMIT 1", (s, p))
        else:         self.execute("SELECT s FROM quads WHERE s=%s AND p=%s AND o=%s LIMIT 1", (s, p, o))
    return not self.fetchone() is None
  
  def _del_triple(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: self.execute("DELETE FROM quads")
        else:         self.execute("DELETE FROM quads WHERE o=%s", (o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE p=%s", (p,))
        else:         self.execute("DELETE FROM quads WHERE p=%s AND o=%s", (p, o,))
    else:
      if p is None:
        if o is None: self.execute("DELETE FROM quads WHERE s=%s", (s,))
        else:         self.execute("DELETE FROM quads WHERE s=%s AND o=%s", (s, o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE s=%s AND p=%s", (s, p,))
        else:         self.execute("DELETE FROM quads WHERE s=%s AND p=%s AND o=%s", (s, p, o,))
        
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
        conditions  .append("q%s.c = %%s" % i)
        params      .append(c)
        
      if   k == " iri":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        tables    .append("resources")
        conditions.append("resources.storid = q%s.s" % i)
        if "*" in v:
          conditions.append("resources.iri LIKE %s")
          params.append(v.replace("*", "%").replace("_", "\\_"))
        else:
          conditions.append("resources.iri = %s")
          params.append(v)
        
      elif k == " is_a":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("(q%s.p = '%s' OR q%s.p = '%s') AND q%s.o IN (%s)" % (i, rdf_type, i, rdfs_subclassof, i, ",".join("%s" for i in v)))
        params    .extend(v)
        
      elif k == " type":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("q%s.p = '%s' AND q%s.o IN (%s)" % (i, rdf_type, i, ",".join("%s" for i in v)))
        params    .extend(v)
        
      elif k == " subclass_of":
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("q%s.p = '%s' AND q%s.o IN (%s)" % (i, rdfs_subclassof, i, ",".join("%s" for i in v)))
        params    .extend(v)
        
      elif isinstance(k, tuple): # Prop with inverse
        if i == 1: # Does not work if it is the FIRST => add a dumb first.
          i += 1
          tables.append("quads q%s" % i)
          if not c is None:
            conditions  .append("q%s.c = %%s" % i)
            params      .append(c)
            
        if v.startswith('"*"'):
          cond1 = "q%s.s = q1.s AND q%s.p = %%s" % (i, i)
          cond2 = "q%s.o = q1.s AND q%s.p = %%s" % (i, i)
          params.extend([k[0], k[1]])
        else:
          cond1 = "q%s.s = q1.s AND q%s.p = %%s AND q%s.o = %%s" % (i, i, i)
          cond2 = "q%s.o = q1.s AND q%s.p = %%s AND q%s.s = %%s" % (i, i, i)
          params.extend([k[0], v, k[1], v])
        conditions  .append("((%s) OR (%s))" % (cond1, cond2))
        
      else: # Prop without inverse
        if i > 1: conditions.append("q%s.s = q1.s" % i)
        conditions.append("q%s.p = %%s" % i)
        params    .append(k)
        if "*" in v:
          if   v.startswith('"*"'):
            conditions.append("q%s.o LIKE '%'" % i)
          else:
            conditions.append("q%s.o LIKE %%s" % i)
            params    .append(v.replace("*", "%").replace("_", "\\_"))
        else:
          conditions.append("q%s.o = %%s" % i)
          params    .append(v)
          
    req = "SELECT DISTINCT q1.s from %s WHERE %s" % (", ".join(tables), " AND ".join(conditions))
    
    if excepts:
      conditions = []
      for except_p in excepts:
        if isinstance(except_p, tuple): # Prop with inverse
          conditions.append("quads.s = candidates.s AND quads.p = %s")
          params    .append(except_p[0])
          conditions.append("quads.o = candidates.s AND quads.p = %s")
          params    .append(except_p[1])
        else: # No inverse
          conditions.append("quads.s = candidates.s AND quads.p = %s")
          params    .append(except_p)
          
          
      req = """
WITH candidates(s) AS (%s)
SELECT s FROM candidates
EXCEPT SELECT candidates.s FROM candidates, quads WHERE (%s)""" % (req, ") OR (".join(conditions))
      
    #print(prop_vals)
    #print(req)
    #print(params)
    
    self.execute(req, params)
    return self.fetchall()
  
  def _punned_entities(self):
    from owlready2.base import rdf_type, owl_class, owl_named_individual
    self.execute("SELECT q1.s FROM quads q1, quads q2 WHERE q1.s=q2.s AND q1.p=%s AND q2.p=%s AND q1.o=%s AND q2.o=%s", (rdf_type, rdf_type, owl_class, owl_named_individual))
    return [storid for (storid,) in self.fetchall()]
  
    
  def __len__(self):
    self.execute("SELECT COUNT(*) FROM quads")
    return self.fetchone()[0]

  
  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_sp(self, s, p):
#    for (x,) in self.execute("""
#WITH RECURSIVE transit(x)
#AS (      SELECT o FROM quads WHERE s=%s AND p=%s
#UNION ALL SELECT quads.o FROM quads, transit WHERE quads.s=transit.x AND quads.p=%s)
#SELECT DISTINCT x FROM transit""", (s, p, p)).fetchall(): yield x
    with self.cursor() as cur:
      cur.execute("EXECUTE get_transitive_sp(%s,%s)", (s, p))
      for (x,) in cur: yield x
    
  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_po(self, p, o):
    with self.cursor() as cur:
      cur.execute("EXECUTE get_transitive_po(%s,%s)", (p, o))
      for (x,) in cur: yield x

# Slower than Python implementation
#   def get_transitive_sym2(self, s, p):
#     r = { s }
#     self.execute("""
# WITH RECURSIVE transit(s,o)
# AS (  SELECT s,o from quads WHERE (s=%s OR o=%s) AND (p=%s)
# UNION SELECT quads.s,quads.o FROM quads, transit WHERE (quads.s=transit.s OR quads.o=transit.o OR quads.s=transit.o OR quads.o=transit.s) AND quads.p=%s)
# SELECT s, o FROM transit""", (s, s, p, p))
#     for (s, o) in self.fetchall():
#       r.add(s)
#       r.add(o)
#     yield from r
    

  def _destroy_collect_storids(self, destroyed_storids, modified_relations, storid):
    with self.cursor() as cur :
      cur.execute("""SELECT s FROM quads WHERE o=%%s AND p IN (
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
      ), (storid,))
      for (blank_using,) in list(cur.fetchall()):
        if not blank_using in destroyed_storids:
          destroyed_storids.add(blank_using)
          self._destroy_collect_storids(destroyed_storids, modified_relations, blank_using)

      cur.execute("""SELECT c, s FROM quads WHERE o=%%s AND p='%s' AND substr(s, 1, 1)='_'""" % (
          rdf_first,
      ), (storid,))
      for (c, blank_using) in list(cur.fetchall()):
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
      
    self.execute("SELECT s FROM quads WHERE o=%s LIMIT 1", (root,))
    list_user = self.fetchone()
    if list_user: list_user = list_user[0]
    return list_user, root, previouss, nexts, length
  
  def destroy_entity(self, storid, destroyer, relation_updater):
    destroyed_storids   = { storid }
    modified_relations  = defaultdict(set)
    self._destroy_collect_storids(destroyed_storids, modified_relations, storid)
    
    self.execute("SELECT DISTINCT s,p FROM quads WHERE o IN (%s)" % ",".join(["%s" for i in destroyed_storids]), tuple(destroyed_storids))
    for s,p in self.fetchall():
      if not s in destroyed_storids:
        modified_relations[s].add(p)
        
    # Two separate loops because high level destruction must be ended before removing from the quadstore (high level may need the quadstore)
    for storid in destroyed_storids:
      destroyer(storid)
      
    for storid in destroyed_storids:
      self.execute("DELETE FROM quads WHERE s=%s OR o=%s", (storid, storid))
      
    for s, ps in modified_relations.items():
      relation_updater(destroyed_storids, s, ps)
      
    return destroyed_storids
  
  def _iter_ontology_iri(self, c = None):
    if c:
      self.execute("SELECT iri FROM ontologies WHERE c=%s", (c,))
      return self.fetchone()[0]
    else:
      self.execute("SELECT c, iri FROM ontologies")
      return self.fetchall()
    
  def _iter_triples(self, quads = False, sort_by_s = False):
    cursor = self.db.cursor() # Use a new cursor => can iterate without laoding all data in a big list, while still being able to query the default cursor
    if quads:
      if sort_by_s: cursor.execute("SELECT c,s,p,o FROM quads ORDER BY s")
      else:         cursor.execute("SELECT c,s,p,o FROM quads")
    else:
      if sort_by_s: cursor.execute("SELECT s,p,o FROM quads ORDER BY s")
      else:         cursor.execute("SELECT s,p,o FROM quads")
    return cursor
  
        
  
class SubGraph(BaseSubGraph):
  def __init__(self, parent, onto, c, db, sql):
    BaseSubGraph.__init__(self, parent, onto)
    self.c      = c
    self.db     = db
    self.sql    = sql
    self.cursor   = self.db.cursor
    self.execute  = self.sql.execute
    self.fetchone = self.sql.fetchone
    self.fetchall = self.sql.fetchall
    self.abbreviate       = parent.abbreviate
    self.unabbreviate     = parent.unabbreviate
    self.new_numbered_iri = parent.new_numbered_iri
    
    self.parent.onto_2_subgraph[onto] = self
    
  def create_parse_func(self, filename = None, delete_existing_triples = True, datatype_attr = "http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype"):
    values       = []
    #abbrevs      = {}
    abbrevs      = self.parent.get_iri_dict()
    new_abbrevs  = []

    t0  = time.time()
    
    # def abbreviate(iri): # Re-implement for speed
    #   storid = abbrevs.get(iri)
    #   if not storid is None: return storid
    #   self.execute("EXECUTE abbreviate1(%s)", (iri,))
    #   r = self.fetchone()
    #   if r:
    #     abbrevs[iri] = r[0]
    #     return r[0]
    #   self.parent.current_resource += 1
    #   storid = _int_base_62(self.parent.current_resource)
    #   new_abbrevs.append((storid, iri))
    #   abbrevs[iri] = storid
    #   return storid
    
    def abbreviate(iri): # Re-implement for speed
      storid = abbrevs.get(iri)
      if storid is None:
        self.parent.current_resource += 1
        storid = _int_base_62(self.parent.current_resource)
        new_abbrevs.append((storid, iri))
        abbrevs[iri] = storid
      return storid

    entities = set()
    def on_prepare_triple(s, p, o):
      entities.add(s)
      
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
      
      with self.cursor() as cur:
        if delete_existing_triples: cur.execute("DELETE FROM quads WHERE c=%s", (self.c,))
        
        if len(self.parent) < 100000:
          cur.execute("""DROP INDEX index_resources_iri""")
          cur.execute("""DROP INDEX index_quads_s""")
          cur.execute("""DROP INDEX index_quads_o""")
          reindex = True
        else:
          reindex = False
          
      if owlready2.namespace._LOG_LEVEL: print("* OwlReady2 * Importing %s triples from ontology %s ..." % (len(values), self.onto.base_iri), file = sys.stderr)
      
      new_abbrevs.sort(key = lambda x: x[1])
      values.sort(key = lambda x: x[0])

      t  = time.time()
      self.sql.execute("""set maintenance_work_mem = %s""", (HIGH_WORK_MEM,))
      
      with self.cursor() as cur:
        f = StringIO("\n".join("%s\t%s" % vs for vs in new_abbrevs))
        cur.copy_from(f, "resources")
      
      with self.cursor() as cur:
        f = StringIO("\n".join("%s\t%s\t%s\t%s" % (self.c, vs[0], vs[1], vs[2].replace("\\", "\\\\").replace("\t", "\\t").replace('\n', '\\n')) for vs in values))
        cur.copy_from(f, "quads")
        
      t  = time.time()
      if reindex:
        with self.cursor() as cur:
          cur.execute("""
CREATE UNIQUE INDEX index_resources_iri ON resources(iri);
CREATE INDEX index_quads_s ON quads(s);
CREATE INDEX index_quads_o ON quads(o);""")
      t  = time.time()
      
      self.sql.execute("""set maintenance_work_mem = %s""", (DEFAULT_WORK_MEM,))
      
      with self.cursor() as cur:
        cur.execute("SELECT resources.iri FROM quads, resources WHERE quads.c=%s AND quads.o=%s AND resources.storid=quads.s LIMIT 1", (self.c, owl_ontology))
        onto_base_iri = cur.fetchone()
        if onto_base_iri: onto_base_iri = onto_base_iri[0]
        else:             onto_base_iri = ""
        
      if onto_base_iri and (not onto_base_iri.endswith("/")):
        onto_base_iri_hash = "%s#" % onto_base_iri
        for e in entities:
          if e.startswith(onto_base_iri_hash):
            onto_base_iri = onto_base_iri + "#"
            break
        else:
          onto_base_iri_slash = "%s/" % onto_base_iri
          for e in entities:
            if e.startswith(onto_base_iri_slash):
              onto_base_iri = onto_base_iri + "/"
              break
          else:
            onto_base_iri = onto_base_iri + "#"
            
        with self.cursor() as cur:
          cur.execute("UPDATE ontologies SET last_update=%s,iri=%s WHERE c=%s", (date, onto_base_iri, self.c,))
      else:
        with self.cursor() as cur:
          cur.execute("UPDATE ontologies SET last_update=%s WHERE c=%s", (date, self.c,))

      return onto_base_iri
      
    return on_prepare_triple, self.parent.new_blank_node, new_literal, abbreviate, on_finish


  def context_2_user_context(self, c): return self.parent.c_2_onto[c]
 
  def add_ontology_alias(self, iri, alias):
    self.execute("INSERT into ontology_alias VALUES (%s,%s)", (iri, alias))
    
  def get_last_update_time(self):
    self.execute("SELECT last_update FROM ontologies WHERE c=%s", (self.c,))
    return self.fetchone()[0]
  
  def set_last_update_time(self, t):
    self.execute("UPDATE ontologies SET last_update=%s WHERE c=%s", (t, self.c))
    
  def destroy(self):
    self.execute("DELETE FROM quads WHERE c=%s",      (self.c,))
    self.execute("DELETE FROM ontologies WHERE c=%s", (self.c,))
    
  def _set_triple(self, s, p, o):
    if (s is None) or (p is None) or (o is None): raise ValueError
    self.execute("DELETE FROM quads WHERE c=%s AND s=%s AND p=%s", (self.c, s, p,))
    self.execute("INSERT INTO quads VALUES (%s, %s, %s, %s)", (self.c, s, p, o))
    
  def _add_triple(self, s, p, o):
    if (s is None) or (p is None) or (o is None): raise ValueError
    self.execute("INSERT INTO quads VALUES (%s, %s, %s, %s)", (self.c, s, p, o))
    
  def _del_triple(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: self.execute("DELETE FROM quads WHERE c=%s", (self.c,))
        else:         self.execute("DELETE FROM quads WHERE c=%s AND o=%s", (self.c, o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE c=%s AND p=%s", (self.c, p,))
        else:         self.execute("DELETE FROM quads WHERE c=%s AND p=%s AND o=%s", (self.c, p, o,))
    else:
      if p is None:
        if o is None: self.execute("DELETE FROM quads WHERE c=%s AND s=%s", (self.c, s,))
        else:         self.execute("DELETE FROM quads WHERE c=%s AND s=%s AND o=%s", (self.c, s, o,))
      else:
        if o is None: self.execute("DELETE FROM quads WHERE c=%s AND s=%s AND p=%s", (self.c, s, p,))
        else:         self.execute("DELETE FROM quads WHERE c=%s AND s=%s AND p=%s AND o=%s", (self.c, s, p, o,))
        
  def get_triples(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=%s", (self.c,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=%s AND o=%s", (self.c, o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=%s AND p=%s", (self.c, p,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=%s AND p=%s AND o=%s", (self.c, p, o,))
    else:
      if p is None:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=%s AND s=%s", (self.c, s,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=%s AND s=%s AND o=%s", (self.c, s, o,))
      else:
        if o is None: self.execute("SELECT s,p,o FROM quads WHERE c=%s AND s=%s AND p=%s", (self.c, s, p,))
        else:         self.execute("SELECT s,p,o FROM quads WHERE c=%s AND s=%s AND p=%s AND o=%s", (self.c, s, p, o,))
    return self.fetchall()
  
  def get_triples_s(self, s):
    #self.execute("SELECT p,o FROM quads WHERE c=%s AND s=%s", (self.c, s,))
    self.execute("EXECUTE get_triples_sc(%s,%s)", (self.c, s,))
    return self.fetchall()
  
  def get_triples_sp(self, s, p):
    #self.execute("SELECT o FROM quads WHERE c=%s AND s=%s AND p=%s", (self.c, s, p,))
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triples_spc(%s,%s,%s)", (self.c, s, p))
      for (x,) in cur: yield x
      
  def get_triples_po(self, p, o):
    #self.execute("SELECT s FROM quads WHERE c=%s AND p=%s AND o=%s", (self.c, p, o,))
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triples_poc(%s,%s,%s)", (self.c, p, o))
      for (x,) in cur: yield x
    
  def get_triple_sp(self, s, p):
    #self.execute("SELECT o FROM quads WHERE c=%s AND s=%s AND p=%s LIMIT 1", (self.c, s, p,))
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triple_spc(%s,%s,%s)", (self.c, s, p))
      r = cur.fetchone()
      if r: return r[0]
      return None
    
  def get_triple_po(self, p, o):
    #self.execute("SELECT s FROM quads WHERE c=%s AND p=%s AND o=%s LIMIT 1", (self.c, p, o,))
    with self.cursor() as cur:
      cur.execute("EXECUTE get_triple_poc(%s,%s,%s)", (self.c, p, o))
      r = cur.fetchone()
      if r: return r[0]
      return None
  
  def get_pred(self, s):
    with self.cursor() as cur:
      cur.execute("SELECT DISTINCT p FROM quads WHERE c=%s AND s=%s", (self.c, s,))
      for (x,) in cur: yield x
    
  def has_triple(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads WHERE c=%s LIMIT 1", (self.c,))
        else:         self.execute("SELECT s FROM quads WHERE c=%s AND o=%s LIMIT 1", (self.c, o,))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE c=%s AND p=%s LIMIT 1", (self.c, p,))
        else:         self.execute("SELECT s FROM quads WHERE c=%s AND p=%s AND o=%s LIMIT 1", (self.c, p, o,))
    else:
      if p is None:
        if o is None: self.execute("SELECT s FROM quads WHERE c=%s AND s=%s LIMIT 1", (self.c, s,))
        else:         self.execute("SELECT s FROM quads WHERE c=%s AND s=%s AND o=%s LIMIT 1", (self.c, s, o,))
      else:
        if o is None: self.execute("SELECT s FROM quads WHERE c=%s AND s=%s AND p=%s LIMIT 1", (self.c, s, p,))
        else:         self.execute("SELECT s FROM quads WHERE c=%s AND s=%s AND p=%s AND o=%s LIMIT 1", (self.c, s, p, o,))
    return not self.fetchone() is None
  
  def get_quads(self, s, p, o, c):
    return [(s, p, o, self.c) for (s, p, o) in self.get_triples(s, p, o)]
  
  def search(self, prop_vals, c = None): return self.parent.search(prop_vals, self.c)
  
  def __len__(self):
    self.execute("SELECT COUNT(*) FROM quads WHERE c=%s", (self.c,))
    return self.fetchone()[0]


  def _iter_ontology_iri(self, c = None):
    if c:
      self.execute("SELECT iri FROM ontologies WHERE c=%s", (c,))
      return self.fetchone()[0]
    else:
      self.execute("SELECT c, iri FROM ontologies")
      return self.fetchall()
    
  def _iter_triples(self, quads = False, sort_by_s = False):
    cursor = self.db.cursor() # Use a new cursor => can iterate without laoding all data in a big list, while still being able to query the default cursor
    if quads:
      if sort_by_s: cursor.execute("SELECT c,s,p,o FROM quads WHERE c=%s ORDER BY s", (self.c,))
      else:         cursor.execute("SELECT c,s,p,o FROM quads WHERE c=%s", (self.c,))
    else:
      if sort_by_s: cursor.execute("SELECT s,p,o FROM quads WHERE c=%s ORDER BY s", (self.c,))
      else:         cursor.execute("SELECT s,p,o FROM quads WHERE c=%s", (self.c,))
    return cursor

  
  
  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_sp(self, s, p):
    self.execute("EXECUTE get_transitive_spc(%s,%s)", (s, p, c))
    for (x,) in self.fetchall(): yield x
    
  # Reimplemented using RECURSIVE SQL structure, for performance
  def get_transitive_po(self, p, o):
    self.execute("EXECUTE get_transitive_poc(%s,%s)", (p, o, c))
    for (x,) in self.fetchall(): yield x

#  def get_transitive_sym(self, s, p):
#    r = { s }
#    for (s, o) in self.execute("""
#WITH RECURSIVE transit(s,o)
#AS (  SELECT s,o from quads WHERE (s=%s OR o=%s) AND p=%s AND c=%s
#    UNION SELECT quads.s,quads.o FROM quads, transit WHERE (quads.s=transit.s OR quads.o=transit.o OR quads.s=transit.o OR quads.o=transit.s) AND quads.p=%s AND quads.c=%s)
#SELECT s, o FROM transit""", (s, s, p, self.c, p, self.c)):
#      r.add(s)
#      r.add(o)
#    yield from r
