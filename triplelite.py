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

import sys, os, os.path, sqlite3, time, re, threading
from collections import defaultdict
from itertools import chain

import owlready2
from owlready2.base import *
from owlready2.driver import BaseMainGraph, BaseSubGraph
from owlready2.driver import _guess_format, _save
from owlready2.util import FTS
from owlready2.base import _universal_abbrev_2_iri

def all_combinations(l):
  """returns all the combinations of the sublist in the given list (i.e. l[0] x l[1] x ... x l[n])."""
  if len(l) == 0: return ()
  if len(l) == 1: return [(a,) for a in l[0]]
  r = []
  for a in l[0]: r.extend((a,) + b for b in all_combinations(l[1:]))
  return r

# def group_iters(quad_cursor, data_cursor):
#   s = None
  
#   quad = next(quad_cursor, None)
#   data = next(data_cursor, None)
  
#   while quad or data:
#     if quad and data:
#       if quad[0] < data[0]: s = quad[0]
#       else:                 s = data[0]
#     elif quad:              s = quad[0]
#     else:                   s = data[0]
    
#     while quad:
#       if quad[0] != s: break
#       yield quad
#       quad = next(quad_cursor, None)
      
#     while data:
#       if data[0] != s: break
#       yield data
#       data = next(data_cursor, None)
      

class Graph(BaseMainGraph):
  _SUPPORT_CLONING = True
  def __init__(self, filename, clone = None, exclusive = True, world = None, profiling = False):
    exists        = os.path.exists(filename) and os.path.getsize(filename) # BEFORE creating db!
    initialize_db = (clone is None) and ((filename == ":memory:") or (not exists))
    
    self.db = sqlite3.connect(filename, check_same_thread = False)
    if exclusive: self.db.execute("""PRAGMA locking_mode = EXCLUSIVE""")
    else:         self.db.execute("""PRAGMA locking_mode = NORMAL""")
    
    if profiling:
      import time
      from collections import Counter
      self.requests_counts = Counter()
      self.requests_times  = Counter()
      
      def execute(s, args = ()):
        if "SELECT" in s:
          self.requests_counts[s] += 1
          t0 = time.time()
          r = list(self.db.execute(s, args))
          t = time.time() - t0
          self.requests_times[s] += t
        return self.db.execute(s, args)
      self.execute = execute
      
      def reset_profiling():
        self.requests_counts = Counter()
        self.requests_times  = Counter()
      self.reset_profiling = reset_profiling
      
      def show_profiling():
        print(file = sys.stderr)
        print("Request counts:", file = sys.stderr)
        for s, nb in self.requests_counts.most_common():
          print(" ", nb, "\t", s.replace("\n", " "), file = sys.stderr)
        print(file = sys.stderr)
        print("Request total times:", file = sys.stderr)
        for s, nb in self.requests_times.most_common():
          print(" ", nb, "\t", s.replace("\n", " "), file = sys.stderr)
        print(file = sys.stderr)
        print("Request mean times:", file = sys.stderr)
        rmt = Counter()
        for s, nb in self.requests_counts.most_common():
          rmt[s] = self.requests_times[s] / nb
        for s, nb in rmt.most_common():
          print(" ", nb, "\t", s.replace("\n", " "), file = sys.stderr)
      self.show_profiling = show_profiling
      
    else:
      self.execute  = self.db.execute
      
    self.c_2_onto          = {}
    self.onto_2_subgraph   = {}
    self.last_numbered_iri = {}
    self.world             = world
    self.c                 = None
    
    self.lock              = threading.RLock()
    self.lock_level        = 0
    
    if initialize_db:
      self.current_blank    = 0
      self.current_resource = 300 # 300 first values are reserved
      self.prop_fts         = set()
      
      self.execute("""CREATE TABLE store (version INTEGER, current_blank INTEGER, current_resource INTEGER)""")
      self.execute("""INSERT INTO store VALUES (5, 0, 300)""")
      self.execute("""CREATE TABLE objs (c INTEGER, s INTEGER, p INTEGER, o INTEGER)""")
      self.execute("""CREATE TABLE datas (c INTEGER, s INTEGER, p INTEGER, o BLOB, d INTEGER)""")
      self.execute("""CREATE VIEW quads (c,s,p,o,d) AS SELECT c,s,p,o,NULL FROM objs UNION ALL SELECT c,s,p,o,d FROM datas""")
      
#       self.execute("""CREATE TABLE equivs (rowid INTEGER, c INTEGER, s TEXT, o TEXT)""")
#       self.db.cursor().executescript("""
# CREATE TRIGGER equivs_insert AFTER INSERT ON objs WHEN new.p='x' BEGIN
#   INSERT INTO equivs VALUES (new.rowid * 2, new.c, new.s, new.o), (new.rowid * 2 + 1, new.c, new.o, new.s);
# END;
# CREATE TRIGGER equivs_delete AFTER DELETE ON objs WHEN old.p='x' BEGIN
#   DELETE FROM equivs WHERE rowid IN (old.rowid * 2, old.rowid * 2 + 1);
# END;
# CREATE TRIGGER equivs_update AFTER UPDATE ON objs WHEN new.p='%s' BEGIN
#   UPDATE equivs SET s=new.s, o=new.o  WHERE rowid = new.rowid * 2;
#   UPDATE equivs SET s=new.o, o=new.s  WHERE rowid = new.rowid * 2;
# END;
# """)
#       self.execute("""CREATE INDEX index_equivs_s ON equivs(s)""")

#       """
# INSERT INTO equivs VALUES SELECT c,s,o FROM objs WHERE p='x';
# INSERT INTO equivs VALUES SELECT c,o,s FROM objs WHERE p='x';
# """
      
      
      self.execute("""CREATE TABLE ontologies (c INTEGER PRIMARY KEY, iri TEXT, last_update DOUBLE)""")
      self.execute("""CREATE TABLE ontology_alias (iri TEXT, alias TEXT)""")
      self.execute("""CREATE TABLE prop_fts (storid INTEGER)""")
      try:
        self.execute("""CREATE TABLE resources (storid INTEGER PRIMARY KEY, iri TEXT) WITHOUT ROWID""")
      except sqlite3.OperationalError: # Old SQLite3 does not support WITHOUT ROWID -- here it is just an optimization
        self.execute("""CREATE TABLE resources (storid INTEGER PRIMARY KEY, iri TEXT)""")
      self.db.executemany("INSERT INTO resources VALUES (?,?)", _universal_abbrev_2_iri.items())
      #self.execute("""CREATE UNIQUE INDEX index_resources_iri ON resources(iri)""")
      #self.execute("""CREATE INDEX index_objs_sp ON objs(s,p)""")
      #self.execute("""CREATE INDEX index_objs_po ON objs(p,o)""")
      #self.execute("""CREATE INDEX index_datas_sp ON datas(s,p)""")
      #self.execute("""CREATE INDEX index_datas_po ON datas(p,o)""")
      self.set_indexed(True)
      self.db.commit()
      
    else:
      self.indexed = True
      if clone:
        s = "\n".join(clone.db.iterdump())
        self.db.cursor().executescript(s)
        
      version, self.current_blank, self.current_resource = self.execute("SELECT version, current_blank, current_resource FROM store").fetchone()
      if version == 1:
        print("* Owlready2 * Converting quadstore to internal format 2...", file = sys.stderr)
        self.execute("""CREATE TABLE ontology_alias (iri TEXT, alias TEXT)""")
        self.execute("""UPDATE store SET version=2""")
        self.db.commit()
        
      if version == 2:
        print("* Owlready2 * Converting quadstore to internal format 3...", file = sys.stderr)
        self.execute("""CREATE TABLE prop_fts (fts INTEGER PRIMARY KEY, storid TEXT)""")
        self.execute("""UPDATE store SET version=3""")
        self.db.commit()
        
      if version == 3:
        print("* Owlready2 * Converting quadstore to internal format 4 (this can take a while)...", file = sys.stderr)
        self.execute("""CREATE TABLE objs (c INTEGER, s TEXT, p TEXT, o TEXT)""")
        self.execute("""CREATE TABLE datas (c INTEGER, s TEXT, p TEXT, o BLOB, d TEXT)""")

        objs  = []
        datas = []
        for c,s,p,o in self.execute("""SELECT c,s,p,o FROM quads"""):
          if o.endswith('"'):
            o, d = o.rsplit('"', 1)
            o = o[1:]
            if   d in {'H', 'N', 'R', 'O', 'J', 'I', 'M', 'P', 'K', 'Q', 'S', 'L'}: o = int(o)
            elif d in {'U', 'X', 'V', 'W'}: o = float(o)
            datas.append((c,s,p,o,d))
          else:
            objs.append((c,s,p,o))
        self.db.executemany("INSERT INTO objs VALUES (?,?,?,?)",    objs)
        self.db.executemany("INSERT INTO datas VALUES (?,?,?,?,?)", datas)
        
        self.execute("""DROP TABLE quads""")
        self.execute("""DROP INDEX IF EXISTS index_quads_s """)
        self.execute("""DROP INDEX IF EXISTS index_quads_o""")
        self.execute("""CREATE VIEW quads (c,s,p,o,d) AS SELECT c,s,p,o,NULL FROM objs UNION ALL SELECT c,s,p,o,d FROM datas""")
        self.execute("""CREATE INDEX index_objs_sp ON objs(s,p)""")
        self.execute("""CREATE INDEX index_objs_po ON objs(p,o)""")
        self.execute("""CREATE INDEX index_datas_sp ON datas(s,p)""")
        self.execute("""CREATE INDEX index_datas_po ON datas(p,o)""")
        
        self.execute("""UPDATE store SET version=4""")
        self.db.commit()
        
      if version == 4:
        print("* Owlready2 * Converting quadstore to internal format 5 (this can take a while)...", file = sys.stderr)
        self.execute("""CREATE TABLE objs2 (c INTEGER, s INTEGER, p INTEGER, o INTEGER)""")
        self.execute("""CREATE TABLE datas2 (c INTEGER, s INTEGER, p INTEGER, o BLOB, d INTEGER)""")
        
        _BASE_62 = { c : i for (i, c) in enumerate("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }
        def _base_62_2_int(storid):
          if storid.startswith("_"): sgn = -1; storid = storid[1:]
          else:                      sgn =  1
          r = 0
          for (i, c) in enumerate(storid):
            r += _BASE_62[c] * (62 ** (len(storid) - i - 1))
          return sgn * r
        
        try:
          self.execute("""CREATE TABLE resources2 (storid INTEGER PRIMARY KEY, iri TEXT) WITHOUT ROWID""")
        except sqlite3.OperationalError: # Old SQLite3 does not support WITHOUT ROWID -- here it is just an optimization
          self.execute("""CREATE TABLE resources2 (storid INTEGER PRIMARY KEY, iri TEXT)""")
        l = []
        for storid, iri in self.execute("""SELECT storid, iri FROM resources"""):
          l.append((_base_62_2_int(storid), iri))
        self.db.executemany("INSERT INTO resources2 VALUES (?,?)", l)
        
        l = []
        for c,s,p,o in self.execute("""SELECT c,s,p,o FROM objs"""):
          s = _base_62_2_int(s)
          p = _base_62_2_int(p)
          o = _base_62_2_int(o)
          l.append((c,s,p,o))
        self.db.executemany("INSERT INTO objs2 VALUES (?,?,?,?)", l)
        
        l = []
        for c,s,p,o,d in self.execute("""SELECT c,s,p,o,d FROM datas"""):
          s = _base_62_2_int(s)
          p = _base_62_2_int(p)
          if   not d:  d = 0
          elif d.startswith("@"): pass
          else:        d = _base_62_2_int(d)
          l.append((c,s,p,o,d))
        self.db.executemany("INSERT INTO datas2 VALUES (?,?,?,?,?)", l)
        
        self.execute("""DROP INDEX IF EXISTS index_resources_iri""")
        self.execute("""DROP INDEX IF EXISTS index_quads_s""")
        self.execute("""DROP INDEX IF EXISTS index_quads_o""")
        self.execute("""DROP INDEX IF EXISTS index_objs_sp""")
        self.execute("""DROP INDEX IF EXISTS index_objs_po""")
        self.execute("""DROP INDEX IF EXISTS index_datas_sp""")
        self.execute("""DROP INDEX IF EXISTS index_datas_po""")
        self.execute("""DROP VIEW IF EXISTS quads""")
        self.execute("""DROP TABLE resources""")
        self.execute("""DROP TABLE objs""")
        self.execute("""DROP TABLE datas""")
        
        self.execute("""ALTER TABLE resources2 RENAME TO resources""")
        self.execute("""ALTER TABLE objs2 RENAME TO objs""")
        self.execute("""ALTER TABLE datas2 RENAME TO datas""")
        self.execute("""CREATE VIEW quads (c,s,p,o,d) AS SELECT c,s,p,o,NULL FROM objs UNION ALL SELECT c,s,p,o,d FROM datas""")
        
        self.execute("""CREATE UNIQUE INDEX index_resources_iri ON resources(iri)""")
        self.execute("""CREATE INDEX index_objs_sp ON objs(s,p)""")
        self.execute("""CREATE INDEX index_objs_po ON objs(p,o)""")
        self.execute("""CREATE INDEX index_datas_sp ON datas(s,p)""")
        self.execute("""CREATE INDEX index_datas_po ON datas(p,o)""")
        
        prop_fts  = { storid : fts for (fts, storid) in self.execute("""SELECT fts, storid FROM prop_fts;""") }
        prop_fts2 = { _base_62_2_int(storid) : fts for (storid, fts) in prop_fts.items() }
        for fts in prop_fts.values():
          self.execute("""DROP TABLE fts_%s""" % fts)
          self.execute("""DROP TRIGGER IF EXISTS fts_%s_after_insert""" % fts)
          self.execute("""DROP TRIGGER IF EXISTS fts_%s_after_delete""" % fts)
          self.execute("""DROP TRIGGER IF EXISTS fts_%s_after_update""" % fts)
          
        self.execute("""DROP TABLE prop_fts""")
        self.execute("""CREATE TABLE prop_fts(storid INTEGER)""")
        self.prop_fts = set()
        for storid in prop_fts2: self.enable_full_text_search(storid)
        
        self.execute("""UPDATE store SET version=5""")
        self.db.commit()

        
        
      self.prop_fts = { storid for (storid,) in self.execute("""SELECT storid FROM prop_fts;""") }
      
    self.current_changes = self.db.total_changes
    self.select__abbreviate_method()


    
  def set_indexed(self, indexed):
    self.indexed = indexed
    if indexed:
      #self.execute("""CREATE UNIQUE INDEX index_resources_iri ON resources(iri)""")
      self.execute("""CREATE INDEX index_objs_sp ON objs(s,p)""")
      self.execute("""CREATE INDEX index_objs_po ON objs(p,o)""")
      self.execute("""CREATE INDEX index_datas_sp ON datas(s,p)""")
      self.execute("""CREATE INDEX index_datas_po ON datas(p,o)""")
      for onto in self.world.ontologies.values():
        onto._load_properties()
    else:
      #self.execute("""DROP INDEX IF EXISTS index_resources_iri""")
      self.execute("""DROP INDEX IF EXISTS index_objs_sp""")
      self.execute("""DROP INDEX IF EXISTS index_objs_po""")
      self.execute("""DROP INDEX IF EXISTS index_datas_sp""")
      self.execute("""DROP INDEX IF EXISTS index_datas_po""")
      
  def close(self):
    self.db.close()

  def acquire_write_lock(self):
    self.lock.acquire()
    self.lock_level += 1
  def release_write_lock(self):
    self.lock_level -= 1
    self.lock.release()
  def has_write_lock(self): return self.lock_level
  
  def select__abbreviate_method(self):
    nb = self.execute("SELECT count(*) FROM resources").fetchone()[0]
    if nb < 100000:
      iri_storid = self.execute("SELECT iri, storid FROM resources").fetchall()
      self.  _abbreviate_d = dict(iri_storid)
      self._unabbreviate_d = dict((storid, iri) for (iri, storid) in  iri_storid)
      self._abbreviate   = self._abbreviate_dict
      self._unabbreviate = self._unabbreviate_dict
      self._refactor     = self._refactor_dict
    else:
      self.  _abbreviate_d = None
      self._unabbreviate_d = None
      self._abbreviate   = self._abbreviate_sql
      self._unabbreviate = self._unabbreviate_sql
      self._refactor     = self._refactor_sql
    if self.world:
      self.world._abbreviate   = self._abbreviate
      self.world._unabbreviate = self._unabbreviate
    for subgraph in self.onto_2_subgraph.values():
      subgraph.onto._abbreviate   = subgraph._abbreviate   = self._abbreviate
      subgraph.onto._unabbreviate = subgraph._unabbreviate = self._unabbreviate
      
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
      
  def _abbreviate_sql(self, iri):
    r = self.execute("SELECT storid FROM resources WHERE iri=? LIMIT 1", (iri,)).fetchone()
    if r: return r[0]
    self.current_resource += 1
    storid = self.current_resource
    self.execute("INSERT INTO resources VALUES (?,?)", (storid, iri))
    return storid
  
  def _unabbreviate_sql(self, storid):
    return self.execute("SELECT iri FROM resources WHERE storid=? LIMIT 1", (storid,)).fetchone()[0]
  
  def _abbreviate_dict(self, iri):
    storid = self._abbreviate_d.get(iri)
    if storid is None:
      self.current_resource += 1
      storid = self._abbreviate_d[iri] = self.current_resource
      self._unabbreviate_d[storid] = iri
      self.execute("INSERT INTO resources VALUES (?,?)", (storid, iri))
    return storid
  
  def _unabbreviate_dict(self, storid):
    return self._unabbreviate_d[storid]
  
  def get_storid_dict(self):
    return dict(self.execute("SELECT storid, iri FROM resources").fetchall())
  
  def _new_numbered_iri(self, prefix):
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
  
  def _refactor_sql(self, storid, new_iri):
    self.execute("UPDATE resources SET iri=? WHERE storid=?", (new_iri, storid,))
    
  def _refactor_dict(self, storid, new_iri):
    self.execute("UPDATE resources SET iri=? WHERE storid=?", (new_iri, storid,))
    del self._abbreviate_d[self._unabbreviate_d[storid]]
    self.  _abbreviate_d[new_iri] = storid
    self._unabbreviate_d[storid]  = new_iri
    
  def commit(self):
    if self.current_changes != self.db.total_changes:
      self.current_changes = self.db.total_changes
      self.execute("UPDATE store SET current_blank=?, current_resource=?", (self.current_blank, self.current_resource))
      self.db.commit()

  def context_2_user_context(self, c): return self.c_2_onto[c]

  def new_blank_node(self):
    self.current_blank += 1
    return -self.current_blank
  
  def _get_obj_triples_spo_spo(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs")
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE o=?", (o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs WHERE p=?", (p,))
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE p=? AND o=?", (p, o,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs WHERE s=?", (s,))
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE s=? AND o=?", (s, o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs WHERE s=? AND p=?", (s, p,))
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE s=? AND p=? AND o=?", (s, p, o,))
    return cur.fetchall()
  
  def _get_data_triples_spod_spod(self, s, p, o, d):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas")
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE o=?", (o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE o=? AND d=?", (o,d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas WHERE p=?", (p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE p=? AND o=?", (p, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE p=? AND o=? AND d=?", (p, o, d,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas WHERE s=?", (s,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE s=? AND o=?", (s, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE s=? AND o=? AND d=?", (s, o, d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas WHERE s=? AND p=?", (s, p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE s=? AND p=? AND o=?", (s, p, o))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE s=? AND p=? AND o=? AND d=?", (s, p, o, d,))
    return cur.fetchall()
    
  def _get_triples_spod_spod(self, s, p, o, d):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads")
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE o=?", (o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE o=? AND d=?", (o,d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads WHERE p=?", (p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE p=? AND o=?", (p, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE p=? AND o=? AND d=?", (p, o, d,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads WHERE s=?", (s,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE s=? AND o=?", (s, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE s=? AND o=? AND d=?", (s, o, d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads WHERE s=? AND p=?", (s, p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE s=? AND p=? AND o=?", (s, p, o))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE s=? AND p=? AND o=? AND d=?", (s, p, o, d,))
    return cur.fetchall()
    
  def _get_obj_triples_cspo_cspo(self, c, s, p, o):
    if c is None:
      if s is None:
        if p is None:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs")
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE o=?", (o,))
        else:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs WHERE p=?", (p,))
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE p=? AND o=?", (p, o,))
      else:
        if p is None:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs WHERE s=?", (s,))
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE s=? AND o=?", (s, o,))
        else:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs WHERE s=? AND p=?", (s, p,))
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE s=? AND p=? AND o=?", (s, p, o,))
    else:
      if s is None:
        if p is None:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=?", (c,))
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=? AND o=?", (c, o,))
        else:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=? AND p=?", (c, p,))
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=? AND p=? AND o=?", (c, p, o,))
      else:
        if p is None:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=? AND s=?", (c, s,))
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=? AND s=? AND o=?", (c, s, o,))
        else:
          if o is None: cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=? AND s=? AND p=?", (c, s, p,))
          else:         cur = self.execute("SELECT c,s,p,o FROM objs WHERE c=? AND s=? AND p=? AND o=?", (c, s, p, o,))
    return cur.fetchall()
  
  
  def _get_obj_triples_sp_co(self, s, p):
    return self.execute("SELECT c,o FROM objs WHERE s=? AND p=?", (s, p)).fetchall()
    
  def _get_triples_s_p(self, s):
    for (x,) in self.execute("SELECT DISTINCT p FROM quads WHERE s=?", (s,)).fetchall(): yield x
    
  def _get_obj_triples_s_po(self, s):
    return self.execute("SELECT p,o FROM objs WHERE s=?", (s,)).fetchall()
  
  def _get_obj_triples_sp_o(self, s, p):
    for (x,) in self.execute("SELECT o FROM objs WHERE s=? AND p=?", (s, p)).fetchall(): yield x
    
  def _get_data_triples_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM datas WHERE s=? AND p=?", (s, p)).fetchall()

  def _get_triples_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM quads WHERE s=? AND p=?", (s, p)).fetchall()
    
  def _get_data_triples_s_pod(self, s):
    return self.execute("SELECT p,o,d FROM datas WHERE s=?", (s,)).fetchall()
  
  def _get_triples_s_pod(self, s):
    return self.execute("SELECT p,o,d FROM quads WHERE s=?", (s,)).fetchall()
    
  def _get_obj_triples_po_s(self, p, o):
    for (x,) in self.execute("SELECT s FROM objs WHERE p=? AND o=?", (p, o)).fetchall(): yield x
    
  def _get_obj_triple_sp_o(self, s, p):
    r = self.execute("SELECT o FROM objs WHERE s=? AND p=? LIMIT 1", (s, p)).fetchone()
    if r: return r[0]
    return None
  
  def _get_triple_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM quads WHERE s=? AND p=? LIMIT 1", (s, p)).fetchone()
    
  def _get_data_triple_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM datas WHERE s=? AND p=? LIMIT 1", (s, p)).fetchone()
  
  def _get_obj_triple_po_s(self, p, o):
    r = self.execute("SELECT s FROM objs WHERE p=? AND o=? LIMIT 1", (p, o)).fetchone()
    if r: return r[0]
    return None
  
  def _has_obj_triple_spo(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM objs LIMIT 1")
        else:         cur = self.execute("SELECT s FROM objs WHERE o=? LIMIT 1", (o,))
      else:
        if o is None: cur = self.execute("SELECT s FROM objs WHERE p=? LIMIT 1", (p,))
        else:         cur = self.execute("SELECT s FROM objs WHERE p=? AND o=? LIMIT 1", (p, o))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM objs WHERE s=? LIMIT 1", (s,))
        else:         cur = self.execute("SELECT s FROM objs WHERE s=? AND o=? LIMIT 1", (s, o))
      else:
        if o is None: cur = self.execute("SELECT s FROM objs WHERE s=? AND p=? LIMIT 1", (s, p))
        else:         cur = self.execute("SELECT s FROM objs WHERE s=? AND p=? AND o=? LIMIT 1", (s, p, o))
    return not cur.fetchone() is None
  
  def _has_data_triple_spod(self, s = None, p = None, o = None, d = ""):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM datas LIMIT 1")
        else:         cur = self.execute("SELECT s FROM datas WHERE o=? AND d=? LIMIT 1", (o,d,))
      else:
        if o is None: cur = self.execute("SELECT s FROM datas WHERE p=? LIMIT 1", (p,))
        else:         cur = self.execute("SELECT s FROM datas WHERE p=? AND o=? AND d=? LIMIT 1", (p, o, d))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM datas WHERE s=? LIMIT 1", (s,))
        else:         cur = self.execute("SELECT s FROM datas WHERE s=? AND o=? AND d=? LIMIT 1", (s, o, d))
      else:
        if o is None: cur = self.execute("SELECT s FROM datas WHERE s=? AND p=? LIMIT 1", (s, p))
        else:         cur = self.execute("SELECT s FROM datas WHERE s=? AND p=? AND o=? AND d=? LIMIT 1", (s, p, o, d))
    return not cur.fetchone() is None
  
  def _del_obj_triple_raw_spo(self, s, p, o):
    if s is None:
      if p is None:
        if o is None: self.execute("DELETE FROM objs")
        else:         self.execute("DELETE FROM objs WHERE o=?", (o,))
      else:
        if o is None: self.execute("DELETE FROM objs WHERE p=?", (p,))
        else:         self.execute("DELETE FROM objs WHERE p=? AND o=?", (p, o,))
    else:
      if p is None:
        if o is None: self.execute("DELETE FROM objs WHERE s=?", (s,))
        else:         self.execute("DELETE FROM objs WHERE s=? AND o=?", (s, o,))
      else:
        if o is None: self.execute("DELETE FROM objs WHERE s=? AND p=?", (s, p,))
        else:         self.execute("DELETE FROM objs WHERE s=? AND p=? AND o=?", (s, p, o,))
        
  def _del_data_triple_raw_spodd(self, s, p, o, d):
    if s is None:
      if p is None:
        if o is None:   self.execute("DELETE FROM datas")
        elif d is None: self.execute("DELETE FROM datas WHERE o=?", (o,))
        else:           self.execute("DELETE FROM datas WHERE o=? AND d=?", (o, d,))
      else:
        if o is None:   self.execute("DELETE FROM datas WHERE p=?", (p,))
        elif d is None: self.execute("DELETE FROM datas WHERE p=? AND o=?", (p, o,))
        else:           self.execute("DELETE FROM datas WHERE p=? AND o=? AND d=?", (p, o, d,))
    else:
      if p is None:
        if o is None:   self.execute("DELETE FROM datas WHERE s=?", (s,))
        elif d is None: self.execute("DELETE FROM datas WHERE s=? AND o=?", (s, o,))
        else:           self.execute("DELETE FROM datas WHERE s=? AND o=? AND d=?", (s, o, d,))
      else:
        if o is None:   self.execute("DELETE FROM datas WHERE s=? AND p=?", (s, p,))
        elif d is None: self.execute("DELETE FROM datas WHERE s=? AND p=? AND o=?", (s, p, o,))
        else:           self.execute("DELETE FROM datas WHERE s=? AND p=? AND o=? AND d=?", (s, p, o, d,))
        
  def _punned_entities(self):
    from owlready2.base import rdf_type, owl_class, owl_named_individual
    cur = self.execute("SELECT q1.s FROM objs q1, objs q2 WHERE q1.s=q2.s AND q1.p=? AND q2.p=? AND q1.o=? AND q2.o=?", (rdf_type, rdf_type, owl_class, owl_named_individual))
    return [storid for (storid,) in cur.fetchall()]
  
  
  def __bool__(self): return True # Reimplemented to avoid calling __len__ in this case
  def __len__(self):
    return self.execute("SELECT COUNT() FROM quads").fetchone()[0]

  
#  def get_equivs_s_o(self, s):
#    for (x,) in self.execute("""
#WITH RECURSIVE transit(x)
#AS (  SELECT o FROM equivs WHERE s=?
#UNION SELECT equivs.o FROM equivs, transit WHERE equivs.s=transit.x)
#SELECT DISTINCT x FROM transit""", (s,)).fetchall(): yield x
    
    
  # Reimplemented using RECURSIVE SQL structure, for performance
  def _get_obj_triples_transitive_sp(self, s, p):
    #print(self._unabbreviate(s), self._unabbreviate(p))
    #if self._unabbreviate(s) == "http://wikidata.dbpedia.org/ontology/Person":
    #  if self._unabbreviate(p) == "http://www.w3.org/2000/01/rdf-schema#subClassOf":
    #    oirorejf
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT o FROM objs WHERE s=? AND p=?
UNION ALL SELECT objs.o FROM objs, transit WHERE objs.s=transit.x AND objs.p=?)
SELECT DISTINCT x FROM transit""", (s, p, p)).fetchall(): yield x

  # Reimplemented using RECURSIVE SQL structure, for performance
  def _get_obj_triples_transitive_po(self, p, o):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT s FROM objs WHERE p=? AND o=?
UNION ALL SELECT objs.s FROM objs, transit WHERE objs.p=? AND objs.o=transit.x)
SELECT DISTINCT x FROM transit""", (p, o, p)).fetchall(): yield x

# Slower than Python implementation
#  def _get_obj_triples_transitive_sym2(self, s, p):
#    r = { s }
#    for (s, o) in self.execute("""
#WITH RECURSIVE transit(s,o)
#AS (  SELECT s,o from objs WHERE (s=? OR o=?) AND (p=?)
#    UNION SELECT objs.s,quads.o FROM objs, transit WHERE (quads.s=transit.s OR objs.o=transit.o OR objs.s=transit.o OR objs.o=transit.s) AND objs.p=?)
#SELECT s, o FROM transit""", (s, s, p, p)):
#      r.add(s)
#      r.add(o)
#    yield from r
    

  def _destroy_collect_storids(self, destroyed_storids, modified_relations, storid):
    for (blank_using,) in list(self.execute("""SELECT s FROM quads WHERE o=? AND p IN (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AND s < 0""" % (
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
        
    for (c, blank_using) in list(self.execute("""SELECT c, s FROM objs WHERE o=? AND p=%s AND s < 0""" % (
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
    b         = self._get_obj_triple_sp_o(blank, rdf_rest)
    while b != rdf_nil:
      nexts.append(b)
      length += 1
      b       = self._get_obj_triple_sp_o(b, rdf_rest)
      
    b         = self._get_obj_triple_po_s(rdf_rest, blank)
    if b:
      while b:
        previouss.append(b)
        length += 1
        root    = b
        b       = self._get_obj_triple_po_s(rdf_rest, b)
    else:
      root = blank
      
    list_user = self.execute("SELECT s FROM objs WHERE o=? LIMIT 1", (root,)).fetchone()
    if list_user: list_user = list_user[0]
    return list_user, root, previouss, nexts, length
  
  def destroy_entity(self, storid, destroyer, relation_updater):
    destroyed_storids   = { storid }
    modified_relations  = defaultdict(set)
    self._destroy_collect_storids(destroyed_storids, modified_relations, storid)
    
    for s,p in self.execute("SELECT DISTINCT s,p FROM objs WHERE o IN (%s)" % ",".join(["?" for i in destroyed_storids]), tuple(destroyed_storids)):
      if not s in destroyed_storids:
        modified_relations[s].add(p)
        
    # Two separate loops because high level destruction must be ended before removing from the quadstore (high level may need the quadstore)
    for storid in destroyed_storids:
      destroyer(storid)
      
    for storid in destroyed_storids:
      self.execute("DELETE FROM objs  WHERE s=? OR o=?", (storid, storid))
      self.execute("DELETE FROM datas WHERE s=?", (storid,))
      
    for s, ps in modified_relations.items():
      relation_updater(destroyed_storids, s, ps)
      
    return destroyed_storids
  
  def _iter_ontology_iri(self, c = None):
    if c:
      return self.execute("SELECT iri FROM ontologies WHERE c=?", (c,)).fetchone()[0]
    else:
      return self.execute("SELECT c, iri FROM ontologies").fetchall()
    
  # def _iter_triples(self, quads = False, sort_by_s = False, c = None):
  #   quad_cursor = self.db.cursor() # Use a new cursor => can iterate without loading all data in a big list, while still being able to query the default cursor
  #   data_cursor = self.db.cursor() # Use a new cursor => can iterate without loading all data in a big list, while still being able to query the default cursor
  #   sql = ""
  #   if c:         sql += " WHERE c=%s" % c
  #   if sort_by_s: sql += " ORDER BY s"

  #   if quads:
  #     quad_cursor.execute("SELECT s,p,o,NULL,c FROM quads %s" % sql)
  #     data_cursor.execute("SELECT s,p,o,d,c FROM datas %s" % sql)
  #   else:
  #     quad_cursor.execute("SELECT s,p,o,NULL FROM quads %s" % sql)
  #     data_cursor.execute("SELECT s,p,o,d FROM datas %s" % sql)
      
  #   if sort_by_s:
  #     yield from group_iters(quad_cursor, data_cursor)
  #   else:
  #     yield from quad_cursor
  #     yield from data_cursor
      
  def _iter_triples(self, quads = False, sort_by_s = False, c = None):
    cursor = self.db.cursor() # Use a new cursor => can iterate without loading all data in a big list, while still being able to query the default cursor
    sql = ""
    if c:         sql += " WHERE c=%s" % c
    if sort_by_s: sql += " ORDER BY s"

    if quads:
      cursor.execute("SELECT c,s,p,o,d FROM quads %s" % sql)
    else:
      cursor.execute("SELECT s,p,o,d FROM quads %s" % sql)
      
    return cursor
      
  def get_fts_prop_storid(self): return self.prop_fts
  
  def enable_full_text_search(self, prop_storid):
    self.prop_fts.add(prop_storid)
    
    self.execute("""INSERT INTO prop_fts VALUES (?)""", (prop_storid,));
    
    self.execute("""CREATE VIRTUAL TABLE fts_%s USING fts5(o, d, content=datas, content_rowid=rowid)""" % prop_storid)
    self.execute("""INSERT INTO fts_%s(rowid, o) SELECT rowid, o FROM datas WHERE p=%s""" % (prop_storid, prop_storid))
    
    self.db.cursor().executescript("""
CREATE TRIGGER fts_%s_after_insert AFTER INSERT ON datas WHEN new.p=%s BEGIN
  INSERT INTO fts_%s(rowid, o) VALUES (new.rowid, new.o);
END;
CREATE TRIGGER fts_%s_after_delete AFTER DELETE ON datas WHEN old.p=%s BEGIN
  INSERT INTO fts_%s(fts_%s, rowid, o) VALUES('delete', old.rowid, old.o);
END;
CREATE TRIGGER fts_%s_after_update AFTER UPDATE ON datas WHEN new.p=%s BEGIN
  INSERT INTO fts_%s(fts_%s, rowid, o) VALUES('delete', new.rowid, new.o);
  INSERT INTO fts_%s(rowid, o) VALUES (new.rowid, new.o);
END;""" % (prop_storid, prop_storid, prop_storid,   prop_storid, prop_storid, prop_storid, prop_storid,   prop_storid, prop_storid, prop_storid, prop_storid, prop_storid))
  
  def disable_full_text_search(self, prop_storid):
    if not isinstance(prop_storid, int): prop_storid = prop_storid.storid
    self.prop_fts.discard(prop_storid)
    
    self.execute("""DELETE FROM prop_fts WHERE storid = ?""", (prop_storid,))
    self.execute("""DROP TABLE fts_%s""" % prop_storid)
    self.execute("""DROP TRIGGER fts_%s_after_insert""" % prop_storid)
    self.execute("""DROP TRIGGER fts_%s_after_delete""" % prop_storid)
    self.execute("""DROP TRIGGER fts_%s_after_update""" % prop_storid)
    



    
class SubGraph(BaseSubGraph):
  def __init__(self, parent, onto, c, db):
    BaseSubGraph.__init__(self, parent, onto)
    self.c      = c
    self.db     = db
    self.execute          = db.execute
    self._abbreviate       = parent._abbreviate
    self._unabbreviate     = parent._unabbreviate
    self._new_numbered_iri = parent._new_numbered_iri
    
    self.parent.onto_2_subgraph[onto] = self
    
  def create_parse_func(self, filename = None, delete_existing_triples = True, datatype_attr = "http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype"):
    objs         = []
    datas        = []
    new_abbrevs  = []
    
    cur = self.db.cursor()
    
    if delete_existing_triples:
      cur.execute("DELETE FROM objs WHERE c=?", (self.c,))
      cur.execute("DELETE FROM datas WHERE c=?", (self.c,))
      
    if cur.execute("""SELECT COUNT() FROM ontologies""").fetchone()[0] < 2:
      cur.execute("""DROP INDEX IF EXISTS index_resources_iri""")
      cur.execute("""DROP INDEX IF EXISTS index_objs_sp""")
      cur.execute("""DROP INDEX IF EXISTS index_objs_po""")
      cur.execute("""DROP INDEX IF EXISTS index_datas_sp""")
      cur.execute("""DROP INDEX IF EXISTS index_datas_po""")
      reindex = True
    else:
      reindex = False
      
    # XXX
      
    # Re-implement _abbreviate() for speed
    if self.parent._abbreviate_d is None:
      abbrevs = {}
      def _abbreviate(iri):
        storid = abbrevs.get(iri)
        if not storid is None: return storid
        r = cur.execute("SELECT storid FROM resources WHERE iri=? LIMIT 1", (iri,)).fetchone()
        if r:
          abbrevs[iri] = r[0]
          return r[0]
        self.parent.current_resource += 1
        storid = self.parent.current_resource
        new_abbrevs.append((storid, iri))
        abbrevs[iri] = storid
        return storid
    else:
      abbrevs = self.parent._abbreviate_d
      def _abbreviate(iri):
        storid = abbrevs.get(iri)
        if not storid is None: return storid
        
        self.parent.current_resource += 1
        storid = self.parent.current_resource
        new_abbrevs.append((storid, iri))
        abbrevs[iri] = storid
        return storid
      
    def insert_objs():
      nonlocal objs, new_abbrevs
      if owlready2.namespace._LOG_LEVEL: print("* OwlReady2 * Importing %s object triples from ontology %s ..." % (len(objs), self.onto.base_iri), file = sys.stderr)
      cur.executemany("INSERT INTO resources VALUES (?,?)", new_abbrevs)
      cur.executemany("INSERT INTO objs VALUES (%s,?,?,?)" % self.c, objs)
      objs        .clear()
      new_abbrevs .clear()
      
    def insert_datas():
      nonlocal datas, new_abbrevs
      if owlready2.namespace._LOG_LEVEL: print("* OwlReady2 * Importing %s data triples from ontology %s ..." % (len(datas), self.onto.base_iri), file = sys.stderr)
      cur.executemany("INSERT INTO datas VALUES (%s,?,?,?,?)" % self.c, datas)
      datas.clear()
      
    def on_prepare_obj(s, p, o):
      if isinstance(s, str): s = _abbreviate(s)
      if isinstance(o, str): o = _abbreviate(o)
      objs.append((s, _abbreviate(p), o))
      if len(objs) > 1000000: insert_objs()
      
    def on_prepare_data(s, p, o, d):
      if isinstance(s, str): s = _abbreviate(s)
      if d and (not d.startswith("@")): d = _abbreviate(d)
      datas.append((s, _abbreviate(p), o, d or 0))
      if len(datas) > 1000000: insert_datas()
      
      
    def on_finish():
      if filename: date = os.path.getmtime(filename)
      else:        date = time.time()
      
      insert_objs()
      insert_datas()
      
      if reindex:
        cur.execute("""CREATE UNIQUE INDEX index_resources_iri ON resources(iri)""")
        if self.parent.indexed:
          cur.execute("""CREATE INDEX index_objs_sp ON objs(s,p)""")
          cur.execute("""CREATE INDEX index_objs_po ON objs(p,o)""")
          cur.execute("""CREATE INDEX index_datas_sp ON datas(s,p)""")
          cur.execute("""CREATE INDEX index_datas_po ON datas(p,o)""")
          
      t0 = time.time()
      onto_base_iri = cur.execute("SELECT resources.iri FROM objs, resources WHERE objs.c=? AND objs.o=? AND resources.storid=objs.s LIMIT 1", (self.c, owl_ontology)).fetchone()
      if onto_base_iri: onto_base_iri = onto_base_iri[0]
      else:             onto_base_iri = ""
      
      if onto_base_iri.endswith("/"):
        cur.execute("UPDATE ontologies SET last_update=?,iri=? WHERE c=?", (date, onto_base_iri, self.c,))
      elif onto_base_iri:
        onto_base_iri = self.parent.fix_base_iri(onto_base_iri, self.c)
        cur.execute("UPDATE ontologies SET last_update=?,iri=? WHERE c=?", (date, onto_base_iri, self.c,))
      else:
        cur.execute("UPDATE ontologies SET last_update=? WHERE c=?", (date, self.c,))
        
      self.parent.select__abbreviate_method()
      
      return onto_base_iri
    
    
    return objs, datas, on_prepare_obj, on_prepare_data, insert_objs, insert_datas, self.parent.new_blank_node, _abbreviate, on_finish


  def context_2_user_context(self, c): return self.parent.c_2_onto[c]
 
  def add_ontology_alias(self, iri, alias):
    self.execute("INSERT into ontology_alias VALUES (?,?)", (iri, alias))
    
  def get_last_update_time(self):
    return self.execute("SELECT last_update FROM ontologies WHERE c=?", (self.c,)).fetchone()[0]
  
  def set_last_update_time(self, t):
    self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (t, self.c))
  
  def destroy(self):
    self.execute("DELETE FROM objs WHERE c=?",      (self.c,))
    self.execute("DELETE FROM datas WHERE c=?",      (self.c,))
    self.execute("DELETE FROM ontologies WHERE c=?", (self.c,))
    
  def _set_obj_triple_raw_spo(self, s, p, o):
    if (s is None) or (p is None) or (o is None): raise ValueError
    self.execute("DELETE FROM objs WHERE c=? AND s=? AND p=?", (self.c, s, p,))
    self.execute("INSERT INTO objs VALUES (?, ?, ?, ?)", (self.c, s, p, o))
    
  def _add_obj_triple_raw_spo(self, s, p, o):
    if (s is None) or (p is None) or (o is None): raise ValueError
    self.execute("INSERT INTO objs VALUES (?, ?, ?, ?)", (self.c, s, p, o))
    
  def _del_obj_triple_raw_spo(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: self.execute("DELETE FROM objs WHERE c=?", (self.c,))
        else:         self.execute("DELETE FROM objs WHERE c=? AND o=?", (self.c, o,))
      else:
        if o is None: self.execute("DELETE FROM objs WHERE c=? AND p=?", (self.c, p,))
        else:         self.execute("DELETE FROM objs WHERE c=? AND p=? AND o=?", (self.c, p, o,))
    else:
      if p is None:
        if o is None: self.execute("DELETE FROM objs WHERE c=? AND s=?", (self.c, s,))
        else:         self.execute("DELETE FROM objs WHERE c=? AND s=? AND o=?", (self.c, s, o,))
      else:
        if o is None: self.execute("DELETE FROM objs WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        else:         self.execute("DELETE FROM objs WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o,))
        
  def _set_data_triple_raw_spodd(self, s, p, o, d):
    if (s is None) or (p is None) or (o is None) or (d is None): raise ValueError
    self.execute("DELETE FROM datas WHERE c=? AND s=? AND p=?", (self.c, s, p,))
    self.execute("INSERT INTO datas VALUES (?, ?, ?, ?, ?)", (self.c, s, p, o, d))
    
  def _add_data_triple_raw_spodd(self, s, p, o, d):
    if (s is None) or (p is None) or (o is None) or (d is None): raise ValueError
    self.execute("INSERT INTO datas VALUES (?, ?, ?, ?, ?)", (self.c, s, p, o, d))
    

  def _del_data_triple_raw_spodd(self, s, p, o, d):
    if s is None:
      if p is None:
        if o is None:   self.execute("DELETE FROM datas WHERE c=?", (self.c,))
        elif d is None: self.execute("DELETE FROM datas WHERE c=? AND o=?", (self.c, o,))
        else:           self.execute("DELETE FROM datas WHERE c=? AND o=? AND d=?", (self.c, o, d,))
      else:
        if o is None:   self.execute("DELETE FROM datas WHERE c=? AND p=?", (self.c, p,))
        elif d is None: self.execute("DELETE FROM datas WHERE c=? AND p=? AND o=?", (self.c, p, o,))
        else:           self.execute("DELETE FROM datas WHERE c=? AND p=? AND o=? AND d=?", (self.c, p, o, d,))
    else:
      if p is None:
        if o is None:   self.execute("DELETE FROM datas WHERE c=? AND s=?", (self.c, s,))
        elif d is None: self.execute("DELETE FROM datas WHERE c=? AND s=? AND o=?", (self.c, s, o,))
        else:           self.execute("DELETE FROM datas WHERE c=? AND s=? AND o=? AND d=?", (self.c, s, o, d,))
      else:
        if o is None:   self.execute("DELETE FROM datas WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        elif d is None: self.execute("DELETE FROM datas WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o,))
        else:           self.execute("DELETE FROM datas WHERE c=? AND s=? AND p=? AND o=? AND d=?", (self.c, s, p, o, d,))

  def _has_obj_triple_spo(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM objs WHERE c=? LIMIT 1", (self.c,))
        else:         cur = self.execute("SELECT s FROM objs WHERE c=? AND o=? LIMIT 1", (self.c, o))
      else:
        if o is None: cur = self.execute("SELECT s FROM objs WHERE c=? AND p=? LIMIT 1", (self.c, p,))
        else:         cur = self.execute("SELECT s FROM objs WHERE c=? AND p=? AND o=? LIMIT 1", (self.c, p, o))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM objs WHERE c=? AND s=? LIMIT 1", (self.c, s,))
        else:         cur = self.execute("SELECT s FROM objs WHERE c=? AND s=? AND o=? LIMIT 1", (self.c, s, o))
      else:
        if o is None: cur = self.execute("SELECT s FROM objs WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,))
        else:         cur = self.execute("SELECT s FROM objs WHERE c=? AND s=? AND p=? AND o=? LIMIT 1", (self.c, s, p, o))
    return not cur.fetchone() is None
       
  def _has_data_triple_spod(self, s = None, p = None, o = None, d = ""):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM datas WHERE c=? LIMIT 1", (self.c,))
        else:         cur = self.execute("SELECT s FROM datas WHERE c=? AND o=? AND d=? LIMIT 1", (self.c, o, d))
      else:
        if o is None: cur = self.execute("SELECT s FROM datas WHERE c=? AND p=? LIMIT 1", (self.c, p,))
        else:         cur = self.execute("SELECT s FROM datas WHERE c=? AND p=? AND o=? AND d=? LIMIT 1", (self.c, p, o, d))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s FROM datas WHERE c=? AND s=? LIMIT 1", (self.c, s,))
        else:         cur = self.execute("SELECT s FROM datas WHERE c=? AND s=? AND o=? AND d=? LIMIT 1", (self.c, s, o, d))
      else:
        if o is None: cur = self.execute("SELECT s FROM datas WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,))
        else:         cur = self.execute("SELECT s FROM datas WHERE c=? AND s=? AND p=? AND o=? AND d=? LIMIT 1", (self.c, s, p, o, d))
    return not cur.fetchone() is None
    
        
  def _get_obj_triples_spo_spo(self, s = None, p = None, o = None):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs WHERE c=?", (self.c,))
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE c=? AND o=?", (self.c, o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs WHERE c=? AND p=?", (self.c, p,))
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE c=? AND p=? AND o=?", (self.c, p, o,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs WHERE c=? AND s=?", (self.c, s,))
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE c=? AND s=? AND o=?", (self.c, s, o,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o FROM objs WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        else:         cur = self.execute("SELECT s,p,o FROM objs WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o,))
    return cur.fetchall()

  def _get_data_triples_spod_spod(self, s, p, o, d = ""):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=?", (self.c,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND o=?", (self.c, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND o=? AND d=?", (self.c, o,d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND p=?", (self.c, p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND p=? AND o=?", (self.c, p, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND p=? AND o=? AND d=?", (self.c, p, o, d,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND s=?", (self.c, s,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND s=? AND o=?", (self.c, s, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND s=? AND o=? AND d=?", (self.c, s, o, d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o))
          else:
            cur = self.execute("SELECT s,p,o,d FROM datas WHERE c=? AND s=? AND p=? AND o=? AND d=?", (self.c, s, p, o, d,))
    return cur.fetchall()

  def _get_triples_spod_spod(self, s, p, o, d = ""):
    if s is None:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=?", (self.c,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND o=?", (self.c, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND o=? AND d=?", (self.c, o,d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND p=?", (self.c, p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND p=? AND o=?", (self.c, p, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND p=? AND o=? AND d=?", (self.c, p, o, d,))
    else:
      if p is None:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND s=?", (self.c, s,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND s=? AND o=?", (self.c, s, o,))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND s=? AND o=? AND d=?", (self.c, s, o, d,))
      else:
        if o is None: cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND s=? AND p=?", (self.c, s, p,))
        else:
          if d is None:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND s=? AND p=? AND o=?", (self.c, s, p, o))
          else:
            cur = self.execute("SELECT s,p,o,d FROM quads WHERE c=? AND s=? AND p=? AND o=? AND d=?", (self.c, s, p, o, d,))
    return cur.fetchall()

  
  def _get_obj_triples_s_po(self, s):
    return self.execute("SELECT p,o FROM objs WHERE c=? AND s=?", (self.c, s,)).fetchall()
  
  def _get_obj_triples_sp_o(self, s, p):
    for (x,) in self.execute("SELECT o FROM objs WHERE c=? AND s=? AND p=?", (self.c, s, p,)).fetchall(): yield x
    
  def _get_obj_triples_sp_co(self, s, p):
    return self.execute("SELECT c,o FROM objs WHERE c=? AND s=? AND p=?", (self.c, s, p,)).fetchall()
    
  def _get_triples_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM quads WHERE c=? AND s=? AND p=?", (self.c, s, p)).fetchall()
    
  def _get_data_triples_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM datas WHERE c=? AND s=? AND p=?", (self.c, s, p,)).fetchall()

  def _get_data_triples_s_pod(self, s):
    return self.execute("SELECT p,o,d FROM datas WHERE c=? AND s=?", (self.c, s,)).fetchall()
    
  def _get_triples_s_pod(self, s):
    return self.execute("SELECT p,o,d FROM quads WHERE c=? AND s=?", (self.c, s,)).fetchall()
    
  def _get_obj_triples_po_s(self, p, o):
    for (x,) in self.execute("SELECT s FROM objs WHERE c=? AND p=? AND o=?", (self.c, p, o,)).fetchall(): yield x
    
  def _get_obj_triple_sp_o(self, s, p):
    r = self.execute("SELECT o FROM objs WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,)).fetchone()
    if r: return r[0]
    return None
  
  def _get_triple_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM quads WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p)).fetchone()
    
  def _get_data_triple_sp_od(self, s, p):
    return self.execute("SELECT o,d FROM datas WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,)).fetchone()
  
  def _get_obj_triple_po_s(self, p, o):
    r = self.execute("SELECT s FROM objs WHERE c=? AND p=? AND o=? LIMIT 1", (self.c, p, o,)).fetchone()
    if r: return r[0]
    return None
  
  def _get_triples_s_p(self, s):
    for (x,) in self.execute("SELECT DISTINCT p FROM quads WHERE c=? AND s=?", (self.c, s,)).fetchall(): yield x
    
  def _get_obj_triples_cspo_cspo(self, c, s, p, o):
    return [(self.c, s, p, o) for (s, p, o) in self._get_obj_triples_spo_spo(s, p, o)]
  
  def search(self, prop_vals, c = None, debug = False): return self.parent.search(prop_vals, self.c, debug)
  
  def __len__(self):
    return self.execute("SELECT COUNT() FROM quads WHERE c=?", (self.c,)).fetchone()[0]
  
  
  def _iter_ontology_iri(self, c = None):
    if c:
      return self.execute("SELECT iri FROM ontologies WHERE c=?", (c,)).fetchone()[0]
    else:
      return self.execute("SELECT c, iri FROM ontologies").fetchall()
    
  def _iter_triples(self, quads = False, sort_by_s = False):
    return self.parent._iter_triples(quads, sort_by_s, self.c)
  
  def _refactor(self, storid, new_iri): return self.parent._refactor(storid, new_iri)
    
  # Reimplemented using RECURSIVE SQL structure, for performance
  def _get_obj_triples_transitive_sp(self, s, p):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT o FROM objs WHERE c=? AND s=? AND p=?
UNION ALL SELECT objs.o FROM objs, transit WHERE objs.c=? AND objs.s=transit.x AND objs.p=?)
SELECT DISTINCT x FROM transit""", (self.c, s, p, self.c, p)).fetchall(): yield x
  
  # Reimplemented using RECURSIVE SQL structure, for performance
  def _get_obj_triples_transitive_po(self, p, o):
    for (x,) in self.execute("""
WITH RECURSIVE transit(x)
AS (      SELECT s FROM objs WHERE c=? AND p=? AND o=?
UNION ALL SELECT objs.s FROM objs, transit WHERE objs.c=? AND objs.p=? AND objs.o=transit.x)
SELECT DISTINCT x FROM transit""", (self.c, p, o, self.c, p)).fetchall(): yield x

#  def _get_obj_triples_transitive_sym(self, s, p):
#    r = { s }
#    for (s, o) in self.execute("""
#WITH RECURSIVE transit(s,o)
#AS (  SELECT s,o from objs WHERE (s=? OR o=?) AND p=? AND c=?
#    UNION SELECT objs.s,quads.o FROM objs, transit WHERE (quads.s=transit.s OR objs.o=transit.o OR objs.s=transit.o OR objs.o=transit.s) AND objs.p=? AND objs.c=?)
#SELECT s, o FROM transit""", (s, s, p, self.c, p, self.c)):
#      r.add(s)
#      r.add(o)
#    yield from r



_NEXT_SEARCH_ID = 0
class _SearchList(LazyList):
  def __init__(self, world, prop_vals, c = None):
    global _NEXT_SEARCH_ID
    
    super().__init__(self._do_search)
    self.world     = world
    self.prop_vals = prop_vals
    self._c         = c
    
    _NEXT_SEARCH_ID += 1
    self.id = _NEXT_SEARCH_ID
    
    self.tables            = []
    self.conditions        = []
    self.params            = []
    self.alternatives      = []
    self.excepts           = []
    self.except_conditions = []
    self.except_params     = []
    self.nested_searchs    = []
    
    n = 0
    for k, v, d in prop_vals:
      if v is None:
        self.excepts.append(k)
        continue
      
      n += 1
      i = "%s_%s" % (self.id, n)
      if n == 1: self.target = i
      if d is None:
        self.tables.append("objs q%s" % i)
      else:
        self.tables.append("datas q%s" % i)
        
      if not c is None:
        self.conditions  .append("q%s.c = ?" % i)
        self.params      .append(c)
        
      if   k == " iri":
        if n > 1: self.conditions.append("q%s.s = q%s.s" % (i, self.target))
        self.tables    .append("resources")
        self.conditions.append("resources.storid = q%s.s" % i)
        if "*" in v: self.conditions.append("resources.iri GLOB ?")
        else:        self.conditions.append("resources.iri = ?")
        self.params.append(v)
        
      elif k == " is_a":
        if n > 1: self.conditions.append("q%s.s = q%s.s" % (i, self.target))
        if isinstance(v, _SearchList):
          self.conditions.append("(q%s.p = %s OR q%s.p = %s) AND q%s.o = q%s.s" % (i, rdf_type, i, rdfs_subclassof, i, v.target))
          self.nested_searchs.append(v)
          self.nested_searchs.extend(v.nested_searchs)
        else:
          self.conditions.append("(q%s.p = %s OR q%s.p = %s) AND q%s.o IN (%s)" % (i, rdf_type, i, rdfs_subclassof, i, ",".join("?" for i in v)))
          self.params    .extend(v)
          
      elif k == " type":
        if n > 1: self.conditions.append("q%s.s = q%s.s" % (i, self.target))
        if isinstance(v, _SearchList):
          self.conditions.append("q%s.p = %s AND q%s.o = q%s.s" % (i, rdf_type, i, v.target))
          self.nested_searchs.append(v)
          self.nested_searchs.extend(v.nested_searchs)
        else:
          self.conditions.append("q%s.p = %s AND q%s.o IN (%s)" % (i, rdf_type, i, ",".join("?" for i in v)))
          self.params    .extend(v)
          
      elif k == " subclass_of":
        if n > 1: self.conditions.append("q%s.s = q%s.s" % (i, self.target))
        if isinstance(v, _SearchList):
          self.conditions.append("q%s.p = %s AND q%s.o = q%s.s" % (i, rdfs_subclassof, i, v.target))
          self.nested_searchs.append(v)
          self.nested_searchs.extend(v.nested_searchs)
        else:
          self.conditions.append("q%s.p = %s AND q%s.o IN (%s)" % (i, rdfs_subclassof, i, ",".join("?" for i in v)))
          self.params    .extend(v)
          
      elif isinstance(k, tuple): # Prop with inverse
        if n == 1: # Does not work if it is the FIRST => add a dumb first.
          n += 1
          i = "%s_%s" % (self.id, n)
          self.tables.append("objs q%s" % i)
          if not c is None:
            self.conditions  .append("q%s.c = ?" % i)
            self.params      .append(c)
            
        if   v == "*":
          cond1 = "q%s.s = q%s.s AND q%s.p = ?" % (i, self.target, i)
          cond2 = "q%s.o = q%s.s AND q%s.p = ?" % (i, self.target, i)
          params1 = [k[0]]
          params2 = [k[1]]
        elif isinstance(v, _SearchList):
          cond1 = "q%s.s = q%s.s AND q%s.p = ? AND q%s.o = q%s.s" % (i, self.target, i, i, v.target)
          cond2 = "q%s.o = q%s.s AND q%s.p = ? AND q%s.s = q%s.s" % (i, self.target, i, i, v.target)
          params1 = [k[0]]
          params2 = [k[1]]
          self.nested_searchs.append(v)
          self.nested_searchs.extend(v.nested_searchs)
        else:
          cond1 = "q%s.s = q%s.s AND q%s.p = ? AND q%s.o = ?" % (i, self.target, i, i)
          cond2 = "q%s.o = q%s.s AND q%s.p = ? AND q%s.s = ?" % (i, self.target, i, i)
          params1 = [k[0], v]
          params2 = [k[1], v]
        self.alternatives.append(((cond1, params1), (cond2, params2)))
        
      else: # Prop without inverse
        if n > 1: self.conditions.append("q%s.s = q%s.s" % (i, self.target))
        if isinstance(v, FTS):
          self.tables    .append("fts_%s" % k)
          self.conditions.append("q%s.rowid = fts_%s.rowid" % (i, k))
          self.conditions.append("fts_%s MATCH ?" % k)
          self.params    .append(v)
          if v.lang != "":
            self.conditions.append("fts_%s.d = ?" % (k,))
            self.params    .append("@%s" % v.lang)
            
        else:
          self.conditions.append("q%s.p = ?" % i)
          self.params    .append(k)
          if   isinstance(v, _SearchList):
            self.conditions.append("q%s.o = q%s.s" % (i, v.target))
            self.params    .append(v)
            self.nested_searchs.append(v)
            self.nested_searchs.extend(v.nested_searchs)
            
          elif isinstance(v, NumS):
            for operator, value in v.operators_and_values:
              self.conditions.append("q%s.o %s ?" % (i, operator))
              self.params    .append(value)
              
          elif isinstance(v, str) and ("*" in v):
            if   v == "*":
              self.conditions.append("q%s.o GLOB '*'" % i)
            else:
              self.conditions.append("q%s.o GLOB ?" % i)
              self.params    .append(v)
              
          else:
            self.conditions.append("q%s.o = ?" % i)
            self.params    .append(v)
            if d and (d != "*"):
              self.conditions.append("q%s.d = ?" % i)
              self.params    .append(d)
              
    if self.excepts:
      for except_p in self.excepts:  # Use only quads because it may contain several properties mixing objs and datas
        self.except_conditions.append("quads.s = candidates.s AND quads.p = ?")
        self.except_params    .append(except_p[0])
        if isinstance(except_p, tuple): # Prop with inverse
          self.except_conditions.append("quads.o = candidates.s AND quads.p = ?")
          self.except_params    .append(except_p[1])

          
  def sql_request(self):
    tables     = self.tables     + [x for search in self.nested_searchs for x in search.tables]
    conditions = self.conditions + [x for search in self.nested_searchs for x in search.conditions]
    params     = self.params     + [x for search in self.nested_searchs for x in search.params]
    
    if self.nested_searchs:
      for search in self.nested_searchs:
        if search.excepts: raise ValueError("Nested searches with exclusions are not supported!")
      
    if not self.alternatives:
      sql = "SELECT DISTINCT q%s.s from %s WHERE %s" % (self.target, ", "   .join(tables), " AND ".join(conditions))
      
    else:
      conditions0 = conditions
      params0     = params
      params      = []
      sqls        = []
      for combination in all_combinations(self.alternatives):
        combination_conditions, combination_paramss = zip(*combination)
        sql = "SELECT q%s.s from %s WHERE %s" % (self.target, ", ".join(tables), " AND ".join(conditions0 + list(combination_conditions)))
        sqls.append(sql)
        params.extend(params0)
        for combination_params in combination_paramss: params.extend(combination_params)
      sql = "SELECT DISTINCT * FROM (\n%s\n)" % "\nUNION ALL\n".join(sqls)
      
    if self.excepts:
      if sql.startswith("SELECT DISTINCT"): sql = "SELECT %s" % sql[16:]
      sql = """WITH candidates(s) AS (%s)
SELECT DISTINCT s FROM candidates
EXCEPT %s""" % (sql, "\nUNION ALL ".join("""SELECT candidates.s FROM candidates, quads WHERE %s""" % except_condition for except_condition in self.except_conditions))
      params = params + self.except_params
      
    return sql, params

  
  def _do_search(self):
    sql, params = self.sql_request()
    return (self.world._get_by_storid(o) for (o,) in self.world.graph.execute(sql, params).fetchall())
  
  def _do_search_rdf(self):
    sql, params = self.sql_request()
    return self.world.graph.execute(sql, params).fetchall()
    
  def dump(self):
    sql, params = self.sql_request()
    print("search debug:")
    print("  prop_vals = ", self.prop_vals)
    try:
      sql_with_params = sql.replace("?", "%s") % tuple(params)
      print("  req       = ", sql_with_params)
    except:
      print("  req       = ", )
      print("  params    = ", params)
    print("  params    = ", params)
    
