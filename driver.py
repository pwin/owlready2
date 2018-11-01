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

try:
  from rdfxml_2_ntriples_pyx import parse_rdfxml
except:
  from owlready2.rdfxml_2_ntriples import parse as parse_rdfxml

try:
  from owlxml_2_ntriples_pyx import parse_owlxml
except:
  from owlready2.owlxml_2_ntriples import parse as parse_owlxml


class BaseGraph(object):
  _SUPPORT_CLONING = False
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

  def dump(self, format = "ntriples"):
    import io
    s = io.BytesIO()
    self.save(s, format)
    print(s.getvalue().decode("utf8"))


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
      on_prepare_triple, new_blank, new_literal, abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples)
      
      try:
        splitter = re.compile("\s")
        bn_src_2_sql = {}
        
        line = f.readline().decode("utf8")
        current_line = 0
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
        if len(self) == 0:
          self._add_triple(self.onto.storid, rdf_type, owl_ontology)
        raise OwlReadyOntologyParsingError("NTriples parsing error in file %s, line %s." % (getattr(f, "name", "???"), current_line)) from e
      
      #if not self.has_triple(self.onto.storid, rdf_type, owl_ontology): # Not always present (e.g. not in dbpedia)
      #  self._add_triple(self.onto.storid, rdf_type, owl_ontology)
        
    elif format == "rdfxml":
      try:
        on_prepare_triple, new_blank, new_literal, abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples)
        parse_rdfxml(f, on_prepare_triple, new_blank, new_literal, default_base)
        onto_base_iri = on_finish()
      except OwlReadyOntologyParsingError as e:
        if len(self) == 0:
          self._add_triple(self.onto.storid, rdf_type, owl_ontology)
        raise e
      
    elif format == "owlxml":
      try:
        on_prepare_triple, new_blank, new_literal, abbreviate, on_finish = self.create_parse_func(getattr(f, "name", ""), delete_existing_triples, "datatypeIRI")
        parse_owlxml(f, on_prepare_triple, new_blank, new_literal)
        onto_base_iri = on_finish()
      except OwlReadyOntologyParsingError as e:
        if len(self) == 0:
          self._add_triple(self.onto.storid, rdf_type, owl_ontology)
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
    unabbreviate = lru_cache(None)(graph.unabbreviate)
    
    for s,p,o in graph._iter_triples():
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
      
  elif format == "nquads":
    unabbreviate = lru_cache(None)(graph.unabbreviate)
    
    c_2_iri = { c : iri for c, iri in graph._iter_ontology_iri() }
    print(c_2_iri)
    
    for c, s,p,o in graph._iter_triples(True):
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
      f.write(("<%s> %s %s %s .\n" % (c_2_iri[c], s, p, o)).encode("utf8"))
      
  elif format == "rdfxml":
    @lru_cache(None)
    def unabbreviate(storid):
      r = graph.unabbreviate(storid).replace("&", "&amp;")
      if r.startswith(base_iri):
        if base_iri.endswith("/"): return r[len(base_iri) :]
        else:                      return r[len(base_iri) - 1 :]
      return r
      #return graph.unabbreviate(storid).replace("&", "&amp;")
    
    base_iri = graph._iter_ontology_iri(graph.c)
    
    xmlns = {
#      base_iri[:-1] : "",
#      base_iri : "#",
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
        first = graph.get_triple_sp(bn, rdf_first)
        if first != rdf_nil: yield first
        bn = graph.get_triple_sp(bn, rdf_rest)
        
    def purge():
      nonlocal s_lines, current_s, type
      
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
          #if current_s.startswith(base_iri): current_s = current_s[len(base_iri)-1 :]
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
          #if current_s.startswith(base_iri): current_s = current_s[len(base_iri)-1 :]
          l.append("""<%s rdf:about="%s"/>""" % (type, current_s))
          
        else:
          l.append("""<%s/>""" % type)

      if current_s: l.append("")
      
      
    type      = "rdf:Description"
    s_lines   = []
    current_s = ""
    for s,p,o in graph._iter_triples(False, True):
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
                #if i.startswith(base_iri): i = i[len(base_iri)-1 :]
                s_lines.append("""    <rdf:Description rdf:about="%s"/>""" % i)
          else:
            l = bn_2_inner_list[o]
            inner_lists_used.add(id(l))
            s_lines.append("""  <%s>""" % p)
            s_lines.append(l)
          s_lines.append("""  </%s>""" % p)
          
      else:
        o = unabbreviate(o)
        #if o.startswith(base_iri): o = o[len(base_iri)-1 :]
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
