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

import sys, xml.parsers.expat

try:
  from owlready2.base import OwlReadyOntologyParsingError
except:
  class OwlReadyOntologyParsingError(Exception): pass

INT_DATATYPES   = { "http://www.w3.org/2001/XMLSchema#integer", "http://www.w3.org/2001/XMLSchema#byte", "http://www.w3.org/2001/XMLSchema#short", "http://www.w3.org/2001/XMLSchema#int", "http://www.w3.org/2001/XMLSchema#long", "http://www.w3.org/2001/XMLSchema#unsignedByte", "http://www.w3.org/2001/XMLSchema#unsignedShort", "http://www.w3.org/2001/XMLSchema#unsignedInt", "http://www.w3.org/2001/XMLSchema#unsignedLong", "http://www.w3.org/2001/XMLSchema#negativeInteger", "http://www.w3.org/2001/XMLSchema#nonNegativeInteger", "http://www.w3.org/2001/XMLSchema#positiveInteger" }
FLOAT_DATATYPES = { "http://www.w3.org/2001/XMLSchema#decimal", "http://www.w3.org/2001/XMLSchema#double", "http://www.w3.org/2001/XMLSchema#float", "http://www.w3.org/2002/07/owl#real" }

rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

types = {
  "http://www.w3.org/2002/07/owl#Class"              : "http://www.w3.org/2002/07/owl#Class",
  "http://www.w3.org/2002/07/owl#NamedIndividual"    : "http://www.w3.org/2002/07/owl#NamedIndividual",
  "http://www.w3.org/2002/07/owl#ObjectProperty"     : "http://www.w3.org/2002/07/owl#ObjectProperty",
  "http://www.w3.org/2002/07/owl#DataProperty"       : "http://www.w3.org/2002/07/owl#DatatypeProperty",
  "http://www.w3.org/2002/07/owl#AnnotationProperty" : "http://www.w3.org/2002/07/owl#AnnotationProperty",
}

prop_types = {
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

sub_ofs = {
  "http://www.w3.org/2002/07/owl#SubClassOf"              : "http://www.w3.org/2000/01/rdf-schema#subClassOf",
  "http://www.w3.org/2002/07/owl#SubPropertyOf"           : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "http://www.w3.org/2002/07/owl#SubObjectPropertyOf"     : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "http://www.w3.org/2002/07/owl#SubDataPropertyOf"       : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  "http://www.w3.org/2002/07/owl#SubAnnotationPropertyOf" : "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
  }

equivs = {
  "http://www.w3.org/2002/07/owl#EquivalentClasses" : "http://www.w3.org/2002/07/owl#equivalentClass",
  "http://www.w3.org/2002/07/owl#EquivalentProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#EquivalentObjectProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#EquivalentDataProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#EquivalentAnnotationProperties" : "http://www.w3.org/2002/07/owl#equivalentProperty",
  "http://www.w3.org/2002/07/owl#SameIndividual" : "http://www.w3.org/2002/07/owl#sameAs",
  }

restrs = {
  "http://www.w3.org/2002/07/owl#ObjectSomeValuesFrom" : "http://www.w3.org/2002/07/owl#someValuesFrom",
  "http://www.w3.org/2002/07/owl#ObjectAllValuesFrom"  : "http://www.w3.org/2002/07/owl#allValuesFrom",
  "http://www.w3.org/2002/07/owl#DataSomeValuesFrom"   : "http://www.w3.org/2002/07/owl#someValuesFrom",
  "http://www.w3.org/2002/07/owl#DataAllValuesFrom"    : "http://www.w3.org/2002/07/owl#allValuesFrom",
  "http://www.w3.org/2002/07/owl#ObjectHasValue"       : "http://www.w3.org/2002/07/owl#hasValue",
  "http://www.w3.org/2002/07/owl#DataHasValue"         : "http://www.w3.org/2002/07/owl#hasValue",
  }

qual_card_restrs = {
  "http://www.w3.org/2002/07/owl#ObjectExactCardinality" : "http://www.w3.org/2002/07/owl#qualifiedCardinality",
  "http://www.w3.org/2002/07/owl#ObjectMinCardinality"   : "http://www.w3.org/2002/07/owl#minQualifiedCardinality",
  "http://www.w3.org/2002/07/owl#ObjectMaxCardinality"   : "http://www.w3.org/2002/07/owl#maxQualifiedCardinality",
  "http://www.w3.org/2002/07/owl#DataExactCardinality"   : "http://www.w3.org/2002/07/owl#qualifiedCardinality",
  "http://www.w3.org/2002/07/owl#DataMinCardinality"     : "http://www.w3.org/2002/07/owl#minQualifiedCardinality",
  "http://www.w3.org/2002/07/owl#DataMaxCardinality"     : "http://www.w3.org/2002/07/owl#maxQualifiedCardinality",
  }

card_restrs = {
  "http://www.w3.org/2002/07/owl#ObjectExactCardinality" : "http://www.w3.org/2002/07/owl#cardinality",
  "http://www.w3.org/2002/07/owl#ObjectMinCardinality"   : "http://www.w3.org/2002/07/owl#minCardinality",
  "http://www.w3.org/2002/07/owl#ObjectMaxCardinality"   : "http://www.w3.org/2002/07/owl#maxCardinality",
  "http://www.w3.org/2002/07/owl#DataExactCardinality"   : "http://www.w3.org/2002/07/owl#cardinality",
  "http://www.w3.org/2002/07/owl#DataMinCardinality"     : "http://www.w3.org/2002/07/owl#minCardinality",
  "http://www.w3.org/2002/07/owl#DataMaxCardinality"     : "http://www.w3.org/2002/07/owl#maxCardinality",
  }

disjoints = {
  "http://www.w3.org/2002/07/owl#DisjointClasses"              : ("http://www.w3.org/2002/07/owl#AllDisjointClasses"   , "http://www.w3.org/2002/07/owl#disjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DisjointObjectProperties"     : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DisjointDataProperties"       : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DisjointAnnotationProperties" : ("http://www.w3.org/2002/07/owl#AllDisjointProperties", "http://www.w3.org/2002/07/owl#propertyDisjointWith", "http://www.w3.org/2002/07/owl#members"),
  "http://www.w3.org/2002/07/owl#DifferentIndividuals"         : ("http://www.w3.org/2002/07/owl#AllDifferent"         , None, "http://www.w3.org/2002/07/owl#distinctMembers"),
}



def parse(f, on_prepare_obj = None, on_prepare_data = None, new_blank = None, default_base = ""):
  parser = xml.parsers.expat.ParserCreate(None, "")
  try:
    parser.buffer_text          = True
    parser.specified_attributes = True
  except: pass
  
  ontology_iri           = ""
  objs                   = []
  annots                 = []
  prefixes               = {}
  current_content        = ""
  current_attrs          = None
  current_blank          = 0
  in_declaration         = False
  in_prop_chain          = False
  before_declaration     = True
  last_cardinality       = "0"
  nb_triple              = 0
  

  if not on_prepare_obj:
    def on_prepare_obj(s,p,o):
      nonlocal nb_triple
      nb_triple += 1
      if not s.startswith("_"): s = "<%s>" % s
      if not o.startswith("_"): o = "<%s>" % o
      print("%s %s %s ." % (s,"<%s>" % p,o))
      
    def on_prepare_data(s,p,o,d):
      nonlocal nb_triple
      nb_triple += 1
      if not s.startswith("_"): s = "<%s>" % s
      
      #o = o.replace('"', '\\"').replace("\n", "\\n")
      if d and d.startswith("@"):
        print('%s %s "%s"%s .' % (s,"<%s>" % p,o,d))
      elif d:
        print('%s %s "%s"^^<%s> .' % (s,"<%s>" % p,o,d))
      else:
        print('%s %s "%s" .' % (s,"<%s>" % p,o))


  def on_prepare_triple(s,p,o):
    if isinstance(o, tuple): on_prepare_data(s, p, o[0], o[1])
    else:                    on_prepare_obj (s, p, o)
    
  if not new_blank:
    def new_blank():
      nonlocal current_blank
      current_blank += 1
      return "_:%s" % current_blank
    
  def new_list(l):
    bn = bn0 = new_blank()
    
    if l:
      for i in range(len(l) - 1):
        on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[i])
        bn_next = new_blank()
        on_prepare_obj   (bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", bn_next)
        bn = bn_next
      on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", l[-1])
      on_prepare_obj   (bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      
    else:
      on_prepare_triple(bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first", "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      on_prepare_obj   (bn, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest",  "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
      
    return bn0
  
  
  
  def _unabbreviate_IRI(_abbreviated_iri):
    prefix, name = _abbreviated_iri.split(":", 1)
    return prefixes[prefix] + name
  
  def get_IRI(attrs):
    if "IRI" in attrs:
      iri = attrs["IRI"]
      if not iri: return ontology_iri
      if   iri.startswith("#") or iri.startswith("/"): iri = ontology_iri + iri
      return iri
    return _unabbreviate_IRI(attrs["abbreviatedIRI"])
  
  def startElement(tag, attrs):
    nonlocal current_content, current_attrs, in_declaration, before_declaration, last_cardinality, in_prop_chain, ontology_iri
    current_content = ""
    if   (tag == "http://www.w3.org/2002/07/owl#Prefix"):
      prefixes[attrs["name"]] = attrs["IRI"]
    
    elif (tag == "http://www.w3.org/2002/07/owl#Declaration"):
      in_declaration     = True
      before_declaration = False
      
    elif (tag in types):
      iri = get_IRI(attrs)
      if in_declaration: on_prepare_obj(iri, rdf_type, types[tag])
      objs.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#Datatype"):           objs.append(get_IRI(attrs))
    
    elif (tag == "http://www.w3.org/2002/07/owl#Literal"):            current_attrs = attrs
    
    elif((tag == "http://www.w3.org/2002/07/owl#ObjectIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#ObjectUnionOf") or
         (tag == "http://www.w3.org/2002/07/owl#ObjectOneOf") or (tag == "http://www.w3.org/2002/07/owl#DataOneOf") or
         (tag == "http://www.w3.org/2002/07/owl#DataIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#DataUnionOf") or
         (tag == "http://www.w3.org/2002/07/owl#DisjointClasses") or (tag == "http://www.w3.org/2002/07/owl#DisjointObjectProperties") or (tag == "http://www.w3.org/2002/07/owl#DisjointDataProperties") or (tag == "http://www.w3.org/2002/07/owl#DifferentIndividuals")):
      objs.append("(")
      
    elif((tag == "http://www.w3.org/2002/07/owl#ObjectExactCardinality") or (tag == "http://www.w3.org/2002/07/owl#ObjectMinCardinality") or (tag == "http://www.w3.org/2002/07/owl#ObjectMaxCardinality") or
         (tag == "http://www.w3.org/2002/07/owl#DataExactCardinality"  ) or (tag == "http://www.w3.org/2002/07/owl#DataMinCardinality"  ) or (tag == "http://www.w3.org/2002/07/owl#DataMaxCardinality"  )):
      objs.append("(")
      last_cardinality = attrs["cardinality"]
      
    elif (tag == "http://www.w3.org/2002/07/owl#AnonymousIndividual"): objs.append(new_blank())
    
    elif (tag == "http://www.w3.org/2002/07/owl#SubObjectPropertyOf"): in_prop_chain = False
    
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectInverseOf") or (tag == "http://www.w3.org/2002/07/owl#DataInverseOf") or (tag == "http://www.w3.org/2002/07/owl#inverseOf"): objs.append(new_blank())
    
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyChain"): objs.append("(")
    
    elif (tag == "http://www.w3.org/2002/07/owl#DatatypeRestriction"): objs.append("(")
    
    elif (tag == "http://www.w3.org/2002/07/owl#FacetRestriction"): objs.append(attrs["facet"])
    
    elif (tag == "http://www.w3.org/2002/07/owl#Ontology"):
      ontology_iri = attrs["ontologyIRI"]
      on_prepare_obj(ontology_iri, rdf_type, "http://www.w3.org/2002/07/owl#Ontology")
      version_iri = attrs.get("versionIRI")
      if version_iri:
        on_prepare_obj(ontology_iri, "http://www.w3.org/2002/07/owl#versionIRI", version_iri)
        
    elif (tag == "RDF") or (tag == "rdf:RDF"): raise ValueError("Not an OWL/XML file! (It seems to be an OWL/RDF file)")
    
    
  def endElement(tag):
    nonlocal in_declaration, objs, in_prop_chain
    
    if   (tag == "http://www.w3.org/2002/07/owl#Declaration"):
      in_declaration = False
      objs = [] # Purge stack
      
    elif (tag == "http://www.w3.org/2002/07/owl#Literal"):
      lang = current_attrs.get("http://www.w3.org/XML/1998/namespacelang")
      if lang: objs.append((current_content, "@%s" % lang))
      else:
        d = current_attrs.get("datatypeIRI", "")
        if   d in INT_DATATYPES:   o = int  (current_content)
        elif d in FLOAT_DATATYPES: o = float(current_content)
        else:                      o =       current_content
        objs.append((o, d))
        
    elif (tag == "http://www.w3.org/2002/07/owl#SubClassOf") or (tag == "http://www.w3.org/2002/07/owl#SubObjectPropertyOf") or (tag == "http://www.w3.org/2002/07/owl#SubDataPropertyOf") or (tag == "http://www.w3.org/2002/07/owl#SubAnnotationPropertyOf"):
      parent = objs.pop()
      child  = objs.pop()
      if (tag == "http://www.w3.org/2002/07/owl#SubObjectPropertyOf") and in_prop_chain:
        relation = "http://www.w3.org/2002/07/owl#propertyChainAxiom"
        parent, child = child, parent
      else:
        relation = sub_ofs[tag]
      on_prepare_obj(child, relation, parent)
      if annots: purge_annotations((child, relation, parent))
      
    elif (tag == "http://www.w3.org/2002/07/owl#ClassAssertion"):
      child  = objs.pop() # Order is reversed compared to SubClassOf!
      parent = objs.pop()
      on_prepare_obj(child, rdf_type, parent)
      if annots: purge_annotations((child, rdf_type, parent))
      
    elif (tag == "http://www.w3.org/2002/07/owl#EquivalentClasses") or (tag == "http://www.w3.org/2002/07/owl#EquivalentObjectProperties") or (tag == "http://www.w3.org/2002/07/owl#EquivalentDataProperties"):
      o1 = objs.pop()
      o2 = objs.pop()
      if (isinstance(o1, int) and (o1 < 0)) or (isinstance(o1, str) and o1.startswith("_")): o1, o2 = o2, o1 # Swap in order to have blank node at third position -- rapper seems to do that
      on_prepare_obj(o1, equivs[tag], o2)
      if annots: purge_annotations((o1, equivs[tag], o2))
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyDomain") or (tag == "http://www.w3.org/2002/07/owl#DataPropertyDomain") or (tag == "http://www.w3.org/2002/07/owl#AnnotationPropertyDomain"):
      val = objs.pop(); obj = objs.pop();
      on_prepare_obj(obj, "http://www.w3.org/2000/01/rdf-schema#domain", val)
      if annots: purge_annotations((obj, "http://www.w3.org/2000/01/rdf-schema#domain", val))
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyRange") or (tag == "http://www.w3.org/2002/07/owl#DataPropertyRange") or (tag == "http://www.w3.org/2002/07/owl#AnnotationPropertyRange"):
      val = objs.pop(); obj = objs.pop();
      on_prepare_obj(obj, "http://www.w3.org/2000/01/rdf-schema#range", val)
      if annots: purge_annotations((obj, "http://www.w3.org/2000/01/rdf-schema#range", val))
      
    elif (tag in prop_types):
      obj = objs.pop()
      on_prepare_obj(obj, rdf_type, prop_types[tag])
      
    elif (tag == "http://www.w3.org/2002/07/owl#InverseObjectProperties") or (tag == "http://www.w3.org/2002/07/owl#InverseDataProperties"):
      a, b = objs.pop(), objs.pop()
      on_prepare_obj(b, "http://www.w3.org/2002/07/owl#inverseOf", a)
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyChain"):
      start    = _rindex(objs)
      list_iri = new_list(objs[start + 1 : ])
      in_prop_chain = True
      objs[start :] = [list_iri]
      
    elif (tag in disjoints):
      start    = _rindex(objs)
      list_obj = objs[start + 1 : ]
      tag, rel, member = disjoints[tag]
      if rel and (len(list_obj) == 2):
        on_prepare_obj(list_obj[0], rel, list_obj[1])
        if annots: purge_annotations((list_obj[0], rel, list_obj[1]))
        
      else:
        list_iri = new_list(list_obj)
        iri = new_blank()
        on_prepare_obj(iri, rdf_type, tag)
        on_prepare_obj(iri, member, list_iri)
        if annots: purge_annotations((iri, rdf_type, tag))
        
      del objs[start :]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectPropertyAssertion"):
      p,s,o = objs[-3 :]
      on_prepare_obj(s, p, o)
      if annots: purge_annotations((s,p,o))
      del objs[-3 :]
      
    elif (tag == "http://www.w3.org/2002/07/owl#DataPropertyAssertion"):
      p,s,o = objs[-3 :]
      on_prepare_data(s, p, *o)
      if annots: purge_annotations((s,p,o))
      del objs[-3 :]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectComplementOf") or (tag == "http://www.w3.org/2002/07/owl#DataComplementOf"):
      iri = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class")
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#complementOf", objs[-1])
      objs[-1] = iri
    
    elif (tag in restrs):
      iri = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Restriction")
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onProperty", objs.pop(-2))
      on_prepare_triple(iri, restrs[tag], objs[-1])
      objs[-1] = iri
      
    elif (tag in card_restrs):
      iri = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Restriction")
      start = _rindex(objs)
      values = objs[start + 1 : ]
      del objs[start :]
      
      if len(values) == 2: # Qualified
        tag = qual_card_restrs[tag]
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onProperty", values[-2])
        if isinstance(objs[-1], str) and objs[-1].startswith("http://www.w3.org/2001/XMLSchema"):
          on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onDataRange", values[-1])
        else:
          on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onClass", values[-1])
      else: # Non qualified
        tag = card_restrs[tag]
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#onProperty", values[-1])
      on_prepare_data(iri, tag, last_cardinality, "http://www.w3.org/2001/XMLSchema#nonNegativeInteger")
      objs.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectOneOf"):
      start    = _rindex(objs)
      list_iri = new_list(objs[start + 1 : ])
      iri      = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class")
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#oneOf", list_iri)
      objs[start :] = [iri]
      
    elif (tag == "http://www.w3.org/2002/07/owl#DataOneOf"):
      start    = _rindex(objs)
      list_iri = new_list(objs[start + 1 : ])
      iri      = new_blank()
      on_prepare_obj(iri, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype")
      on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#oneOf", list_iri)
      objs[start :] = [iri]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#ObjectUnionOf") or (tag == "http://www.w3.org/2002/07/owl#DataIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#DataUnionOf"):
      start    = _rindex(objs)
      list_iri = new_list(objs[start + 1 : ])
      iri      = new_blank()
      if isinstance(objs[start + 1 : ][0], str) and objs[start + 1 : ][0].startswith("http://www.w3.org/2001/XMLSchema"):
        on_prepare_obj(iri, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype")
      else:
        on_prepare_obj(iri, rdf_type, "http://www.w3.org/2002/07/owl#Class")
      if (tag == "http://www.w3.org/2002/07/owl#ObjectIntersectionOf") or (tag == "http://www.w3.org/2002/07/owl#DataIntersectionOf"):
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#intersectionOf", list_iri)
      else:
        on_prepare_obj(iri, "http://www.w3.org/2002/07/owl#unionOf", list_iri)
      objs[start :] = [iri]
      
    elif (tag == "http://www.w3.org/2002/07/owl#Import"):
      on_prepare_data(ontology_iri, "http://www.w3.org/2002/07/owl#imports", current_content, "")
      
    elif (tag == "http://www.w3.org/2002/07/owl#IRI"):
      iri = current_content
      if not iri: iri = ontology_iri
      else:
        if iri.startswith("#") or iri.startswith("/"): iri = ontology_iri + iri
      objs.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#AbbreviatedIRI"):
      iri = _unabbreviate_IRI(current_content)
      objs.append(iri)
      
    elif (tag == "http://www.w3.org/2002/07/owl#AnnotationAssertion"):
      on_prepare_triple(objs[-2], objs[-3], objs[-1])
      if annots: purge_annotations((objs[-2], objs[-3], objs[-1]))
      
    elif (tag == "http://www.w3.org/2002/07/owl#Annotation"):
      if before_declaration: # On ontology
        on_prepare_triple(ontology_iri, objs[-2], objs[-1])
      else:
        annots.append((objs[-2], objs[-1]))
      del objs[-2:]
      
    elif (tag == "http://www.w3.org/2002/07/owl#DatatypeRestriction"):
      start               = _rindex(objs)
      datatype, *list_bns = objs[start + 1 : ]
      list_bns            = new_list(list_bns)
      bn                  = new_blank()
      objs[start :]  = [bn]
      on_prepare_obj(bn, rdf_type, "http://www.w3.org/2000/01/rdf-schema#Datatype")
      on_prepare_obj(bn, "http://www.w3.org/2002/07/owl#onDatatype", datatype)
      on_prepare_obj(bn, "http://www.w3.org/2002/07/owl#withRestrictions", list_bns)
      
    elif (tag == "http://www.w3.org/2002/07/owl#FacetRestriction"):
      facet, literal = objs[-2:]
      bn = new_blank()
      on_prepare_triple(bn, facet, literal)
      objs[-2:] = [bn]
      
    elif (tag == "http://www.w3.org/2002/07/owl#ObjectInverseOf") or (tag == "http://www.w3.org/2002/07/owl#DataInverseOf") or (tag == "http://www.w3.org/2002/07/owl#inverseOf"):
      bn, prop = objs[-2:]
      on_prepare_obj(bn, "http://www.w3.org/2002/07/owl#inverseOf", prop)
      
      objs[-2:] = [bn]
    
      
  def characters(content):
    nonlocal current_content
    current_content += content
    
  def purge_annotations(on_iri):
    nonlocal annots
    if isinstance(on_iri, tuple):
      s,p,o  = on_iri
      on_iri = new_blank()
      on_prepare_obj(on_iri, rdf_type, "http://www.w3.org/2002/07/owl#Axiom")
      on_prepare_obj(on_iri, "http://www.w3.org/2002/07/owl#annotatedSource", s)
      on_prepare_obj(on_iri, "http://www.w3.org/2002/07/owl#annotatedProperty", p)
      on_prepare_triple(on_iri, "http://www.w3.org/2002/07/owl#annotatedTarget", o)
      
    for prop_iri, value in annots: on_prepare_triple(on_iri, prop_iri, value)
    annots = []


  #parser.StartNamespaceDeclHandler = startNamespace
  #parser.EndNamespaceDeclHandler   = endNamespace
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



    
def _rindex(l):
  i = len(l) - 1
  while l[i] != "(": i -= 1
  return i

    


if __name__ == "__main__":
  filename = sys.argv[-1]

  import time
  t = time.time()
  nb_triple = parse(filename)
  t = time.time() - t
  print("# %s triples read in %ss" % (nb_triple, t), file = sys.stderr)
