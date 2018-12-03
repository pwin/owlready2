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

from functools import lru_cache

import owlready2
from owlready2.base import *
from owlready2.base import _universal_datatype_2_abbrev

owlready2_optimized = None
try: import owlready2_optimized
except:
  print("* Owlready2 * Warning: optimized Cython parser module 'owlready2_optimized' is not available, defaulting to slower Python implementation", file = sys.stderr)
  pass


INT_DATATYPES   = { "http://www.w3.org/2001/XMLSchema#integer", "http://www.w3.org/2001/XMLSchema#byte", "http://www.w3.org/2001/XMLSchema#short", "http://www.w3.org/2001/XMLSchema#int", "http://www.w3.org/2001/XMLSchema#long", "http://www.w3.org/2001/XMLSchema#unsignedByte", "http://www.w3.org/2001/XMLSchema#unsignedShort", "http://www.w3.org/2001/XMLSchema#unsignedInt", "http://www.w3.org/2001/XMLSchema#unsignedLong", "http://www.w3.org/2001/XMLSchema#negativeInteger", "http://www.w3.org/2001/XMLSchema#nonNegativeInteger", "http://www.w3.org/2001/XMLSchema#positiveInteger" }
FLOAT_DATATYPES = { "http://www.w3.org/2001/XMLSchema#decimal", "http://www.w3.org/2001/XMLSchema#double", "http://www.w3.org/2001/XMLSchema#float", "http://www.w3.org/2002/07/owl#real" }

class BaseGraph(object):
  _SUPPORT_CLONING = False
  #READ_METHODS  = ["_refactor", "_new_numbered_iri", "_abbreviate", "_unabbreviate",
  #                 "get_triple_sp", "_get_data_triple_triple_sp", "get_triple_po", "_get_obj_triples_transitive_sp", "_get_obj_triples_transitive_po", "_get_obj_triples_transitive_sym", "_get_obj_triples_transitive_sp_indirect", "get_triples", "_get_data_triple_triples", "get_triples_s", "get_triples_sp", "_get_data_triple_triples_sp", "get_triples_po", "get_pred", "get_quads", "_get_triple_data_triples_sp", "_get_triple_data_triple_sp", "_get_triples_sp", "has_triple", "_has_data_triple_triple", "_del_triple", "_del_data_triple"]
  #WRITE_METHODS = ["_add_triple", "_set_triple", "_add_data_triple", "_set_data_triple"]
  
  BASE_METHODS  = ["_refactor", "_new_numbered_iri", "_abbreviate", "_unabbreviate",
                   
                   "_get_obj_triples_cspo_cspo", "_get_obj_triples_spo_spo", "_get_obj_triples_sp_co", "_get_obj_triples_s_po",
                   "_get_obj_triples_po_s", "_get_obj_triples_sp_o", "_get_obj_triple_sp_o", "_get_obj_triple_po_s", "_has_obj_triple_spo", "_del_obj_triple_raw_spo",
                   
                   "_get_data_triples_spod_spod", "_get_data_triples_sp_od", "_get_data_triple_sp_od", "_get_data_triples_s_pod", "_has_data_triple_spod", "_del_data_triple_raw_spodd",
                   
                   "_get_triples_spod_spod", "_get_triples_sp_od", "_get_triple_sp_od", "_get_triples_s_pod", "_get_triples_s_p",
                   
                   "_get_obj_triples_transitive_sp", "_get_obj_triples_transitive_po", "_get_obj_triples_transitive_sym", "_get_obj_triples_transitive_sp_indirect"]
  
  WORLD_METHODS = [] # "get_equivs_s_o"
  
  ONTO_METHODS = ["_add_obj_triple_raw_spo", "_set_obj_triple_raw_spo", "_add_data_triple_raw_spodd", "_set_data_triple_raw_spodd"]
  
  def sub_graph(self, user_context): return self.__class__(self, user_context)
  
  def context_2_user_context(self, context): raise NotImplementedError
  
  def parse(self, f): raise NotImplementedError
    
  def save(self, f, format = "pretty-xml"): raise NotImplementedError
  
  def _abbreviate  (self, iri): return iri
  def _unabbreviate(self, iri): return iri
  
  def _get_obj_triples_transitive_sp(self, s, p, already = None):
    if already is None: already = set()
    else:
      if s in already: return already
      already.add(s)
    for o in self._get_obj_triples_sp_o(s, p):
      self._get_obj_triples_transitive_sp(o, p, already)
    return already
  
  def _get_obj_triples_transitive_po(self, p, o, already = None):
    if already is None: already = set()
    else:
      if o in already: return already
      already.add(o)
    for s in self._get_obj_triples_po_s(p, o):
      self._get_obj_triples_transitive_po(p, s, already)
    return already
  
  def _get_obj_triples_transitive_sym(self, s, p, already = None):
    if already is None: already = set()
    else:
      if s in already: return already
      already.add(s)
    for s2 in self._get_obj_triples_po_s(p, s): self._get_obj_triples_transitive_sym(s2, p, already)
    for s2 in self._get_obj_triples_sp_o(s, p): self._get_obj_triples_transitive_sym(s2, p, already)
    return already
  
  def _get_obj_triples_transitive_sp_indirect(self, s, predicates_inverses, already = None):
    if already is None: already = set()
    else:
      if s in already: return already
      already.add(s)
    for (predicate, inverse) in predicates_inverses:
      for o in self._get_obj_triples_sp_o(s, predicate): self._get_obj_triples_transitive_sp_indirect(o, predicates_inverses, already)
      if inverse:
        for o in self._get_obj_triples_po_s(inverse, s): self._get_obj_triples_transitive_sp_indirect(o, predicates_inverses, already)
    return already
  
  
  def dump(self, format = "ntriples", file = None):
    import io
    s = io.BytesIO()
    self.save(s, format)
    print(s.getvalue().decode("utf8"), file = file)


class BaseMainGraph(BaseGraph):
  def parse(self, f): raise NotImplementedError
  
  def save(self, f, format = "rdfxml", **kargs): _save(f, format, self, **kargs)
  

class BaseSubGraph(BaseGraph):
  def __init__(self, parent, onto):
    self.parent = parent
    self.onto   = onto
    
  def parse(self, f, format = None, delete_existing_triples = True, default_base = ""):
    format = format or _guess_format(f)
    
    if   format == "ntriples":
      objs, datas, on_prepare_obj, on_prepare_data, insert_objs, insert_datas, new_blank, _abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples)
      
      try:
        current_line = 0
        if owlready2_optimized:
          owlready2_optimized.parse_ntriples(f, objs, datas, insert_objs, insert_datas, _abbreviate, new_blank, default_base)
          
        else:
          splitter = re.compile("\s")
          bn_src_2_sql = {}
          
          line = f.readline().decode("utf8")
          while line:
            current_line += 1
            if (not line.startswith("#")) and (not line.startswith("\n")):
              s,p,o = splitter.split(line[:-3], 2)
              
              if   s.startswith("<"): s = s[1:-1]
              elif s.startswith("_"):
                bn = bn_src_2_sql.get(s)
                if bn is None: bn = bn_src_2_sql[s] = new_blank()
                s = bn
              
              p = p[1:-1]
            
              if   o.startswith("<"): on_prepare_obj(s, p, o[1:-1])
              elif o.startswith("_"):
                bn = bn_src_2_sql.get(o)
                if bn is None: bn = bn_src_2_sql[o] = new_blank()
                on_prepare_obj(s, p, bn)
              elif o.startswith('"'):
                o, d = o.rsplit('"', 1)
                if d.startswith("^"):
                  d = d[3:-1]
                  if   d in INT_DATATYPES:   o = int  (o[1:])
                  elif d in FLOAT_DATATYPES: o = float(o[1:])
                  else:                      o = o[1:].encode("raw-unicode-escape").decode("unicode-escape")
                else:
                  o = o[1:].encode("raw-unicode-escape").decode("unicode-escape")
                on_prepare_data(s, p, o, d)
                
            line = f.readline().decode("utf8")
          
        onto_base_iri = on_finish()
        
      except Exception as e:
        if len(self) == 0:
          self._add_obj_triple_raw_spo(self.onto.storid, rdf_type, owl_ontology)
        if current_line:
          raise OwlReadyOntologyParsingError("NTriples parsing error in file %s, line %s." % (getattr(f, "name", "???"), current_line)) from e
        else:
          raise OwlReadyOntologyParsingError("NTriples parsing error in file %s." % getattr(f, "name", "???")) from e
          
    elif format == "rdfxml":
      objs, datas, on_prepare_obj, on_prepare_data, insert_objs, insert_datas, new_blank, _abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples)
      try:
        if owlready2_optimized:
          owlready2_optimized.parse_rdfxml(f, objs, datas, insert_objs, insert_datas, _abbreviate, new_blank, default_base)
        else:
          import owlready2.rdfxml_2_ntriples
          owlready2.rdfxml_2_ntriples.parse(f, on_prepare_obj, on_prepare_data, new_blank, default_base)
        onto_base_iri = on_finish()
      except OwlReadyOntologyParsingError as e:
        if len(self) == 0: self._add_obj_triple_raw_spo(self.onto.storid, rdf_type, owl_ontology)
        raise e
      
    elif format == "owlxml":
      objs, datas, on_prepare_obj, on_prepare_data, insert_objs, insert_datas, new_blank, _abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples)
      try:
        if owlready2_optimized:
          owlready2_optimized.parse_owlxml(f, objs, datas, insert_objs, insert_datas, _abbreviate, new_blank, default_base)
        else:
          import owlready2.owlxml_2_ntriples
          owlready2.owlxml_2_ntriples.parse(f, on_prepare_obj, on_prepare_data, new_blank, default_base)
        onto_base_iri = on_finish()
      except OwlReadyOntologyParsingError as e:
        if len(self) == 0: self._add_obj_triple_raw_spo(self.onto.storid, rdf_type, owl_ontology)
        raise e
      
    else:
      raise ValueError("Unsupported format %s." % format)
    
    return onto_base_iri
 
  def save(self, f, format = "rdfxml", **kargs):
    self.parent.commit()
    _save(f, format, self, **kargs)
    
  
  
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


def _save(f, format, graph):
  if   format == "ntriples":
    _unabbreviate = lru_cache(None)(graph._unabbreviate)
    
    for s,p,o,d in graph._iter_triples():
      #print(repr((s,p,o,d)))
      if   s < 0: s = "_:%s" % (-s)
      else:       s = "<%s>" % _unabbreviate(s)
      p = "<%s>" % _unabbreviate(p)
      if d is None:
        if o < 0: o = "_:%s" % (-o)
        else:     o = "<%s>" % _unabbreviate(o)
      else:
        if isinstance(o, str):  o = o.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        if   isinstance(d, str) and d.startswith("@"): o = '"%s"%s' % (o, d)
        elif d == 0:                                   o = '"%s"' % o
        else:                                          o = '"%s"^^<%s>' % (o, _unabbreviate(d)) # Unabbreviate datatype's iri
        
      f.write(("%s %s %s .\n" % (s, p, o)).encode("utf8"))
      
  elif format == "nquads":
    _unabbreviate = lru_cache(None)(graph._unabbreviate)
    
    c_2_iri = { c : iri for c, iri in graph._iter_ontology_iri() }
    
    for c,s,p,o,d in graph._iter_triples(True):
      if   s < 0: s = "_:%s" % (-s)
      else:       s = "<%s>" % _unabbreviate(s)
      p = "<%s>" % _unabbreviate(p)
      if d is None:
        if o < 0: o = "_:%s" % (-o)
        else:     o = "<%s>" % _unabbreviate(o)
      else:
        if isinstance(o, str):  o = o.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        if   isinstance(d, str) and d.startswith("@"): o = '"%s"%s' % (o, d)
        elif d == 0:                                   o = '"%s"' % o
        else:                                          o = '"%s"^^<%s>' % (o, _unabbreviate(d)) # Unabbreviate datatype's iri
        
      f.write(("<%s> %s %s %s .\n" % (c_2_iri[c], s, p, o)).encode("utf8"))
      
  elif format == "rdfxml":
    @lru_cache(None)
    def _unabbreviate(storid):
      r = graph._unabbreviate(storid).replace("&", "&amp;")
      if r.startswith(base_iri):
        if base_iri.endswith("/"): return r[len(base_iri) :]
        else:                      return r[len(base_iri) - 1 :]
      return r
    
    base_iri = graph._iter_ontology_iri(graph.c)
    
    xmlns = {
      "http://www.w3.org/1999/02/22-rdf-syntax-ns#" : "rdf:",
      "http://www.w3.org/2001/XMLSchema#" : "xsd:",
      "http://www.w3.org/2000/01/rdf-schema#" : "rdfs:",
      "http://www.w3.org/2002/07/owl#" : "owl:",
    }
    if isinstance(base_iri, str):
      if base_iri.endswith("/"):
        xmlns[base_iri] = ""
      else:
        xmlns[base_iri[:-1]] = ""
        xmlns[base_iri     ] = "#"
    else:
      base_iri = "    " # Non-null, non-URL
      
    xmlns_abbbrevs = set(xmlns.values())
    @lru_cache(None)
    def abbrev(x):
      splitted   = x.rsplit("#", 1)
      splitted_s = x.rsplit("/", 1)
      if   (len(splitted  ) == 2) and (len(splitted_s) == 2) and (len(splitted[1]) < len(splitted_s[1])):
        left = splitted[0] + "#"
      elif (len(splitted_s) == 2):
        splitted = splitted_s
        left = splitted[0] + "/"
      else: return x
      
      xmln = xmlns.get(left)
      if not xmln:
        xmln0 = splitted[0].rsplit("/", 1)[1][:4]
        if not xmln0[0] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ": xmln0 = "x_" + xmln0
        xmln  = xmln0 + ":"
        i = 2
        while xmln in xmlns_abbbrevs:  xmln = "%s%s:" % (xmln0, i) ; i += 1
        
        xmlns[left] = xmln = xmln
        xmlns_abbbrevs.add(xmln)
        
      return xmln + splitted[1]
    
    lines  = []
    liness = {}
    for type in [
        "owl:Ontology",
        "owl:ObjectProperty",
        "owl:DatatypeProperty",
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
        first = graph._get_obj_triple_sp_o(bn, rdf_first)
        if first != rdf_nil: yield first
        bn = graph._get_obj_triple_sp_o(bn, rdf_rest)
        
    def purge():
      nonlocal s_lines, current_s, type
      
      if current_s < 0:
        l = bn_2_inner_list[current_s]
        current_s = 0
      else:
        l = liness.get(type) or lines[-1]
        
      if s_lines:
        if current_s < 0:
          l.append("""<%s rdf:nodeID="%s">""" % (type, current_s))
          
        elif current_s > 0:
          current_s = _unabbreviate(current_s)
          l.append("""<%s rdf:about="%s">""" % (type, current_s))
          
        else:
          l.append("""<%s>""" % type)
          
        l.extend(s_lines)
        s_lines = []
        
        l.append("""</%s>""" % type)
        
      else:
        if current_s < 0:
          l.append("""<%s rdf:nodeID="%s"/>""" % (type, current_s))
          
        elif current_s > 0:
          current_s = _unabbreviate(current_s)
          l.append("""<%s rdf:about="%s"/>""" % (type, current_s))
          
        else:
          l.append("""<%s/>""" % type)

      if current_s: l.append("")
      
      
    type      = "rdf:Description"
    s_lines   = []
    current_s = ""
    for s,p,o,d in graph._iter_triples(False, True):
      if s != current_s:
        if current_s: purge()
        current_s = s
        type = "rdf:Description"
        
      if (p == rdf_type) and (type == "rdf:Description") and (not o < 0):
        t = abbrev(_unabbreviate(o))
        if not t in bad_types:
          type = t
          if type.startswith("#"): type = type[1:]
          continue
        
      p = abbrev(_unabbreviate(p))
      if p.startswith("#"): p = p[1:]
      
      if  not d is None:
        if isinstance(o, str):  o = o.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if   isinstance(d, str) and d.startswith("@"): s_lines.append("""  <%s xml:lang="%s">%s</%s>""" % (p, d[1:], o, p))
        elif d:                                        s_lines.append("""  <%s rdf:datatype="%s">%s</%s>""" % (p, _unabbreviate(d), o, p))
        else:                                          s_lines.append("""  <%s>%s</%s>""" % (p, o, p))
        
      elif o < 0:
          if p in tags_with_list:
            s_lines.append("""  <%s rdf:parseType="Collection">""" % p)
            for i in parse_list(o):
              if i < 0:
                l = bn_2_inner_list[i]
                inner_lists_used.add(id(l))
                s_lines.append(l)
              elif isinstance(i, int):
                i = _unabbreviate(i)
                s_lines.append("""    <rdf:Description rdf:about="%s"/>""" % i)
          else:
            l = bn_2_inner_list[o]
            inner_lists_used.add(id(l))
            s_lines.append("""  <%s>""" % p)
            s_lines.append(l)
          s_lines.append("""  </%s>""" % p)
          
      else:
        o = _unabbreviate(o)
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
    if base_iri.endswith("/"):
      decls.append('xmlns="%s"' % base_iri)
      
    f.write(b"""<?xml version="1.0"?>\n""")
    f.write(("""<rdf:RDF %s>\n\n""" % "\n         ".join(decls)).encode("utf8"))
    f.write( """\n""".join(flatten(sum(lines, []))).encode("utf8"))
    f.write(b"""\n\n</rdf:RDF>\n""")
