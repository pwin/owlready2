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

import sys, os, os.path, sqlite3, time, datetime, re
from functools import lru_cache

from owlready2.driver import *
from owlready2.util import _int_base_62
from owlready2.base import _universal_abbrev_2_iri

class Graph(BaseGraph):
  def __init__(self, filename, clone = None):
    exists        = os.path.exists(filename) and os.path.getsize(filename)
    self.db       = sqlite3.connect(filename, check_same_thread = False)
    
    self.db.execute("""PRAGMA locking_mode = EXCLUSIVE""")
    
    self.sql      = self.db.cursor()
    self.execute  = self.sql.execute
    self.fetchone = self.sql.fetchone
    self.fetchall = self.sql.fetchall
    self.c_2_onto = {}
    self.onto_2_subgraph = {}
    
    if (clone is None) and ((filename == ":memory:") or (not exists)):
      self.current_blank    = 0
      self.current_resource = 300 # 300 first values are reserved
      
      self.execute("""CREATE TABLE store (version INTEGER, current_blank INTEGER, current_resource INTEGER)""")
      self.execute("""INSERT INTO store VALUES (1, 0, 300)""")
      self.execute("""CREATE TABLE quads (c INTEGER, s TEXT, p TEXT, o TEXT)""")
      self.execute("""CREATE TABLE ontologies (c INTEGER PRIMARY KEY, iri TEXT, last_update DOUBLE)""")
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
        
      self.execute("SELECT current_blank, current_resource FROM store")
      self.current_blank, self.current_resource = self.fetchone()
      
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
    self.execute("SELECT iri FROM resources WHERE iri GLOB ? ORDER BY LENGTH(iri) DESC, iri DESC", ("%s*" % prefix,))
    while True:
      iri = self.fetchone()
      if not iri: break
      num = iri[0][len(prefix):]
      if num.isdigit(): return "%s%s" % (prefix, int(num) + 1)
    return "%s1" % prefix
  
  def refactor(self, storid, new_iri):
    self.execute("UPDATE resources SET iri=? WHERE storid=?", (new_iri, storid,))
    
  def sub_graph(self, onto):
    self.execute("SELECT c FROM ontologies WHERE iri=?", (onto.base_iri,))
    c = self.fetchone()
    if c is None:
      self.execute("INSERT INTO ontologies VALUES (NULL, ?, 0)", (onto.base_iri,))
      self.execute("SELECT c FROM ontologies WHERE iri=?", (onto.base_iri,))
      c = self.fetchone()
    c = c[0]
    self.c_2_onto[c] = onto
    
    return SubGraph(self, onto, c, self.db, self.sql)
  
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
  
  def search(self, prop_vals, c = None):
    tables = []
    conditions = []
    params = []
    i = 0
    for k, v in prop_vals:
      i += 1
      tables        .append("quads q%s" % i)
      if i > 1:
        conditions  .append("q%s.s = q1.s" % i)
      if k == "iri":
        tables      .append("resources")
        conditions  .append("resources.storid = q%s.s" % i)
        if "*" in v:
          conditions.append("resources.iri GLOB ?")
        else:
          conditions.append("resources.iri = ?")
        params      .append(v)
      else:
        if   k == "is_a":
          conditions  .append("(q%s.p = %s OR q%s.p = %s)" % (i, rdf_type, i, rdfs_subclassof))
        elif k == "type":
          conditions  .append("q%s.p = %s" % (i, rdf_type))
        elif k == "subclass_of":
          conditions  .append("q%s.p = %s" % (i, rdfs_subclassof))
        else:
          conditions  .append("q%s.p = ?" % i)
          params      .append(k)
          
        if "*" in v:
          conditions.append("q%s.o GLOB ?" % i)
        else:
          conditions.append("q%s.o = ?" % i)
        params      .append(v)
        
      if not c is None:
        conditions  .append("q%s.c = ?" % i)
        params      .append(c)
        
    req = "SELECT DISTINCT q1.s from %s WHERE %s" % (", ".join(tables), " AND ".join(conditions))
    #print(req, params)
    self.execute(req, params)
    return self.fetchall()

  def _punned_entities(self):
    from owlready2.base import rdf_type, owl_class, owl_named_individual
    self.execute("SELECT q1.s FROM quads q1, quads q2 WHERE q1.s=q2.s AND q1.p=? AND q2.p=? AND q1.o=? AND q2.o=?", (rdf_type, rdf_type, owl_class, owl_named_individual))
    return [storid for (storid,) in self.fetchall()]
  
  def __len__(self):
    return self.execute("SELECT COUNT(s) FROM quads").fetchone()[0]

  def dump(self):
    import io
    s = io.BytesIO()
    self.save(s, "ntriples")
    print(s.getvalue().decode("utf8"))
    

  
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
  
  def parse(self, f, format = None, delete_existing_triples = True, force_rdflib = False):
    import owlready2
    
    format = format or _guess_format(f)
    
    rapper = None
    
    splitter = re.compile("\s")
    #splitter = re.compile(r"^([^#].*?)\s+(.*?)\s+(.*?)\s*\.$", re.MULTILINE)
    #splitter = re.compile(r"^(.*?)\s+(.*?)\s+(.*?)\s*\.$")
    
    if   format == "ntriples":
      def get_triple():
        line = f.readline()
        while line:
          if not line.startswith("#"):
            #print(splitter.findall(line))
            #splitter.findall(line)[0]
            yield splitter.split(line[:-3], 2)
            #line = line.rsplit(" ", 1)[0]
            #yield line.split(" ", 2)
          line = f.readline()
          
      triples = get_triple()
      
    elif format == "rdfxml":
      if _has_rapper and not force_rdflib:
        import subprocess
        
        url = getattr(f, "url", "")
        if url:
          rapper = subprocess.Popen([owlready2.RAPPER_EXE, "-q", "-g", url], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        else:
          rapper = subprocess.Popen([owlready2.RAPPER_EXE, "-q", "-g", "-", "http://test.org/xxx.owl"], stdin = f, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
          
        def get_triple():
          line = rapper.stdout.readline()
          while line:
            yield line.rsplit(b" ", 1)[0].decode("unicode-escape").split(" ", 2)
            line = rapper.stdout.readline()
        triples = get_triple()
        
      else:
        import rdflib, rdflib.term
        g = rdflib.Graph()
        try:
          g.parse(f)
        except Exception as e:
          self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (0, self.c,))
          line = getattr(e, "getLineNumber", None)
          if callable(line): line = line()
          if line:
            raise OwlReadyOntologyParsingError("%s: line %s" % (e.args[0], line)) from e
          else:
            raise OwlReadyOntologyParsingError(*e.args) from e
          
        def get_triple():
          for s,p,o in g:
            if   isinstance(s, rdflib.term.URIRef ): s = "<%s>" % s
            elif isinstance(s, rdflib.term.BNode  ): s = "_:%s" % s
            p = "<%s>" % p
            if   isinstance(o, rdflib.term.URIRef ): o = "<%s>" % o
            elif isinstance(o, rdflib.term.Literal): o = o.n3()
            elif isinstance(o, rdflib.term.BNode  ): o = "_:%s" % o
            yield s,p,o
        triples = get_triple()
        
    elif format == "owlxml":
      triples = []
      def on_triple(s,p,o): triples.append((s,p,o))
      import owlready2.owlxml_2_ntriples
      try:
        owlready2.owlxml_2_ntriples.parse(f, on_triple)
      except Exception as e:
        self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (0, self.c,))
        line = getattr(e, "getLineNumber", None)
        if callable(line): line = line()
        if line:
          raise OwlReadyOntologyParsingError("%s: line %s" % (e.args[0], line)) from e
        else:
          raise OwlReadyOntologyParsingError(*e.args) from e
        
    else:
      raise ValueError("Unsupported format %s." % format)
      
    try:
      self.parse_from_ntriples_triples(triples, getattr(f, "name", ""), delete_existing_triples)
    except Exception as e:
      self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (0, self.c,))
      self.execute("DELETE FROM quads WHERE c=?", (self.c,))
      self._add_triple(self.onto.storid, rdf_type, owl_ontology)
      raise OwlReadyOntologyParsingError("Error while parsing NTriple file: line %s" % self._current_line) from e
    
    if rapper:
      error = rapper.stderr.read()
      rapper.stdout.close()
      rapper.stderr.close()
      rapper.wait()
      
      if b"Error" in error:
        self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (0, self.c,))
        self.execute("DELETE FROM quads WHERE c=?", (self.c,))
        self._add_triple(self.onto.storid, rdf_type, owl_ontology)
        raise OwlReadyOntologyParsingError("Error when parsing %s file with rapper." % format)
        
        
  def parse_from_ntriples_triples(self, triples, filename = None, delete_existing_triples = True):
    values       = []
    bn_src_2_sql = {}
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
    
    self._current_line = 1
    for s,p,o in triples:
      if   s.startswith("<"): s = abbreviate(s[1:-1])
      elif s.startswith("_"):
        bn = bn_src_2_sql.get(s)
        if bn is None:
          bn = self.parent.new_blank_node()
          bn_src_2_sql[s] = bn
        s = bn
        
      p = abbreviate(p[1:-1])
      
      if o.startswith("<"): o = abbreviate(o[1:-1])
      elif o.startswith("_"):
        bn = bn_src_2_sql.get(o)
        if bn is None:
          bn = self.parent.new_blank_node()
          bn_src_2_sql[o] = bn
        o = bn
      elif o.startswith('"'):
        v, l = o.rsplit('"', 1)
        if l.startswith("^"): o = '%s"%s' % (v, abbreviate(l[3:-1])) # Abbreviate datatype's iri
      
      values.append((s,p,o))
      self._current_line += 1
      
      #if (len(values) % 100000) == 0: print(len(values), file = sys.stderr)
      
    if filename: date = os.path.getmtime(filename)
    else:        date = time.time()
    self.execute("UPDATE ontologies SET last_update=? WHERE c=?", (date, self.c,))
    
    if delete_existing_triples: self.execute("DELETE FROM quads WHERE c=?", (self.c,))
    
    import owlready2.namespace
    if owlready2.namespace._LOG_LEVEL: print("* OwlReady 2 * Importing %s triples from ontology %s ..." % (len(values), self.onto.base_iri), file = sys.stderr)
    self.sql.executemany("INSERT INTO resources VALUES (?,?)", new_abbrevs)
    self.sql.executemany("INSERT INTO quads VALUES (%s,?,?,?)" % self.c, values)
    
    del self._current_line
    
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
    
  def get_triple_sp(self, s = None, p = None):
    r = self.execute("SELECT o FROM quads WHERE c=? AND s=? AND p=? LIMIT 1", (self.c, s, p,)).fetchone()
    if r: return r[0]
    return None
  
  def get_triple_po(self, p = None, o = None):
    r = self.execute("SELECT s FROM quads WHERE c=? AND p=? AND o=? LIMIT 1", (self.c, p, o,)).fetchone()
    if r: return r[0]
    return None
  
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
    return self.execute("SELECT COUNT(s) FROM quads WHERE c=?", (self.c,)).fetchone()[0]

  def dump(self):
    import io
    s = io.BytesIO()
    self.save(s, "ntriples")
    print(s.getvalue().decode("utf8"))
  
  
def _save(f, format, graph, c = None, force_rdflib = False):
  unabbreviate = lru_cache(None)(graph.unabbreviate)
  
  if   format == "ntriples":
    if c is None: graph.sql.execute("SELECT s,p,o FROM quads")
    else:         graph.sql.execute("SELECT s,p,o FROM quads WHERE c=?", (c,))
    for s,p,o in graph.sql.fetchall():
      if   s.startswith("_"): s = "_:bn%s" % s[1:]
      else:                   s = "<%s>" % unabbreviate(s)
      p = "<%s>" % unabbreviate(p)
      if   o.startswith("_"): o = "_:bn%s" % o[1:]
      elif o.startswith('"'):
        if not o.endswith('"'):
          v, l = o.rsplit('"', 1)
          v = v[1:].replace('"', '\\"')
          if   l.startswith("@"): o = '"%s"%s' % (v, l)
          else:                   o = '"%s"^^<%s>' % (v, unabbreviate(l)) # Unabbreviate datatype's iri
      else: o = "<%s>" % unabbreviate(o)
      #print("%s %s %s .\n" % (s, p, o))
      f.write(("%s %s %s .\n" % (s, p, o)).encode("utf8"))
      
  elif format == "rdfxml":
    if _has_rapper and not force_rdflib:
      import subprocess
      import owlready2
      rapper = subprocess.Popen([owlready2.RAPPER_EXE, "-q", "-i", "ntriples", "-o", "rdfxml-abbrev", "-", "http://test/xxx.owl"], stdin = subprocess.PIPE, stdout = f)
      _save(rapper.stdin, "ntriples", graph, c)
      rapper.stdin.close()
      rapper.wait()
      
    else:
      import rdflib
      from   rdflib.term import URIRef, BNode, Literal
      g = rdflib.Graph()
      
      if c is None: graph.sql.execute("SELECT s,p,o FROM quads")
      else:         graph.sql.execute("SELECT s,p,o FROM quads WHERE c=?", (c,))
      for s,p,o in graph.sql.fetchall():
        if   s.startswith("_"): s = BNode("bn%s" % s[1:])
        else:                   s = URIRef(unabbreviate(s))
        p = URIRef(unabbreviate(p))
        if   o.startswith("_"): o = BNode("bn%s" % o[1:])
        elif o.startswith('"'):
          v, l = o.rsplit('"', 1)
          if   l.startswith("@"): o = Literal(v[1:], lang = l[1:])
          elif l == "":           o = Literal(v[1:])
          else:                   o = Literal(v[1:], datatype = URIRef(unabbreviate(l)))
        else: o = URIRef(unabbreviate(o))
        g.add((s,p,o))
        
      g.serialize(f, "xml")
      
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


import owlready2
for _d in os.get_exec_path():
  if os.path.exists(os.path.join(_d, owlready2.RAPPER_EXE)):
    _has_rapper = True
    break
else: _has_rapper = False
del _d

