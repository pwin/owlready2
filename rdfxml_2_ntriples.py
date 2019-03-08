# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2019 Jean-Baptiste LAMY
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

import sys, xml, xml.parsers.expat, urllib.parse
from collections import defaultdict

try:
  from owlready2.base import OwlReadyOntologyParsingError
except:
  class OwlReadyOntologyParsingError(Exception): pass

INT_DATATYPES   = { "http://www.w3.org/2001/XMLSchema#integer", "http://www.w3.org/2001/XMLSchema#byte", "http://www.w3.org/2001/XMLSchema#short", "http://www.w3.org/2001/XMLSchema#int", "http://www.w3.org/2001/XMLSchema#long", "http://www.w3.org/2001/XMLSchema#unsignedByte", "http://www.w3.org/2001/XMLSchema#unsignedShort", "http://www.w3.org/2001/XMLSchema#unsignedInt", "http://www.w3.org/2001/XMLSchema#unsignedLong", "http://www.w3.org/2001/XMLSchema#negativeInteger", "http://www.w3.org/2001/XMLSchema#nonNegativeInteger", "http://www.w3.org/2001/XMLSchema#positiveInteger" }
FLOAT_DATATYPES = { "http://www.w3.org/2001/XMLSchema#decimal", "http://www.w3.org/2001/XMLSchema#double", "http://www.w3.org/2001/XMLSchema#float", "http://www.w3.org/2002/07/owl#real" }


def is_bn(x):
  if isinstance(x, int): return x < 0
  return x.startswith("_")

def is_fake_bn(x):
  if isinstance(x, str): return x.startswith("_ ")
  return False

def parse(f, on_prepare_obj = None, on_prepare_data = None, new_blank = None, default_base = ""):
  parser = xml.parsers.expat.ParserCreate(None, "")
  try:
    parser.buffer_text          = True
    parser.specified_attributes = True
  except: pass
  
  stack                    = [["", ""]] # List of [parse type, value] pairs
  prefixes                 = {}
  prefixess                = [prefixes]
  tag_is_predicate         = False
  current_blank            = 0
  current_fake_blank       = 0
  current_content          = ""
  current_attrs            = None
  nb_triple                = 0
  bns                      = defaultdict(set)
  dont_create_unnamed_bn   = False
  axiom_annotation_sources = {}
  axiom_annotation_props   = {}
  axiom_annotation_targets = {}
  triples_with_unnamed_bn  = defaultdict(list)
  if default_base:
    xml_base = default_base
    if xml_base.endswith("#") or xml_base.endswith("/"): xml_base = xml_base[:-1]
    xml_dir  = xml_base.rsplit("/", 1)[0] + "/"
  else:
    xml_base                 = ""
    xml_dir                  = ""
    
  if not on_prepare_obj:
    def on_prepare_obj(s,p,o):
      nonlocal nb_triple
      nb_triple += 1
      if not is_bn(s): s = "<%s>" % s
      if not is_bn(o): o = "<%s>" % o
      print("%s %s %s ." % (s,"<%s>" % p,o))
      
    def on_prepare_data(s,p,o,d):
      nonlocal nb_triple
      nb_triple += 1
      if not is_bn(s): s = "<%s>" % s
      
      if isinstance(o, str): o = o.replace('"', '\\"').replace("\n", "\\n")
      if d and d.startswith("@"):
        print('%s %s "%s"%s .' % (s,"<%s>" % p,o,d))
      elif d:
        print('%s %s "%s"^^<%s> .' % (s,"<%s>" % p,o,d))
      else:
        print('%s %s "%s" .' % (s,"<%s>" % p,o))
        
  if not new_blank:
    def new_blank():
      nonlocal current_blank
      current_blank += 1
      return "_:%s" % current_blank
    
  def new_fake_blank():
    nonlocal current_fake_blank
    current_fake_blank += 1
    return "_ %s" % current_fake_blank
  
  node_2_blanks = defaultdict(new_blank)
  known_nodes   = set()
  
  def new_list(l):
    bn = bn0 = new_blank()
    
    if l:
      for i in range(len(l) - 1):
        on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[i])
        bn_next = new_blank()
        on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", bn_next)
        bn = bn_next
      on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[-1])
      on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      
    else:
      on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest",  "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      
    return bn0
  
  def add_to_bn(bn, type, rel, value, d = ""):
    if type == "COL":
      value = tuple(frozenset(bns[v])
                    if is_bn(v) and (not v in known_nodes)
                    else v
                    for v in value)
      bns[bn].add((type, rel) + value)
    else:
      if type == "DAT":
        bns[bn].add((type, rel, value, d))
      else:
        if is_bn(value) and (not value in known_nodes): value = frozenset(bns[value])
        bns[bn].add((type, rel, value))
        
  def startNamespace(prefix, uri):
    nonlocal prefixes
    prefixes = prefixes.copy()
    prefixess.append(prefixes)
    
    if prefix: prefixes[prefix  ] = uri
    else:      prefixes[""      ] = uri
      
  def endNamespace(prefix):
    nonlocal prefixes
    prefixess.pop()
    prefixes = prefixess[-1]
    
  def startElement(tag, attrs):
    nonlocal tag_is_predicate, current_content, current_attrs, dont_create_unnamed_bn, xml_base, xml_dir
    
    tag_is_predicate = not tag_is_predicate
    if tag_is_predicate:
      
      if   attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#parseType") == "Collection":
        stack.append(["Collection", []])
        
      elif tag == "http://www.w3.org/1999/02/22-rdf-syntax-ns#RDF":
        stack.append(["RDF", ""])
        
        namespace_base = attrs.get("http://www.w3.org/XML/1998/namespacebase")
        if namespace_base:
          xml_base = namespace_base
          xml_dir  = namespace_base.rsplit("/", 1)[0] + "/"
          
      else:
        iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#resource")
        if iri:
          if not ":" in iri:
            if not iri:                 iri = xml_base
            elif   iri.startswith("#"): iri = xml_base + iri
            elif   iri.startswith("/"): iri = xml_dir  + iri[1:]
            else:                       iri = urllib.parse.urljoin(xml_dir, iri)
          if iri.endswith("/"): iri = iri[:-1]
          stack.append(["Resource", iri])
          
        else:
          iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#nodeID")
          
          if iri:
            iri = node_2_blanks[iri]
            known_nodes.add(iri)
            stack.append(["Resource", iri])
          else:
            stack.append(["Literal", ""])
            current_content = ""
            current_attrs   = attrs
            
          if (tag == "http://www.w3.org/2002/07/owl#annotatedSource") or (tag == "http://www.w3.org/2002/07/owl#annotatedTarget"):
            dont_create_unnamed_bn = True
            
    else:
      iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#about", None)
      if iri is None:
        iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#ID", None)
        if iri: iri = "#%s" % iri
      else:
        if iri.endswith("/"): iri = iri[:-1]
      if iri is None:
        iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#nodeID")
        if iri:
          iri = node_2_blanks[iri]
          known_nodes.add(iri)
        else:
          if dont_create_unnamed_bn: iri = new_fake_blank()
          else:                      iri = new_blank()
      else:
        if not ":" in iri:
          if not iri:                 iri = xml_base
          elif   iri.startswith("#"): iri = xml_base + iri
          elif   iri.startswith("/"): iri = xml_dir  + iri[1:]
          else:                       iri = urllib.parse.urljoin(xml_dir, iri)
          
      if tag != "http://www.w3.org/1999/02/22-rdf-syntax-ns#Description":
        if not is_fake_bn(iri):
          on_prepare_obj(iri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", tag)
        if is_bn(iri):
          add_to_bn(iri, "REL", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", tag)
          
      if stack[-1][0] == "Collection":
        stack[-1][1].append(iri)
        
      else:
        if stack[-1][0] == "Literal": stack[-1][0] = "Resource"
        stack[-1][1] = iri
        
        
  def endElement(tag):
    nonlocal tag_is_predicate, dont_create_unnamed_bn
    
    if tag_is_predicate:
      parse_type, value = stack.pop()
      
      if stack[-1][0] == "Collection": iri = stack[-1][1][-1]
      else:                            iri = stack[-1][1]
      
      if   tag == "http://www.w3.org/2002/07/owl#annotatedSource":
        dont_create_unnamed_bn = False
        axiom_annotation_sources[iri] = value
        if is_fake_bn(value):
          triples_with_unnamed_bn[iri].insert(0, (tag, value, parser.CurrentLineNumber, parser.CurrentColumnNumber))
          
          tag_is_predicate = not tag_is_predicate
          return
        
      elif tag == "http://www.w3.org/2002/07/owl#annotatedProperty":
        axiom_annotation_props  [iri] = value
      
      elif tag == "http://www.w3.org/2002/07/owl#annotatedTarget":
        dont_create_unnamed_bn = False
        axiom_annotation_targets[iri] = value
        if is_fake_bn(value):
          triples_with_unnamed_bn[iri].append((tag, value, parser.CurrentLineNumber, parser.CurrentColumnNumber))
          
          tag_is_predicate = not tag_is_predicate
          return
        
      
      if   parse_type == "Resource":
        if not is_fake_bn(iri):
          on_prepare_obj(iri, tag, value)
          
        if is_bn(iri):
          add_to_bn(iri, "REL", tag, value)
            
        if is_bn(value):
          add_to_bn(value, "INV", tag, iri)
          
          
      elif parse_type == "Literal":
        o = current_content
        d = current_attrs.get("http://www.w3.org/XML/1998/namespacelang")
        if d is None:
          d = current_attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype", "")
          if   d in INT_DATATYPES:   o = int  (o)
          elif d in FLOAT_DATATYPES: o = float(o)
        else:
          d = "@%s" % d
          
        if not is_fake_bn(iri):
          on_prepare_data(iri, tag, o, d)
        if is_bn(iri):
          add_to_bn(iri, "DAT", tag, o, d)
          
      elif parse_type == "Collection":
        if not is_fake_bn(iri):
          on_prepare_obj(iri, tag, new_list(value))
        if is_bn(iri):
          add_to_bn(iri, "COL", tag, value)
          
          
    tag_is_predicate = not tag_is_predicate
    
    
  def characters(content):
    nonlocal current_content
    if stack[-1][0] == "Literal": current_content += content
    
    
  parser.StartNamespaceDeclHandler = startNamespace
  parser.EndNamespaceDeclHandler   = endNamespace
  parser.StartElementHandler       = startElement
  parser.EndElementHandler         = endElement
  parser.CharacterDataHandler      = characters
  
  try:
    if isinstance(f, str):
      f = open(f, "rb")
      parser.ParseFile(f)
      f.close()
    else:
      parser.ParseFile(f)
  except Exception as e:
    raise OwlReadyOntologyParsingError("RDF/XML parsing error in file %s, line %s, column %s." % (getattr(f, "name", getattr(f, "url", "???")), parser.CurrentLineNumber, parser.CurrentColumnNumber)) from e
  
  
  if triples_with_unnamed_bn:
    content_2_bns = defaultdict(list)
    for bn, content in bns.items():
      if not is_fake_bn(bn):
        content_2_bns[frozenset(content)].append(bn)
        
    def rebuild_bn(content):
      bn = new_blank()
      content_2_bns[frozenset(content)].append(bn)
      for i in content:
        if   i[0] == "REL":
          drop, p, o = i
          if not isinstance(o, (str, int)): o = rebuild_bn(o)
          on_prepare_obj(bn, p, o)
        elif i[0] == "DAT":
          drop, p, o, d = i
          if not isinstance(o, (str, int)): o = rebuild_bn(o)
          on_prepare_data(bn, p, o, d)
        elif i[0] == "INV":
          drop, p, o = i
          if not isinstance(o, (str, int)): o = rebuild_bn(o)
          on_prepare_obj(o, p, bn)
        elif i[0] == "COL":
          drop, p, *l = i
          l = [(isinstance(x, (str, int)) and x) or rebuild_bn(x) for x in l]
          o = new_list(l)
          on_prepare_obj(bn, p, o)
        else:
          print(i)
          raise ValueError
      return bn
    
    for axiom_iri, triples in triples_with_unnamed_bn.items():
      for p, o, line, column in triples:
        try:
          content = bns[o]
          if p == "http://www.w3.org/2002/07/owl#annotatedSource":
            target = axiom_annotation_targets[axiom_iri]
            if is_bn(target): target = frozenset(bns[target])
            candidates_bn = content_2_bns[frozenset(content | { ("REL", axiom_annotation_props[axiom_iri], target) })]
            
          else:
            source = axiom_annotation_sources[axiom_iri]
            if is_bn(source):
              source = frozenset(bns[source] | { ("REL", axiom_annotation_props[axiom_iri], target) })
            candidates_bn = (content_2_bns[frozenset(content | { ("INV", axiom_annotation_props[axiom_iri], source) })] or
                             content_2_bns[frozenset(content)])
            
          if candidates_bn: o = candidates_bn[-1]
          else:
            o = rebuild_bn(content)
          on_prepare_obj(axiom_iri,p,o)
        except Exception as e:
          raise OwlReadyOntologyParsingError("RDF/XML parsing error in file %s, line %s, column %s." % (getattr(f, "name", getattr(f, "url", "???")), line, column)) from e
        
    
  return nb_triple


if __name__ == "__main__":
  filename = sys.argv[-1]
  
  import time
  t = time.time()
  nb_triple = parse(filename)
  t = time.time() - t
  print("# %s triples read in %ss" % (nb_triple, t), file = sys.stderr)
