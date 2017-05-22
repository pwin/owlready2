# -*- coding: utf-8 -*-
# Owlready
# Copyright (C) 2013-2017 Jean-Baptiste LAMY
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

import sys, xml, xml.parsers.expat
from collections import defaultdict

try:
  from owlready2.base import OwlReadyOntologyParsingError
except:
  class OwlReadyOntologyParsingError(OwlReadyError): pass

def parse(f, on_triple = None, on_prepare_triple = None, new_blank = None, new_literal = None):
  parser                 = xml.parsers.expat.ParserCreate(None, "")
  stack                  = [["", ""]] # List of [parse type, value] pairs
  prefixes               = {}
  prefixess              = [prefixes]
  tag_is_predicate       = False
  current_blank          = 0
  current_content        = ""
  current_attrs          = None
  nb_triple              = 0
  
  if not on_triple:
    def on_triple(s,p,o):
      print("%s %s %s ." % (s,p,o))
      
  if not on_prepare_triple:
    def on_prepare_triple(s,p,o):
      nonlocal nb_triple
      nb_triple += 1
      if not s.startswith("_"): s = "<%s>" % s
      if not (o.startswith("_") or o.startswith('"')): o = "<%s>" % o
      on_triple(s,"<%s>" % p,o)
      
  if not new_blank:
    def new_blank():
      nonlocal current_blank
      current_blank += 1
      return "_:%s" % current_blank
    
  node_2_blanks = defaultdict(new_blank)
    
  if not new_literal:
    def new_literal(value, attrs):
      value = value.replace('"', '\\"').replace("\n", "\\n")
      lang = attrs.get("http://www.w3.org/XML/1998/namespacelang")
      if lang: return '"%s"@%s' % (value, lang)
      datatype = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype")
      if datatype: return '"%s"^^<%s>' % (value, datatype)
      return '"%s"' % (value)
    
  def new_list(l):
    bn = bn0 = new_blank()
    
    if l:
      for i in range(len(l) - 1):
        on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[i])
        bn_next = new_blank()
        on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", bn_next)
        bn = bn_next
      on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[-1])
      on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      
    else:
      on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest",  "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      
    return bn0
  
  def startNamespace(prefix, uri):
    nonlocal prefixes
    prefixes = prefixes.copy()
    prefixess.append(prefixes)
    
    if prefix:
      prefixes[prefix  ] = uri
    else:
      prefixes[""      ] = uri
      prefixes["<base>"] = uri[:-1]
      prefixes["<dir>" ] = uri.rsplit("/", 1)[0] + "/"
      
  def endNamespace(prefix):
    nonlocal prefixes
    prefixess.pop()
    prefixes = prefixess[-1]
    
  def startElement(tag, attrs):
    nonlocal tag_is_predicate, current_content, current_attrs
    tag_is_predicate = not tag_is_predicate
    if tag_is_predicate:
      
      if   attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#parseType") == "Collection":
        stack.append(["Collection", []])
        
      elif tag == "http://www.w3.org/1999/02/22-rdf-syntax-ns#RDF":
        stack.append(["RDF", ""])
        
      else:
        iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#resource")
        if iri:
          if not ":" in iri:
            if   iri.startswith("#"): iri = prefixes["<base>"] + iri
            else:                     iri = prefixes["<dir>" ] + iri
          stack.append(["Resource", iri])
          
        else:
          iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#nodeID")
          
          if iri:
            iri = node_2_blanks[iri]
            stack.append(["Resource", iri])
          else:
            stack.append(["Literal", ""])
            current_content = ""
            current_attrs   = attrs
            
    else:
      iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#about")
      if iri:
        if not ":" in iri:
          if   iri.startswith("#"): iri = prefixes["<base>"] + iri
          else:                     iri = prefixes["<dir>" ] + iri
      else:
        iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#nodeID")
        if iri: iri = node_2_blanks[iri]
        else:   iri = new_blank()
        
      if tag != "http://www.w3.org/1999/02/22-rdf-syntax-ns#Description":
        on_prepare_triple(iri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", tag)
        
      if stack[-1][0] == "Collection":
        stack[-1][1].append(iri)
        
      else:
        if stack[-1][0] == "Literal": stack[-1][0] = "Resource"
        stack[-1][1] = iri
        
      
  def endElement(tag):
    nonlocal tag_is_predicate
    if tag_is_predicate:
      parse_type, value = stack.pop()
      
      if stack[-1][0] == "Collection": iri = stack[-1][1][-1]
      else:                            iri = stack[-1][1]
      
      if   parse_type == "Resource":
        on_prepare_triple(iri, tag, value)
        
      elif parse_type == "Literal":
        on_prepare_triple(iri, tag, new_literal(current_content, current_attrs))
        
      elif parse_type == "Collection":
        on_prepare_triple(iri, tag, new_list(value))
        
    tag_is_predicate = not tag_is_predicate
    
    
  def characters(content):
    nonlocal current_content
    if stack[-1][0] == "Literal": current_content += content
    
    
  parser.StartNamespaceDeclHandler = startNamespace
  parser.EndNamespaceDeclHandler   = endNamespace
  parser.StartElementHandler       = startElement
  parser.EndElementHandler         = endElement
  parser.CharacterDataHandler      = characters
  
  if isinstance(f, str): f = open(f, "rb")
  try:
    if isinstance(f, str):
      f = open(f, "rb")
      parser.ParseFile(f)
      f.close()
    else:
      parser.ParseFile(f)
  except Exception as e:
    raise OwlReadyOntologyParsingError("RDF/XML parsing error in file %s, line %s, column %s." % (getattr(f, "name", "???"), parser.CurrentLineNumber, parser.CurrentColumnNumber)) from e
  
  return nb_triple


if __name__ == "__main__":
  filename = sys.argv[-1]

  import time
  t = time.time()
  nb_triple = parse(filename)
  t = time.time() - t
  print("# %s triples read in %ss" % (nb_triple, t), file = sys.stderr)
