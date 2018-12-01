# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2018 Jean-Baptiste LAMY
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
from urllib.parse import urljoin
from collections import defaultdict

from owlready2.base import OwlReadyOntologyParsingError

INT_DATATYPES   = { "http://www.w3.org/2001/XMLSchema#integer", "http://www.w3.org/2001/XMLSchema#byte", "http://www.w3.org/2001/XMLSchema#short", "http://www.w3.org/2001/XMLSchema#int", "http://www.w3.org/2001/XMLSchema#long", "http://www.w3.org/2001/XMLSchema#unsignedByte", "http://www.w3.org/2001/XMLSchema#unsignedShort", "http://www.w3.org/2001/XMLSchema#unsignedInt", "http://www.w3.org/2001/XMLSchema#unsignedLong", "http://www.w3.org/2001/XMLSchema#negativeInteger", "http://www.w3.org/2001/XMLSchema#nonNegativeInteger", "http://www.w3.org/2001/XMLSchema#positiveInteger" }
FLOAT_DATATYPES = { "http://www.w3.org/2001/XMLSchema#decimal", "http://www.w3.org/2001/XMLSchema#double", "http://www.w3.org/2001/XMLSchema#float", "http://www.w3.org/2002/07/owl#real" }

cdef void on_prepare_obj(str s, str p, str o, list objs, object _abbreviate, object insert_objs):
  if not s.startswith("_"): s = _abbreviate(s)
  if not o.startswith("_"): o = _abbreviate(o)
  
  objs.append((s, _abbreviate(p), o))
  if len(objs) > 100000: insert_objs()
  
cdef void on_prepare_data(str s, str p, object o, str d, list datas, object _abbreviate, object insert_datas):
  if not s.startswith("_"): s = _abbreviate(s)
  if (d != "") and (not d.startswith("@")): d = _abbreviate(d)
  datas.append((s, _abbreviate(p), o, d))
  if len(datas) > 1000000: insert_datas()

cdef void on_prepare_triple(str s, str p, object o, list objs, list datas, object _abbreviate, object insert_objs, object insert_datas):
  if isinstance(o, tuple): on_prepare_data(s, p, o[0], o[1], datas, _abbreviate, insert_datas)
  else:                    on_prepare_obj (s, p, o,          objs,  _abbreviate, insert_objs)


cdef str new_list(list l, list objs, object insert_objs, object _abbreviate, object new_blank):
  cdef str bn
  cdef str bn0
  cdef str bn_next
  cdef int i
  
  bn = bn0 = new_blank()
  
  if l:
    for i in range(len(l) - 1):
      on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[i], objs, _abbreviate, insert_objs)
      bn_next = new_blank()
      on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", bn_next, objs, _abbreviate, insert_objs)
      bn = bn_next
    on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[-1], objs, _abbreviate, insert_objs)
    on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil", objs, _abbreviate, insert_objs)
      
  else:
    on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil", objs, _abbreviate, insert_objs)
    on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest",  "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil", objs, _abbreviate, insert_objs)
    
  return bn0

cdef str new_data_list(list l, list objs, list datas, object insert_objs, object insert_datas, object _abbreviate, object new_blank):
  cdef str bn
  cdef str bn0
  cdef str bn_next
  cdef int i
  
  bn = bn0 = new_blank()
  
  if l:
    for i in range(len(l) - 1):
      on_prepare_data(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[i][0], l[i][1], datas, _abbreviate, insert_datas)
      bn_next = new_blank()
      on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", bn_next, objs, _abbreviate, insert_objs)
      bn = bn_next
    on_prepare_data(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[-1][0], l[-1][1], datas, _abbreviate, insert_datas)
    on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil", objs, _abbreviate, insert_objs)
      
  else:
    on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil", objs, _abbreviate, insert_objs)
    on_prepare_obj(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest",  "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil", objs, _abbreviate, insert_objs)
    
  return bn0


cdef void add_to_bn(object bns, set known_nodes, str bn, str type, str rel, value, d = None):
    if type == "COL":
      value = tuple(frozenset(bns[v])
                    if v.startswith("_") and (not v in known_nodes)
                    else v
                    for v in value)
      bns[bn].add((type, rel) + value)
    else:
      if type == "DAT":
        bns[bn].add((type, rel, value, d))
      else:
        if value.startswith("_") and (not value in known_nodes): value = frozenset(bns[value])
        bns[bn].add((type, rel, value))


def parse_rdfxml(object f, list objs, list datas, object insert_objs, object insert_datas, object _abbreviate, object new_blank, str default_base = ""):
  cdef object parser = xml.parsers.expat.ParserCreate(None, "")
  try:
    parser.buffer_text          = True
    parser.specified_attributes = True
  except: pass
  
  cdef list stack                    = [["", ""]] # List of [parse type, value] pairs
  cdef dict prefixes                 = {}
  cdef list prefixess                = [prefixes]
  cdef bint tag_is_predicate         = False
  cdef int current_blank             = 0
  cdef int current_fake_blank        = 0
  cdef str current_content           = ""
  cdef dict current_attrs            = None
  cdef int nb_triple                 = 0
  cdef object bns                    = defaultdict(set)
  cdef bint dont_create_unnamed_bn   = False
  cdef dict axiom_annotation_sources = {}
  cdef dict axiom_annotation_props   = {}
  cdef dict axiom_annotation_targets = {}
  cdef object triples_with_unnamed_bn= defaultdict(list)
  
  cdef str xml_base
  cdef str xml_dir
  
  if default_base:
    xml_base = default_base
    if xml_base.endswith("#") or xml_base.endswith("/"): xml_base = xml_base[:-1]
    xml_dir  = xml_base.rsplit("/", 1)[0] + "/"
  else:
    xml_base                 = ""
    xml_dir                  = ""
    
  cdef object node_2_blanks = defaultdict(new_blank)
  cdef set known_nodes      = set()
  
  def startNamespace(str prefix, str uri):
    nonlocal prefixess, prefixes
    prefixes = prefixes.copy()
    prefixess.append(prefixes)
    
    if prefix: prefixes[prefix  ] = uri
    else:      prefixes[""      ] = uri
      
  def endNamespace(str prefix):
    nonlocal prefixess, prefixes
    prefixess.pop()
    prefixes = prefixess[-1]
    
  def startElement(str tag, dict attrs):
    nonlocal tag_is_predicate, stack, current_content, current_attrs, current_fake_blank, dont_create_unnamed_bn, xml_base, xml_dir, known_nodes, node_2_blanks
    cdef str iri
    cdef str namespace_base
    
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
            else:                       iri = urljoin(xml_dir, iri)
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
      if iri is None:
        iri = attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#nodeID")
        if iri:
          iri = node_2_blanks[iri]
          known_nodes.add(iri)
        else:
          if dont_create_unnamed_bn:
            #iri = new_fake_blank()
            current_fake_blank += 1
            iri = "_ %s" % current_fake_blank
            
          else:                      iri = new_blank()
      else:
        if not ":" in iri:
          if not iri:                 iri = xml_base
          elif   iri.startswith("#"): iri = xml_base + iri
          elif   iri.startswith("/"): iri = xml_dir  + iri[1:]
          else:                       iri = urljoin(xml_dir, iri)
          
      if tag != "http://www.w3.org/1999/02/22-rdf-syntax-ns#Description":
        if not iri.startswith("_ "):
          on_prepare_obj(iri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", tag, objs, _abbreviate, insert_objs)
        if iri.startswith("_"):
          add_to_bn(bns, known_nodes,  iri, "REL", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", tag)
          
      if stack[-1][0] == "Collection":
        stack[-1][1].append(iri)
        
      else:
        if stack[-1][0] == "Literal": stack[-1][0] = "Resource"
        stack[-1][1] = iri
        
        
  def endElement(str tag):
    nonlocal tag_is_predicate, dont_create_unnamed_bn,  stack, axiom_annotation_sources, axiom_annotation_props, axiom_annotation_targets, triples_with_unnamed_bn
    cdef str iri
    cdef str parse_type
    cdef object value
    cdef object o
    cdef list triples
    
    if tag_is_predicate:
      parse_type, value = stack.pop()
      
      if stack[-1][0] == "Collection": iri = stack[-1][1][-1]
      else:                            iri = stack[-1][1]
      
      if   tag == "http://www.w3.org/2002/07/owl#annotatedSource":
        dont_create_unnamed_bn = False
        axiom_annotation_sources[iri] = value
        if isinstance(value, str) and value.startswith("_ "):
          triples_with_unnamed_bn[iri].insert(0, (tag, value, parser.CurrentLineNumber, parser.CurrentColumnNumber))
          
          tag_is_predicate = not tag_is_predicate
          return
        
      elif tag == "http://www.w3.org/2002/07/owl#annotatedProperty":
        axiom_annotation_props  [iri] = value
      
      elif tag == "http://www.w3.org/2002/07/owl#annotatedTarget":
        dont_create_unnamed_bn = False
        axiom_annotation_targets[iri] = value
        if isinstance(value, str) and value.startswith("_ "):
          triples_with_unnamed_bn[iri].append((tag, value, parser.CurrentLineNumber, parser.CurrentColumnNumber))
          
          tag_is_predicate = not tag_is_predicate
          return
        
      
      if   parse_type == "Resource":
        if not iri.startswith("_ "):
          on_prepare_obj(iri, tag, value, objs, _abbreviate, insert_objs)
          
        if iri.startswith("_"):
          add_to_bn(bns, known_nodes,  iri, "REL", tag, value)
            
        if value.startswith("_"):
          add_to_bn(bns, known_nodes,  value, "INV", tag, iri)
          
          
      elif parse_type == "Literal":
        o = current_content
        d = current_attrs.get("http://www.w3.org/XML/1998/namespacelang")
        if d is None:
          d = current_attrs.get("http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype", "")
          if   d in INT_DATATYPES:   o = int  (o)
          elif d in FLOAT_DATATYPES: o = float(o)
          #else:                      o = o.replace('"', '\\"').replace("\n", "\\n")
        else:
          d = "@%s" % d
          #o = o.replace('"', '\\"').replace("\n", "\\n")
          
        if not iri.startswith("_ "):
          on_prepare_data(iri, tag, o, d, datas, _abbreviate, insert_datas)
        if iri.startswith("_"):
          add_to_bn(bns, known_nodes,  iri, "DAT", tag, o, d)
          
      elif parse_type == "Collection":
        if not iri.startswith("_ "):
          on_prepare_obj(iri, tag, new_list(value, objs, insert_objs, _abbreviate, new_blank), objs, _abbreviate, insert_objs)
        if iri.startswith("_"):
          add_to_bn(bns, known_nodes,  iri, "COL", tag, value)
          
          
    tag_is_predicate = not tag_is_predicate
    
    
  def characters(str content):
    nonlocal current_content,  stack
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
    raise OwlReadyOntologyParsingError("RDF/XML parsing error in file %s, line %s, column %s." % (getattr(f, "name", "???"), parser.CurrentLineNumber, parser.CurrentColumnNumber)) from e
  
  cdef object content_2_bns
  cdef str bn
  cdef set content
  if triples_with_unnamed_bn:
    content_2_bns = defaultdict(list)
    for bn, content in bns.items():
      if not bn.startswith("_ "):
        content_2_bns[frozenset(content)].append(bn)
        
    def rebuild_bn(object content):
      nonlocal content_2_bns
      cdef str bn = new_blank()
      content_2_bns[frozenset(content)].append(bn)
      cdef tuple i
      cdef object drop
      cdef str p
      cdef str d
      cdef object o
      cdef list l
      for i in content:
        if   i[0] == "REL":
          drop, p, o = i
          if not isinstance(o, str): o = rebuild_bn(o)
          on_prepare_obj(bn, p, o, objs, _abbreviate, insert_objs)
        elif i[0] == "DAT":
          drop, p, o, d = i
          if not isinstance(o, str): o = rebuild_bn(o)
          on_prepare_data(bn, p, o, d, datas, _abbreviate, insert_datas)
        elif i[0] == "INV":
          drop, p, o = i
          if not isinstance(o, str): o = rebuild_bn(o)
          on_prepare_obj(o, p, bn, objs, _abbreviate, insert_objs)
        elif i[0] == "COL":
          drop, p, *l = i
          l = [(isinstance(x, str) and x) or rebuild_bn(x) for x in l]
          on_prepare_obj(bn, p, new_list(l, objs, insert_objs, _abbreviate, new_blank), objs, _abbreviate, insert_objs)
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
            if target.startswith("_"): target = frozenset(bns[target])
            candidates_bn = content_2_bns[frozenset(content | { ("REL", axiom_annotation_props[axiom_iri], target) })]
            
          else:
            source = axiom_annotation_sources[axiom_iri]
            if source.startswith("_"):
              source = frozenset(bns[source] | { ("REL", axiom_annotation_props[axiom_iri], target) })
            candidates_bn = (content_2_bns[frozenset(content | { ("INV", axiom_annotation_props[axiom_iri], source) })] or
                             content_2_bns[frozenset(content)])
            
          if candidates_bn: o = candidates_bn[-1]
          else:
            o = rebuild_bn(content)
          on_prepare_obj(axiom_iri,p,o, objs, _abbreviate, insert_objs)
        except Exception as e:
          raise OwlReadyOntologyParsingError("RDF/XML parsing error in file %s, line %s, column %s." % (getattr(f, "name", "???"), line, column)) from e
        
    
  return nb_triple








cdef str rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

cdef dict types = {
  "http://www.w3.org/2002/07/owl#Class"              : "http://www.w3.org/2002/07/owl#Class",
  "http://www.w3.org/2002/07/owl#NamedIndividual"    : "http://www.w3.org/2002/07/owl#NamedIndividual",
  "http://www.w3.org/2002/07/owl#ObjectProperty"     : "http://www.w3.org/2002/07/owl#ObjectProperty",
  "http://www.w3.org/2002/07/owl#DataProperty"       : "http://www.w3.org/2002/07/owl#DatatypeProperty",
  "http://www.w3.org/2002/07/owl#AnnotationProperty" : "http://www.w3.org/2002/07/owl#AnnotationProperty",
}

cdef dict prop_types = {
  "http://www.w3.org/2002/07/owl#FunctionalObjectProperty"        : "http://www.w3.org/2002/07/owl#FunctionalProperty",
  "http://www.w3.org/2002/07/owl#FunctionalDataProperty"          : "http://www.w3.org/2002/07/owl#FunctionalProperty",
  "http://www.w3.org/2002/07/owl#InverseFunctionalObjectProperty" : "http://www.w3.org/2002/07/owl#InverseFunctionalProperty",
  "http://www.w3.org/2002/07/owl#InverseFunctionalDataProperty"   : "http://www.w3.org/2002/07/owl#InverseFunctionalProperty",
  "http://www.w3.org/2002/07/owl#IrreflexiveObjectProperty"       : "http://www.w3.org/2002/07/owl#IrreflexiveProperty",
  "http://www.w3.org/2002/07/owl#IrreflexiveDataProperty"         : "http://www.w3.org/2002/07/owl#IrreflexiveProperty",
  "http://www.w3.org/2002/07/owl#ReflexiveObjectProperty"         : "http://www.w3.org/2002/07/owl#ReflexiveProperty",
  "http://www.w3.org/2002/07/owl#ReflexiveDataProperty"           : "http://www.w3.org/2002/07/owl#ReflexiveProperty",
  "http://www.w3.org/2002/07/owl#SymmetricObjectProperty"         : "http://www.w3.org/2002/07/owl#SymmetricProperty",
  "http://www.w3.org/2002/07/owl#SymmetricDataProperty"           : "http://www.w3.org/2002/07/owl#SymmetricProperty",
  "http://www.w3.org/2002/07/owl#AsymmetricObjectProperty"        : "http://www.w3.org/2002/07/owl#AsymmetricProperty",
  "http://www.w3.org/2002/07/owl#AsymmetricDataProperty"          : "http://www.w3.org/2002/07/owl#AsymmetricProperty",
  "http://www.w3.org/2002/07/owl#TransitiveObjectProperty"        : "http://www.w3.org/2002/07/owl#TransitiveProperty",
  "http://www.w3.org/2002/07/owl#TransitiveDataProperty"          : "http://www.w3.org/2002/07/owl#TransitiveProperty",
}

cdef dict sub_ofs = {
  "http://www.w3.org/2002/07/owl#SubClassOf"              : "http://www.w3.org/2000/01/rdf-schema#subClassOf",
  "http://www.w3.org/2002/07/owl#SubPropertyOf"           : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "http://www.w3.org/2002/07/owl#SubObjectPropertyOf"     : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "http://www.w3.org/2002/07/owl#SubDataPropertyOf"       : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "http://www.w3.org/2002/07/owl#SubAnnotationPropertyOf" : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  }

cdef dict equivs = {
  "http://www.w3.org/2002/07/owl#EquivalentClasses" : "http://www.w3.org/2002/07/owl#equivalentClass",
  "http://www.w3.org/2002/07/owl#EquivalentProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#EquivalentObjectProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#EquivalentDataProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#EquivalentAnnotationProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#SameIndividual" : "http://www.w3.org/2002/07/owl#sameAs",
  }

cdef dict restrs = {
  "http://www.w3.org/2002/07/owl#ObjectSomeValuesFrom" : "http://www.w3.org/2002/07/owl#someValuesFrom",
  "http://www.w3.org/2002/07/owl#ObjectAllValuesFrom"  : "http://www.w3.org/2002/07/owl#allValuesFrom",
  "http://www.w3.org/2002/07/owl#DataSomeValuesFrom"   : "http://www.w3.org/2002/07/owl#someValuesFrom",
  "http://www.w3.org/2002/07/owl#DataAllValuesFrom"    : "http://www.w3.org/2002/07/owl#allValuesFrom",
  "http://www.w3.org/2002/07/owl#ObjectHasValue"       : "http://www.w3.org/2002/07/owl#hasValue",
  "http://www.w3.org/2002/07/owl#DataHasValue"         : "http://www.w3.org/2002/07/owl#hasValue",
  }

cdef dict qual_card_restrs = {
  "http://www.w3.org/2002/07/owl#ObjectExactCardinality" : "http://www.w3.org/2002/07/owl#qualifiedCardinality",
  "http://www.w3.org/2002/07/owl#ObjectMinCardinality"   : "http://www.w3.org/2002/07/owl#minQualifiedCardinality",
  "http://www.w3.org/2002/07/owl#ObjectMaxCardinality"   : "http://www.w3.org/2002/07/owl#maxQualifiedCardinality",
  "http://www.w3.org/2002/07/owl#DataExactCardinality"   : "http://www.w3.org/2002/07/owl#qualifiedCardinality",
  "http://www.w3.org/2002/07/owl#DataMinCardinality"     : "http://www.w3.org/2002/07/owl#minQualifiedCardinality",
  "http://www.w3.org/2002/07/owl#DataMaxCardinality"     : "http://www.w3.org/2002/07/owl#maxQualifiedCardinality",
  }

cdef dict card_restrs = {
  "http://www.w3.org/2002/07/owl#ObjectExactCardinality" : "http://www.w3.org/2002/07/owl#cardinality",
  "http://www.w3.org/2002/07/owl#ObjectMinCardinality"   : "http://www.w3.org/2002/07/owl#minCardinality",
  "http://www.w3.org/2002/07/owl#ObjectMaxCardinality"   : "http://www.w3.org/2002/07/owl#maxCardinality",
  "http://www.w3.org/2002/07/owl#DataExactCardinality"   : "http://www.w3.org/2002/07/owl#cardinality",
  "http://www.w3.org/2002/07/owl#DataMinCardinality"     : "http://www.w3.org/2002/07/owl#minCardinality",
  "http://www.w3.org/2002/07/owl#DataMaxCardinality"     : "http://www.w3.org/2002/07/owl#maxCardinality",
  }

cdef dict disjoints = {
  "http://www.w3.org/2002/07/owl#DisjointClasses"              : ("http://www.w3.org/2002/07/owl#AllDisjointClasses"   , "http://www.w3.org/2002/07/owl#disjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DisjointObjectProperties"     : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DisjointDataProperties"       : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DisjointAnnotationProperties" : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DifferentIndividuals"         : ("http://www.w3.org/2002/07/owl#AllDifferent"         , None, "http://www.w3.org/2002/07/owl#distinctMembers"),
}

    
cdef int _rindex(list l):
  i = len(l) - 1
  while l[i] != "(": i -= 1
  return i


def parse_owlxml(object f, list objs, list datas, object insert_objs, object insert_datas, object _abbreviate, object new_blank, str default_base = ""):
  cdef object parser = xml.parsers.expat.ParserCreate(None, "")
  try:
    parser.buffer_text          = True
    parser.specified_attributes = True
  except: pass
  
  cdef str ontology_iri           = ""
  cdef list stack                 = []
  cdef list annots                = []
  cdef dict prefixes              = {}
  cdef str current_content        = ""
  cdef dict current_attrs         = None
  cdef int current_blank          = 0
  cdef bint in_declaration        = False
  cdef bint in_prop_chain         = False
  cdef bint before_declaration    = True
  cdef str last_cardinality       = "0"
  cdef int nb_triple              = 0
  cdef str lang
  
  def _unabbreviate_IRI(str _abbreviated_iri):
    cdef str prefix, name
    prefix, name = _abbreviated_iri.split(":", 1)
    return prefixes[prefix] + name
  
  def get_IRI(dict attrs):
    nonlocal ontology_iri
    cdef str iri
    if "IRI" in attrs:
      iri = attrs["IRI"]
      if not iri: return ontology_iri
      if   iri.startswith("#") or iri.startswith("/"): iri = ontology_iri + iri
      return iri
    return _unabbreviate_IRI(attrs["_abbreviatedIRI"])
  
  def startElement(str tag, dict attrs):
    nonlocal current_content, current_attrs, in_declaration, before_declaration, last_cardinality, in_prop_chain, ontology_iri
    current_content = ""
    if   (tag == "http://www.w3.org/2002/07/owl#Prefix"):
      prefixes[attrs["name"]] = attrs["IRI"]
    
    elif (tag == "http://www.w3.org/2002/07/owl#Declaration"):
      in_declaration     = True
      before_declaration = False
      
    elif (tag in types):
      iri = get_IRI(attrs)
      if in_declaration: on_prepare_obj(iri, rdf_type, types[tag], objs, _abbreviate, insert_objs)
      stack.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#Datatype"):           stack.append(get_IRI(attrs))
    
    elif (tag == "http://www.w3.org/2002/07/owl#Literal"):            current_attrs = attrs
    
    elif((tag == "http://www.w3.org/2002/07/owl#ObjectIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#ObjectUnionOf") or
         (tag == "http://www.w3.org/2002/07/owl#ObjectOneOf") or (tag == "http://www.w3.org/2002/07/owl#DataOneOf") or
         (tag == "http://www.w3.org/2002/07/owl#DataIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#DataUnionOf") or
         (tag == "http://www.w3.org/2002/07/owl#DisjointClasses") or (tag == "http://www.w3.org/2002/07/owl#DisjointObjectProperties") or (tag == "http://www.w3.org/2002/07/owl#DisjointDataProperties") or (tag == "http://www.w3.org/2002/07/owl#DifferentIndividuals")):
      stack.append("(")
      
    elif((tag == "http://www.w3.org/2002/07/owl#ObjectExactCardinality") or (tag == "http://www.w3.org/2002/07/owl#ObjectMinCardinality") or (tag == "http://www.w3.org/2002/07/owl#ObjectMaxCardinality") or
         (tag == "http://www.w3.org/2002/07/owl#DataExactCardinality"  ) or (tag == "http://www.w3.org/2002/07/owl#DataMinCardinality"  ) or (tag == "http://www.w3.org/2002/07/owl#DataMaxCardinality"  )):
      stack.append("(")
      last_cardinality = attrs["cardinality"]
      
    elif (tag == "http://www.w3.org/2002/07/owl#AnonymousIndividual"): stack.append(new_blank())
    
    elif (tag == "http://www.w3.org/2002/07/owl#SubObjectPropertyOf"): in_prop_chain = False
    
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectInverseOf") or (tag == "http://www.w3.org/2002/07/owl#DataInverseOf") or (tag == "http://www.w3.org/2002/07/owl#inverseOf"): stack.append(new_blank())
    
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyChain"): stack.append("(")
    
    elif (tag == "http://www.w3.org/2002/07/owl#DatatypeRestriction"): stack.append("(")
    
    elif (tag == "http://www.w3.org/2002/07/owl#FacetRestriction"): stack.append(attrs["facet"])
    
    elif (tag == "http://www.w3.org/2002/07/owl#Ontology"):
      ontology_iri = attrs["ontologyIRI"]
      on_prepare_obj(ontology_iri, rdf_type, "http://www.w3.org/2002/07/owl#Ontology", objs, _abbreviate, insert_objs)
      version_iri = attrs.get("versionIRI")
      if version_iri:
        on_prepare_obj(ontology_iri, "http://www.w3.org/2002/07/owl#versionIRI", version_iri, objs, _abbreviate, insert_objs)
      
    elif (tag == "RDF") or (tag == "rdf:RDF"): raise ValueError("Not an OWL/XML file! (It seems to be an OWL/RDF file)")
    
    
  def endElement(str tag):
    nonlocal in_declaration, stack, in_prop_chain

    if   (tag == "http://www.w3.org/2002/07/owl#Declaration"):
      in_declaration = False
      stack = [] # Purge stack
      
    elif (tag == "http://www.w3.org/2002/07/owl#Literal"):
      lang = current_attrs.get("http://www.w3.org/XML/1998/namespacelang", "")
      if lang != "": stack.append((current_content, "@%s" % lang))
      else:
        d = current_attrs.get("datatypeIRI", "")
        if   d in INT_DATATYPES:   stack.append((int  (current_content), d))
        elif d in FLOAT_DATATYPES: stack.append((float(current_content), d))
        else:                      stack.append((current_content       , d))
        
    elif (tag == "http://www.w3.org/2002/07/owl#SubClassOf") or (tag == "http://www.w3.org/2002/07/owl#SubObjectPropertyOf") or (tag == "http://www.w3.org/2002/07/owl#SubDataPropertyOf") or (tag == "http://www.w3.org/2002/07/owl#SubAnnotationPropertyOf"):
      parent = stack.pop()
      child  = stack.pop()
      if (tag == "http://www.w3.org/2002/07/owl#SubObjectPropertyOf") and in_prop_chain:
        relation = "http://www.w3.org/2002/07/owl#propertyChainAxiom"
        parent, child = child, parent
      else:
        relation = sub_ofs[tag]
      on_prepare_obj(child, relation, parent, objs, _abbreviate, insert_objs)
      if annots: purge_annotations((child, relation, parent))
      
    elif (tag == "http://www.w3.org/2002/07/owl#ClassAssertion"):
      child  = stack.pop() # Order is reversed compared to SubClassOf!
      parent = stack.pop()
      on_prepare_obj(child, rdf_type, parent, objs, _abbreviate, insert_objs)
      if annots: purge_annotations((child, rdf_type, parent))
      
    elif (tag == "http://www.w3.org/2002/07/owl#EquivalentClasses") or (tag == "http://www.w3.org/2002/07/owl#EquivalentObjectProperties") or (tag == "http://www.w3.org/2002/07/owl#EquivalentDataProperties"):
      o1 = stack.pop()
      o2 = stack.pop()
      if o1.startswith("_"): o1, o2 = o2, o1 # Swap in order to have blank node at third position -- rapper seems to do that
      on_prepare_obj(o1, equivs[tag], o2, objs, _abbreviate, insert_objs)
      if annots: purge_annotations((o1, equivs[tag], o2))
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyDomain") or (tag == "http://www.w3.org/2002/07/owl#DataPropertyDomain") or (tag == "http://www.w3.org/2002/07/owl#AnnotationPropertyDomain"):
      val = stack.pop(); obj = stack.pop();
      on_prepare_obj(obj, "http://www.w3.org/2000/01/rdf-schema#domain", val, objs, _abbreviate, insert_objs)
      if annots: purge_annotations((obj, "http://www.w3.org/2000/01/rdf-schema#domain", val))
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyRange") or (tag == "http://www.w3.org/2002/07/owl#DataPropertyRange") or (tag == "http://www.w3.org/2002/07/owl#AnnotationPropertyRange"):
      val = stack.pop(); obj = stack.pop();
      on_prepare_obj(obj, "http://www.w3.org/2000/01/rdf-schema#range", val, objs, _abbreviate, insert_objs)
      if annots: purge_annotations((obj, "http://www.w3.org/2000/01/rdf-schema#range", val))
      
    elif (tag in prop_types):
      obj = stack.pop()
      on_prepare_obj(obj, rdf_type, prop_types[tag], objs, _abbreviate, insert_objs)
      
    elif (tag == "http://www.w3.org/2002/07/owl#InverseObjectProperties") or (tag == "http://www.w3.org/2002/07/owl#InverseDataProperties"):
      a, b = stack.pop(), stack.pop()
      on_prepare_obj(b, "http://www.w3.org/2002/07/owl#inverseOf", a, objs, _abbreviate, insert_objs)
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyChain"):
      start    = _rindex(stack)
      list_iri = new_list(stack[start + 1 : ], objs, insert_objs, _abbreviate, new_blank)
      in_prop_chain = True
      stack[start :] = [list_iri]
      
    elif (tag in disjoints):
      start    = _rindex(stack)
      list_obj = stack[start + 1 : ]
      tag, rel, member = disjoints[tag]
      if rel and (len(list_obj) == 2):
        on_prepare_obj(list_obj[0], rel, list_obj[1], objs, _abbreviate, insert_objs)
        if annots: purge_annotations((list_obj[0], rel, list_obj[1]))
        
      else:
        list_iri = new_list(list_obj, objs, insert_objs, _abbreviate, new_blank)
        iri = new_blank()
        on_prepare_obj(iri, rdf_type, tag, objs, _abbreviate, insert_objs)
        on_prepare_obj(iri, member, list_iri, objs, _abbreviate, insert_objs)
        if annots: purge_annotations((iri, rdf_type, tag))
        
      del stack[start :]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyAssertion"):
      p,s,o = stack[-3 :]
      on_prepare_obj(s, p, o, objs, _abbreviate, insert_objs)
      if annots: purge_annotations((s,p,o))
      del stack[-3 :]
      
    elif (tag == "http://www.w3.org/2002/07/owl#DataPropertyAssertion"):
      p,s,o = stack[-3 :]
      on_prepare_data(s, p, o[0], o[1], datas, _abbreviate, insert_datas)
      if annots: purge_annotations((s,p,o))
      del stack[-3 :]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectComplementOf") or (tag == "http://www.w3.org/2002/07/owl#DataComplementOf"):
      iri = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class", objs, _abbreviate, insert_objs)
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#complementOf", stack[-1], objs, _abbreviate, insert_objs)
      stack[-1] = iri
    
    elif (tag in restrs):
      iri = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Restriction", objs, _abbreviate, insert_objs)
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onProperty", stack.pop(-2), objs, _abbreviate, insert_objs)
      on_prepare_triple(iri, restrs[tag], stack[-1], objs, datas, _abbreviate, insert_objs, insert_datas)
      stack[-1] = iri
      
    elif (tag in card_restrs):
      iri = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Restriction", objs, _abbreviate, insert_objs)
      start = _rindex(stack)
      values = stack[start + 1 : ]
      del stack[start :]
      
      if len(values) == 2: # Qualified
        tag = qual_card_restrs[tag]
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onProperty", values[-2], objs, _abbreviate, insert_objs)
        if stack[-1].startswith("http://www.w3.org/2001/XMLSchema"):
          on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onDataRange", values[-1], objs, _abbreviate, insert_objs)
        else:
          on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onClass", values[-1], objs, _abbreviate, insert_objs)
      else: # Non qualified
        tag = card_restrs[tag]
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onProperty", values[-1], objs, _abbreviate, insert_objs)
      on_prepare_data(iri, tag, last_cardinality, "http://www.w3.org/2001/XMLSchema#nonNegativeInteger", datas, _abbreviate, insert_datas)
      stack.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectOneOf"):
      start    = _rindex(stack)
      list_iri = new_list(stack[start + 1 : ], objs, insert_objs, _abbreviate, new_blank)
      iri      = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class", objs, _abbreviate, insert_objs)
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#oneOf", list_iri, objs, _abbreviate, insert_objs)
      stack[start :] = [iri]
      
    elif (tag == "http://www.w3.org/2002/07/owl#DataOneOf"):
      start    = _rindex(stack)
      list_iri = new_data_list(stack[start + 1 : ], objs, datas, insert_objs, insert_datas, _abbreviate, new_blank)
      iri      = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype", objs, _abbreviate, insert_objs)
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#oneOf", list_iri, objs, _abbreviate, insert_objs)
      stack[start :] = [iri]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#ObjectUnionOf") or (tag == "http://www.w3.org/2002/07/owl#DataIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#DataUnionOf"):
      start    = _rindex(stack)
      list_iri = new_list(stack[start + 1 : ], objs, insert_objs, _abbreviate, new_blank)
      iri      = new_blank()
      if stack[start + 1 : ][0].startswith("http://www.w3.org/2001/XMLSchema"):
        on_prepare_obj(iri, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype", objs, _abbreviate, insert_objs)
      else:
        on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class", objs, _abbreviate, insert_objs)
      if (tag == "http://www.w3.org/2002/07/owl#ObjectIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#DataIntersectionOf"):
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#intersectionOf", list_iri, objs, _abbreviate, insert_objs)
      else:
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#unionOf", list_iri, objs, _abbreviate, insert_objs)
      stack[start :] = [iri]
      
    elif (tag == "http://www.w3.org/2002/07/owl#Import"):
      on_prepare_data(ontology_iri, "http://www.w3.org/2002/07/owl#imports", current_content, "", datas, _abbreviate, insert_datas)
      
    elif (tag == "http://www.w3.org/2002/07/owl#IRI"):
      iri = current_content
      if not iri: iri = ontology_iri
      else:
        if iri.startswith("#") or iri.startswith("/"): iri = ontology_iri + iri
      stack.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#AbbreviatedIRI"):
      iri = _unabbreviate_IRI(current_content)
      stack.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#AnnotationAssertion"):
      on_prepare_triple(stack[-2], stack[-3], stack[-1], objs, datas, _abbreviate, insert_objs, insert_datas)
      if annots: purge_annotations((stack[-2], stack[-3], stack[-1]))
      
    elif (tag == "http://www.w3.org/2002/07/owl#Annotation"):
      if before_declaration: # On ontology
        on_prepare_triple(ontology_iri, stack[-2], stack[-1], objs, datas, _abbreviate, insert_objs, insert_datas)
      else:
        annots.append((stack[-2], stack[-1]))
      del stack[-2:]
      
    elif (tag == "http://www.w3.org/2002/07/owl#DatatypeRestriction"):
      start               = _rindex(stack)
      datatype, *list_bns = stack[start + 1 : ]
      list_bns            = new_list(list_bns, objs, insert_objs, _abbreviate, new_blank)
      bn                  = new_blank()
      stack[start :]  = [bn]
      on_prepare_obj(bn, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype", objs, _abbreviate, insert_objs)
      on_prepare_obj(bn, "http://www.w3.org/2002/07/owl#onDatatype", datatype, objs, _abbreviate, insert_objs)
      on_prepare_obj(bn, "http://www.w3.org/2002/07/owl#withRestrictions", list_bns, objs, _abbreviate, insert_objs)
      
    elif (tag == "http://www.w3.org/2002/07/owl#FacetRestriction"):
      facet, literal = stack[-2:]
      bn = new_blank()
      on_prepare_triple(bn, facet, literal, objs, datas, _abbreviate, insert_objs, insert_datas)
      stack[-2:] = [bn]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectInverseOf") or (tag == "http://www.w3.org/2002/07/owl#DataInverseOf") or (tag == "http://www.w3.org/2002/07/owl#inverseOf"):
      bn, prop = stack[-2:]
      on_prepare_obj(bn, "http://www.w3.org/2002/07/owl#inverseOf", prop, objs, _abbreviate, insert_objs)
      
      stack[-2:] = [bn]
    
      
  def characters(str content):
    nonlocal current_content
    current_content += content
    
  def purge_annotations(on_iri):
    nonlocal annots
    cdef str s, p, prop_iri
    cdef object value, o
    
    if isinstance(on_iri, tuple):
      s,p,o  = on_iri
      on_iri = new_blank()
      on_prepare_obj(on_iri, rdf_type, "http://www.w3.org/2002/07/owl#Axiom", objs, _abbreviate, insert_objs)
      on_prepare_obj(on_iri, "http://www.w3.org/2002/07/owl#annotatedSource", s, objs, _abbreviate, insert_objs)
      on_prepare_obj(on_iri, "http://www.w3.org/2002/07/owl#annotatedProperty", p, objs, _abbreviate, insert_objs)
      on_prepare_triple(on_iri, "http://www.w3.org/2002/07/owl#annotatedTarget", o, objs, datas, _abbreviate, insert_objs, insert_datas)

    for prop_iri, value in annots:
      on_prepare_triple(on_iri, prop_iri, value, objs, datas, _abbreviate, insert_objs, insert_datas)
    annots = []


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
    raise OwlReadyOntologyParsingError("OWL/XML parsing error in file %s, line %s, column %s." % (getattr(f, "name", "???"), parser.CurrentLineNumber, parser.CurrentColumnNumber)) from e
  
  return nb_triple

