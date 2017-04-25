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

import sys, os, warnings
import xml, xml.sax as sax, xml.sax.handler
from collections import defaultdict

rdf_type                  = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
rdf_first                 = "http://www.w3.org/1999/02/22-rdf-syntax-ns#first"
rdf_rest                  = "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest"
rdf_nil                   = "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil"

types      = {
  "Class"              : "http://www.w3.org/2002/07/owl#Class",
  "NamedIndividual"    : "http://www.w3.org/2002/07/owl#NamedIndividual",
  "ObjectProperty"     : "http://www.w3.org/2002/07/owl#ObjectProperty",
  "DataProperty"       : "http://www.w3.org/2002/07/owl#DatatypeProperty",
  "AnnotationProperty" : "http://www.w3.org/2002/07/owl#AnnotationProperty",
}

prop_types = {
  "FunctionalObjectProperty"        : "http://www.w3.org/2002/07/owl#FunctionalProperty",
  "FunctionalDataProperty"          : "http://www.w3.org/2002/07/owl#FunctionalProperty",
  "InverseFunctionalObjectProperty" : "http://www.w3.org/2002/07/owl#InverseFunctionalProperty",
  "InverseFunctionalDataProperty"   : "http://www.w3.org/2002/07/owl#InverseFunctionalProperty",
  "IrreflexiveObjectProperty"       : "http://www.w3.org/2002/07/owl#IrreflexiveProperty",
  "IrreflexiveDataProperty"         : "http://www.w3.org/2002/07/owl#IrreflexiveProperty",
  "ReflexiveObjectProperty"         : "http://www.w3.org/2002/07/owl#ReflexiveProperty",
  "ReflexiveDataProperty"           : "http://www.w3.org/2002/07/owl#ReflexiveProperty",
  "SymmetricObjectProperty"         : "http://www.w3.org/2002/07/owl#SymmetricProperty",
  "SymmetricDataProperty"           : "http://www.w3.org/2002/07/owl#SymmetricProperty",
  "AsymmetricObjectProperty"        : "http://www.w3.org/2002/07/owl#AsymmetricProperty",
  "AsymmetricDataProperty"          : "http://www.w3.org/2002/07/owl#AsymmetricProperty",
  "TransitiveObjectProperty"        : "http://www.w3.org/2002/07/owl#TransitiveProperty",
  "TransitiveDataProperty"          : "http://www.w3.org/2002/07/owl#TransitiveProperty",
}

sub_ofs = {
  "SubClassOf"              : "http://www.w3.org/2000/01/rdf-schema#subClassOf",
  "SubPropertyOf"           : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "SubObjectPropertyOf"     : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "SubDataPropertyOf"       : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "SubAnnotationPropertyOf" : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  }

equivs = {
  "EquivalentClasses" : "http://www.w3.org/2002/07/owl#equivalentClass",
  "EquivalentProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "EquivalentObjectProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "EquivalentDataProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "EquivalentAnnotationProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "" : "http://www.w3.org/2002/07/owl#sameAs",
  }

restrs = {
  "ObjectSomeValuesFrom" : "http://www.w3.org/2002/07/owl#someValuesFrom",
  "ObjectAllValuesFrom"  : "http://www.w3.org/2002/07/owl#allValuesFrom",
  "DataSomeValuesFrom"   : "http://www.w3.org/2002/07/owl#someValuesFrom",
  "DataAllValuesFrom"    : "http://www.w3.org/2002/07/owl#allValuesFrom",
  "ObjectHasValue"       : "http://www.w3.org/2002/07/owl#hasValue",
  "DataHasValue"         : "http://www.w3.org/2002/07/owl#hasValue",
  }

qual_card_restrs = {
  "ObjectExactCardinality" : "http://www.w3.org/2002/07/owl#qualifiedCardinality",
  "ObjectMinCardinality" : "http://www.w3.org/2002/07/owl#minQualifiedCardinality",
  "ObjectMaxCardinality" : "http://www.w3.org/2002/07/owl#maxQualifiedCardinality",
  "DataExactCardinality" : "http://www.w3.org/2002/07/owl#qualifiedCardinality",
  "DataMinCardinality" : "http://www.w3.org/2002/07/owl#minQualifiedCardinality",
  "DataMaxCardinality" : "http://www.w3.org/2002/07/owl#maxQualifiedCardinality",
  }

card_restrs = {
  "ObjectExactCardinality" : "http://www.w3.org/2002/07/owl#cardinality",
  "ObjectMinCardinality" : "http://www.w3.org/2002/07/owl#minCardinality",
  "ObjectMaxCardinality" : "http://www.w3.org/2002/07/owl#maxCardinality",
  "DataExactCardinality" : "http://www.w3.org/2002/07/owl#cardinality",
  "DataMinCardinality" : "http://www.w3.org/2002/07/owl#minCardinality",
  "DataMaxCardinality" : "http://www.w3.org/2002/07/owl#maxCardinality",
  }

disjoints = {
  "DisjointClasses"              : ("http://www.w3.org/2002/07/owl#AllDisjointClasses"   , "http://www.w3.org/2002/07/owl#disjointWith", "http://www.w3.org/2002/07/owl#members"),
  "DisjointObjectProperties"     : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "DisjointDataProperties"       : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "DisjointAnnotationProperties" : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "DifferentIndividuals"         : ("http://www.w3.org/2002/07/owl#AllDifferent"         , None, "http://www.w3.org/2002/07/owl#distinctMembers"),
}

class OWLXMLHandler(sax.handler.ContentHandler):
  def __init__(self, on_triple = None):
    self.objs                   = []
    self.annots                 = []
    self.prefixes               = {}
    self.current_content        = ""
    self.current_lang           = None
    self.current_blank          = 0
    self.in_declaration         = False
    self.before_declaration     = True
    if on_triple:
      self._on_triple            = on_triple
      
  def new_blank(self):
    self.current_blank += 1
    return "_:%s" % self.current_blank
  
  def new_list(self, l):
    iri = iri0 = self.new_blank()
    
    if not l:
      self.on_triple(iri, rdf_first, rdf_nil)
      self.on_triple(iri, rdf_rest,  rdf_nil)
      
    else:
      for i in range(len(l)):
        self.on_triple(iri, rdf_first, l[i])
        if i < len(l) - 1:
          iri_next = self.new_blank()
          self.on_triple(iri, rdf_rest, iri_next)
          iri = iri_next
        else:
          self.on_triple(iri, rdf_rest, rdf_nil)
          
    return iri0
    
  def on_triple(self, s,p,o):
    if not s.startswith("_"): s = "<%s>" % s
    p = "<%s>" % p
    if not (o.startswith("_") or o.startswith('"')): o = "<%s>" % o
    self._on_triple(s,p,o)
    
  def _on_triple(self, s,p,o):
    print("%s %s %s ." % (s,p,o))
    
  def push(self, value): self.objs.append(value)
    
  def unabbreviate_IRI(self, abbreviated_iri):
    prefix, name = abbreviated_iri.split(":", 1)
    return self.prefixes[prefix] + name
  
  def get_IRI(self, attrs):
    if "IRI" in attrs:
      iri = attrs["IRI"]
      if iri.startswith("#"): iri = "%s#%s" % (self.ontology_iri, iri[1:])
      return iri
    return self.unabbreviate_IRI(attrs["abbreviatedIRI"])
  
  def get_loc(self): return self._locator.getSystemId(), self._locator.getLineNumber(), self._locator.getColumnNumber()
  
  def startElement(self, tag, attrs):
    self.current_content = u""
    if   (tag == "Prefix"): self.prefixes[attrs["name"]] = attrs["IRI"]
    
    elif (tag == "Declaration"):
      self.in_declaration     = True
      self.before_declaration = False
      
    elif (tag in types):
      iri = self.get_IRI(attrs)
      if self.in_declaration: self.on_triple(iri, rdf_type, types[tag])
      self.push(iri)
      
    elif (tag == "Datatype"):           self.push(self.get_IRI(attrs))
    elif (tag == "Literal"):            self.push(attrs["datatypeIRI"]); self.current_lang = attrs.get("xml:lang", "")
    
    elif((tag == "ObjectIntersectionOf") or (tag == "ObjectUnionOf") or (tag == "ObjectOneOf") or
         (tag == "DataIntersectionOf") or (tag == "DataUnionOf") or
         (tag == "DisjointClasses") or (tag == "DisjointObjectProperties") or (tag == "DisjointDataProperties") or (tag == "DifferentIndividuals")):
      self.push("(")
      
    elif((tag == "ObjectExactCardinality") or (tag == "ObjectMinCardinality") or (tag == "ObjectMaxCardinality") or
         (tag == "DataExactCardinality"  ) or (tag == "DataMinCardinality"  ) or (tag == "DataMaxCardinality"  )):
      self.push("(")
      self.last_cardinality = int(attrs["cardinality"])
      
    elif (tag == "AnonymousIndividual"): self.push(self.new_blank())
    
    elif (tag == "ObjectInverseOf") or (tag == "DataInverseOf") or (tag == "inverseOf"): self.push(self.new_blank())
    
    elif (tag == "DatatypeRestriction"): self.push("(")
    
    elif (tag == "FacetRestriction"): self.push(attrs["facet"])
    
    elif (tag == "AnnotationAssertion") or (tag == "Annotation"): self.current_lang = None
    
    elif (tag == "Ontology"):
      self.ontology_iri = attrs["ontologyIRI"]
      self.on_triple(self.ontology_iri, rdf_type, "http://www.w3.org/2002/07/owl#Ontology")
            
    elif (tag == "RDF") or (tag == "rdf:RDF"): raise ValueError("Not an OWL/XML file! (It seems to be an OWL/RDF file)")
    
    
  def endElement(self, tag):
    if   (tag == "Declaration"):
      self.in_declaration = False
      self.objs = [] # Purge stack
      
    elif (tag == "Literal"):
      if   self.current_lang:
        self.objs[-1] = '"%s"@%s'    % (self.current_content, self.current_lang)
      elif self.objs[-1] and (self.objs[-1] != "http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral"):
        self.objs[-1] = '"%s"^^<%s>' % (self.current_content, self.objs[-1])
      else:
        self.objs[-1] = '"%s"'       %  self.current_content
      
    elif (tag == "SubClassOf") or (tag == "SubObjectPropertyOf") or (tag == "SubDataPropertyOf") or (tag == "SubAnnotationPropertyOf"):
      parent = self.objs.pop()
      child  = self.objs.pop()
      self.on_triple(child, sub_ofs[tag], parent)
      if self.annots: self.purge_annotations((child, sub_ofs[tag], parent))
      
    elif (tag == "ClassAssertion"):
      child  = self.objs.pop() # Order is reversed compared to SubClassOf!
      parent = self.objs.pop()
      self.on_triple(child, rdf_type, parent)
      if self.annots: self.purge_annotations((child, rdf_type, parent))
      
    elif (tag == "EquivalentClasses") or (tag == "EquivalentObjectProperties") or (tag == "EquivalentDataProperties"):
      o1 = self.objs.pop()
      o2 = self.objs.pop()
      if o1.startswith("_"): o1, o2 = o2, o1 # Swap in order to have bank node at third position -- rapper seems to do that
      self.on_triple(o1, equivs[tag], o2)
      if self.annots: self.purge_annotations((o2, equivs[tag], o1))
      
    elif (tag == "ObjectPropertyDomain") or (tag == "DataPropertyDomain") or (tag == "AnnotationPropertyDomain"):
      val = self.objs.pop(); obj = self.objs.pop();
      self.on_triple(obj, "http://www.w3.org/2000/01/rdf-schema#domain", val)
      if self.annots: self.purge_annotations((obj, "http://www.w3.org/2000/01/rdf-schema#domain", val))
      
    elif (tag == "ObjectPropertyRange") or (tag == "DataPropertyRange") or (tag == "AnnotationPropertyRange"):
      val = self.objs.pop(); obj = self.objs.pop();
      self.on_triple(obj, "http://www.w3.org/2000/01/rdf-schema#range", val)
      if self.annots: self.purge_annotations((obj, "http://www.w3.org/2000/01/rdf-schema#range", val))
      
    elif (tag in prop_types):
      obj = self.objs.pop()
      self.on_triple(obj, rdf_type, prop_types[tag])
      
    elif (tag == "InverseObjectProperties") or (tag == "InverseDataProperties"):
      a, b = self.objs.pop(), self.objs.pop()
      self.on_triple(b, "http://www.w3.org/2002/07/owl#inverseOf", a)
      
    elif (tag in disjoints):
      start = _rindex(self.objs, "(")
      list_obj = self.objs[start + 1 : ]
      tag, rel, member = disjoints[tag]
      if rel and (len(list_obj) == 2):
        self.on_triple(list_obj[0], rel, list_obj[1])
        
      else:
        list_iri = self.new_list(list_obj)
        iri = self.new_blank()
        self.on_triple(iri, rdf_type, tag)
        self.on_triple(iri, member, list_iri)
        
      del self.objs[start :]
      
    elif (tag == "ObjectPropertyAssertion") or (tag == "DataPropertyAssertion"):
      p,s,o = self.objs[-3 :]
      self.on_triple(s, p, o)
      if self.annots: self.purge_annotations((s,p,o))
      del self.objs[-3 :]
      
    elif (tag == "ObjectComplementOf") or (tag == "DataComplementOf"):
      iri = self.new_blank()
      self.on_triple(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class")
      self.on_triple(iri, "http://www.w3.org/2002/07/owl#complementOf", self.objs[-1])
      self.objs[-1] = iri
    
    elif (tag in restrs):
      iri = self.new_blank()
      self.on_triple(iri, rdf_type, "http://www.w3.org/2002/07/owl#Restriction")
      self.on_triple(iri, "http://www.w3.org/2002/07/owl#onProperty", self.objs.pop(-2))
      self.on_triple(iri, restrs[tag], self.objs.pop())
      self.push(iri)
      
    elif (tag in card_restrs):
      iri = self.new_blank()
      self.on_triple(iri, rdf_type, "http://www.w3.org/2002/07/owl#Restriction")
      self.on_triple(iri, "http://www.w3.org/2002/07/owl#onProperty", self.objs.pop(-2))
      start = _rindex(self.objs, "(")
      objs = self.objs[start + 1 : ]
      del self.objs[start :]
      if len(objs) == 1: # Qualified
        tag = qual_card_restrs[tag]
        if objs[-1].startswith("http://www.w3.org/2001/XMLSchema"):
          self.on_triple(iri, "http://www.w3.org/2002/07/owl#onDataRange", objs[-1])
        else:
          self.on_triple(iri, "http://www.w3.org/2002/07/owl#onClass", objs[-1])
      else: # Non qualified
        tag = card_restrs[tag]
      self.on_triple(iri, tag, '"%s"^^<http://www.w3.org/2001/XMLSchema#nonNegativeInteger>' % self.last_cardinality)
      
      self.push(iri)
      
    elif (tag == "ObjectOneOf"):
      start = _rindex(self.objs, "(")
      list_iri = self.new_list(self.objs[start + 1 : ])
      iri = self.new_blank()
      self.on_triple(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class")
      self.on_triple(iri, "http://www.w3.org/2002/07/owl#oneOf", list_iri)
      self.objs[start :] = [iri]
      
    elif (tag == "ObjectIntersectionOf") or (tag == "ObjectUnionOf") or (tag == "DataIntersectionOf") or (tag == "DataUnionOf"):
      start = _rindex(self.objs, "(")
      list_iri = self.new_list(self.objs[start + 1 : ])
      iri = self.new_blank()
      if self.objs[start + 1 : ][0].startswith("http://www.w3.org/2001/XMLSchema"):
        self.on_triple(iri, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype")
      else:
        self.on_triple(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class")
      if (tag == "ObjectIntersectionOf") or (tag == "DataIntersectionOf"):
        self.on_triple(iri, "http://www.w3.org/2002/07/owl#intersectionOf", list_iri)
      else:
        self.on_triple(iri, "http://www.w3.org/2002/07/owl#unionOf", list_iri)
      self.objs[start :] = [iri]
      
    elif (tag == "Import"):
      self.on_triple(self.ontology_iri, "http://www.w3.org/2002/07/owl#imports", self.current_content)
      
    elif (tag == "IRI"):
      iri = self.current_content
      if iri.startswith("#"): iri = "%s#%s" % (self.ontology_iri, iri[1:])
      self.push(iri)
      
    elif (tag == "AbbreviatedIRI"):
      iri = self.unabbreviate_IRI(self.current_content)
      self.push(iri)
      
    elif (tag == "AnnotationAssertion"):
      self.on_triple(self.objs[-2], self.objs[-3], self.objs[-1])
      del self.objs[-3:]
      
    elif (tag == "Annotation"):
      if self.before_declaration: # On ontology
        self.on_triple(self.ontology_iri, self.objs[-2], self.objs[-1])
      else:
        self.annots.append((self.objs[-2], self.objs[-1]))
      del self.objs[-2:]
      
    elif (tag == "DatatypeRestriction"):
      start               = _rindex(self.objs, "(")
      datatype, *list_bns = self.objs[start + 1 : ]
      list_bns            = self.new_list(list_bns)
      bn                  = self.new_blank()
      self.objs[start :]  = [bn]
      self.on_triple(bn, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype")
      self.on_triple(bn, "http://www.w3.org/2002/07/owl#onDatatype", datatype)
      self.on_triple(bn, "http://www.w3.org/2002/07/owl#withRestrictions", list_bns)
      
    elif (tag == "FacetRestriction"):
      facet, literal = self.objs[-2:]
      bn = self.new_blank()
      self.on_triple(bn, facet, literal)
      self.objs[-2:] = [bn]
      
    elif (tag == "ObjectInverseOf") or (tag == "DataInverseOf") or (tag == "inverseOf"):
      bn, prop = self.objs[-2:]
      self.on_triple(bn, "http://www.w3.org/2002/07/owl#inverseOf", prop)
      
      self.objs[-2:] = [bn]
      
      
  def characters(self, content): self.current_content += content
  
  def purge_annotations(self, on_iri):
    if isinstance(on_iri, tuple):
      s,p,o  = on_iri
      on_iri = self.new_blank()
      self.on_triple(on_iri, rdf_type, "http://www.w3.org/2002/07/owl#Axiom")
      self.on_triple(on_iri, "http://www.w3.org/2002/07/owl#annotatedSource", s)
      self.on_triple(on_iri, "http://www.w3.org/2002/07/owl#annotatedProperty", p)
      self.on_triple(on_iri, "http://www.w3.org/2002/07/owl#annotatedTarget", o)
      
    for prop_iri, value in self.annots: self.on_triple(on_iri, prop_iri, value)
    self.annots = []
  
def _rindex(l, o): return len(l) - list(reversed(l)).index(o) - 1

    
def parse(f, on_triple = None):
  parser = sax.make_parser()
  parser.setContentHandler(OWLXMLHandler(on_triple))
  parser.parse(f)
  

if __name__ == "__main__":
  filename = sys.argv[-1]
  parse(filename)
