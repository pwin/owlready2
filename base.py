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

import sys, os, types, tempfile, subprocess, weakref, re, urllib.request, warnings, itertools
from io import StringIO
from collections import defaultdict, OrderedDict
from xml.sax.saxutils import escape
import datetime

from owlready2.util import *

#_HERE = os.path.dirname(__file__)

class OwlReadyWarning                     (UserWarning): pass
class OwlReadyUndefinedIRIWarning         (OwlReadyWarning): pass
class OwlReadyOntologyIRIWarning          (OwlReadyWarning): pass
class OwlReadyMROWarning                  (OwlReadyWarning): pass
class OwlReadyGeneratedNameWarning        (OwlReadyWarning): pass
class OwlReadyDupplicatedNameWarning      (OwlReadyWarning): pass

class OwlReadyError(Exception): pass
class OwlReadySharedBlankNodeError(OwlReadyError): pass
class OwlReadyOntologyParsingError(OwlReadyError): pass
class OwlReadyInconsistentOntologyError(OwlReadyError): pass




def to_literal(o):
  if isinstance(o, locstr) and o.lang: return o, "@%s" % o.lang
  datatype, unparser = _universal_datatype_2_abbrev_unparser.get(o.__class__) or (None, None)
  if datatype is None: raise ValueError("Cannot store literal '%s' of type '%s'!" % (o, type(o)))
  return unparser(o), datatype
  
def from_literal(o, d):
  #from owlready2 import default_world
  #print(repr(o), repr(d), default_world._unabbreviate(d))
  if isinstance(d, str) and d.startswith("@"): return locstr(o, lang = d[1:])
  if d == 0: return o
  datatype, parser = _universal_abbrev_2_datatype_parser.get(d) or (None, None)
  if parser is None: raise ValueError("Cannot read literal of datatype '%s'!" % repr(d))
  return parser(o)

_universal_abbrev_2_iri = {}
_universal_iri_2_abbrev = {}
_next_abb = 1
def _universal_abbrev(iri):
  global _next_abb
  abb = _next_abb
  _next_abb += 1
  _universal_abbrev_2_iri[abb] = iri
  _universal_iri_2_abbrev[iri] = abb
  return abb

owlready_python_module    = _universal_abbrev("http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#python_module")
owlready_python_name      = _universal_abbrev("http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#python_name")

rdf_first                 = _universal_abbrev("http://www.w3.org/1999/02/22-rdf-syntax-ns#first")
rdf_rest                  = _universal_abbrev("http://www.w3.org/1999/02/22-rdf-syntax-ns#rest")
rdf_nil                   = _universal_abbrev("http://www.w3.org/1999/02/22-rdf-syntax-ns#nil")
rdf_type                  = _universal_abbrev("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
rdf_domain                = _universal_abbrev("http://www.w3.org/2000/01/rdf-schema#domain")
rdf_range                 = _universal_abbrev("http://www.w3.org/2000/01/rdf-schema#range")
rdfs_subclassof           = _universal_abbrev("http://www.w3.org/2000/01/rdf-schema#subClassOf")
rdfs_subpropertyof        = _universal_abbrev("http://www.w3.org/2000/01/rdf-schema#subPropertyOf")
owl_class                 = _universal_abbrev("http://www.w3.org/2002/07/owl#Class")
owl_named_individual      = _universal_abbrev("http://www.w3.org/2002/07/owl#NamedIndividual")
owl_object_property       = _universal_abbrev("http://www.w3.org/2002/07/owl#ObjectProperty")
owl_data_property         = _universal_abbrev("http://www.w3.org/2002/07/owl#DatatypeProperty")
owl_annotation_property   = _universal_abbrev("http://www.w3.org/2002/07/owl#AnnotationProperty")
owl_inverse_property      = _universal_abbrev("http://www.w3.org/2002/07/owl#inverseOf")
owl_restriction           = _universal_abbrev("http://www.w3.org/2002/07/owl#Restriction")
owl_onproperty            = _universal_abbrev("http://www.w3.org/2002/07/owl#onProperty")
owl_onclass               = _universal_abbrev("http://www.w3.org/2002/07/owl#onClass")
owl_ondatarange           = _universal_abbrev("http://www.w3.org/2002/07/owl#onDataRange")
owl_cardinality           = _universal_abbrev("http://www.w3.org/2002/07/owl#cardinality")
owl_min_cardinality       = _universal_abbrev("http://www.w3.org/2002/07/owl#minCardinality")
owl_max_cardinality       = _universal_abbrev("http://www.w3.org/2002/07/owl#maxCardinality")
SOME                      = _universal_abbrev("http://www.w3.org/2002/07/owl#someValuesFrom")
ONLY                      = _universal_abbrev("http://www.w3.org/2002/07/owl#allValuesFrom")
EXACTLY                   = _universal_abbrev("http://www.w3.org/2002/07/owl#qualifiedCardinality")
MIN                       = _universal_abbrev("http://www.w3.org/2002/07/owl#minQualifiedCardinality")
MAX                       = _universal_abbrev("http://www.w3.org/2002/07/owl#maxQualifiedCardinality")
VALUE                     = _universal_abbrev("http://www.w3.org/2002/07/owl#hasValue")
owl_unionof               = _universal_abbrev("http://www.w3.org/2002/07/owl#unionOf")
owl_intersectionof        = _universal_abbrev("http://www.w3.org/2002/07/owl#intersectionOf")
owl_oneof                 = _universal_abbrev("http://www.w3.org/2002/07/owl#oneOf")
owl_equivalentclass       = _universal_abbrev("http://www.w3.org/2002/07/owl#equivalentClass")
owl_thing                 = _universal_abbrev("http://www.w3.org/2002/07/owl#Thing")
owl_alldisjointclasses    = _universal_abbrev("http://www.w3.org/2002/07/owl#AllDisjointClasses")
owl_alldifferent          = _universal_abbrev("http://www.w3.org/2002/07/owl#AllDifferent")
owl_members               = _universal_abbrev("http://www.w3.org/2002/07/owl#members")
owl_distinctmembers       = _universal_abbrev("http://www.w3.org/2002/07/owl#distinctMembers")

_universal_abbrev("http://www.w3.org/2000/01/rdf-schema#comment")
_universal_abbrev("http://www.w3.org/2000/01/rdf-schema#label")
_universal_abbrev("http://www.w3.org/2002/07/owl#FunctionalProperty")
_universal_abbrev("http://www.w3.org/2002/07/owl#InverseFunctionalProperty")

SPECIAL_ATTRS      = { "namespace",  "name", "_name", "iri", "_iri", "storid", "is_a", "equivalent_to", "_equivalent_to", "disjoint_with", "_disjoint_with", "__class__", "__qualname__", "__module__", "__doc__", "__bases__" }
SPECIAL_PROP_ATTRS = { "namespace",  "name", "_name", "python_name", "_python_name", "_domain", "_property_chain", "_inverse_property", "inverse_property", "_range", "iri", "_iri", "storid", "is_a", "equivalent_to", "_equivalent_to", "disjoint_with", "_disjoint_with", "__class__", "__qualname__", "__module__", "__doc__", "__bases__" }



LOADING = Environment()
LOADING.__enter__() # Avoid creating triple when creating base classes like Thing

    
_universal_abbrev_2_datatype = {}
_universal_datatype_2_abbrev = {}

_universal_abbrev_2_datatype_parser   = {}
_universal_datatype_2_abbrev_unparser = {}

def _universal_abbrev_datatype(datatype, parser, unparser, *iris):
  abbs = [_universal_abbrev(iri) for iri in iris]
  _universal_datatype_2_abbrev         [datatype] =  abbs[0]
  _universal_datatype_2_abbrev_unparser[datatype] = (abbs[0], unparser or str)
  for abb in abbs:
    _universal_abbrev_2_datatype       [abb] =  datatype
    _universal_abbrev_2_datatype_parser[abb] = (datatype, parser or datatype)


def bool_parser(s):
  return s == "true"
def bool_unparser(b):
  if b: return "true"
  return "false"
def number_unparser(x):
  return x

def _parse_date(s):
  try:
    r = datetime.date(*(int(i or "1") or 1 for i in s.rsplit("-", 2)))
  except:
    sys.excepthook(*sys.exc_info())
    return None
  return r

_universal_abbrev_datatype(int, None, number_unparser, "http://www.w3.org/2001/XMLSchema#integer", "http://www.w3.org/2001/XMLSchema#byte", "http://www.w3.org/2001/XMLSchema#short", "http://www.w3.org/2001/XMLSchema#int", "http://www.w3.org/2001/XMLSchema#long", "http://www.w3.org/2001/XMLSchema#unsignedByte", "http://www.w3.org/2001/XMLSchema#unsignedShort", "http://www.w3.org/2001/XMLSchema#unsignedInt", "http://www.w3.org/2001/XMLSchema#unsignedLong", "http://www.w3.org/2001/XMLSchema#negativeInteger", "http://www.w3.org/2001/XMLSchema#nonNegativeInteger", "http://www.w3.org/2001/XMLSchema#positiveInteger")
_universal_abbrev_datatype(bool, bool_parser, bool_unparser, "http://www.w3.org/2001/XMLSchema#boolean")
_universal_abbrev_datatype(float, None, number_unparser, "http://www.w3.org/2001/XMLSchema#decimal", "http://www.w3.org/2001/XMLSchema#double", "http://www.w3.org/2001/XMLSchema#float", "http://www.w3.org/2002/07/owl#real")
_universal_abbrev_datatype(str, None, None, "http://www.w3.org/2001/XMLSchema#string")
_universal_abbrev_datatype(normstr, None, None, "http://www.w3.org/2001/XMLSchema#normalizedString", "http://www.w3.org/2001/XMLSchema#anyURI", "http://www.w3.org/2001/XMLSchema#Name")
_universal_abbrev_datatype(locstr, None, None, "http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral")
_universal_abbrev_datatype(datetime.datetime,
                           lambda s: datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S"),
                           datetime.datetime.isoformat, "http://www.w3.org/2001/XMLSchema#dateTime")
_universal_abbrev_datatype(datetime.date,
                           _parse_date,
                           datetime.date.isoformat, "http://www.w3.org/2001/XMLSchema#date")
_universal_abbrev_datatype(datetime.time,
                           lambda s: datetime.datetime.strptime(s, "%H:%M:%S").time(),
                           datetime.time.isoformat, "http://www.w3.org/2001/XMLSchema#time")


def set_datatype_iri(datatype, iri):
  unparser = _universal_datatype_2_abbrev_unparser[datatype][1]
  _universal_datatype_2_abbrev         [datatype] =  _universal_iri_2_abbrev[iri]
  _universal_datatype_2_abbrev_unparser[datatype] = (_universal_iri_2_abbrev[iri], unparser)


owl_alldisjointproperties = _universal_abbrev("http://www.w3.org/2002/07/owl#AllDisjointProperties")
owl_equivalentproperty    = _universal_abbrev("http://www.w3.org/2002/07/owl#equivalentProperty")
owl_equivalentindividual  = _universal_abbrev("http://www.w3.org/2002/07/owl#sameAs")
owl_ontology              = _universal_abbrev("http://www.w3.org/2002/07/owl#Ontology")
owl_imports               = _universal_abbrev("http://www.w3.org/2002/07/owl#imports")
owl_nothing               = _universal_abbrev("http://www.w3.org/2002/07/owl#Nothing")
owl_axiom                 = _universal_abbrev("http://www.w3.org/2002/07/owl#Axiom")
owl_annotatedsource       = _universal_abbrev("http://www.w3.org/2002/07/owl#annotatedSource")
owl_annotatedproperty     = _universal_abbrev("http://www.w3.org/2002/07/owl#annotatedProperty")
owl_annotatedtarget       = _universal_abbrev("http://www.w3.org/2002/07/owl#annotatedTarget")
owl_complementof          = _universal_abbrev("http://www.w3.org/2002/07/owl#complementOf")
owl_disjointwith          = _universal_abbrev("http://www.w3.org/2002/07/owl#disjointWith")
owl_propdisjointwith      = _universal_abbrev("http://www.w3.org/2002/07/owl#propertyDisjointWith")
rdfs_datatype             = _universal_abbrev("http://www.w3.org/2000/01/rdf-schema#Datatype")
owl_ondatatype            = _universal_abbrev("http://www.w3.org/2002/07/owl#onDatatype")
owl_withrestrictions      = _universal_abbrev("http://www.w3.org/2002/07/owl#withRestrictions")
xmls_length               = _universal_abbrev("http://www.w3.org/2001/XMLSchema#length")
xmls_minlength            = _universal_abbrev("http://www.w3.org/2001/XMLSchema#minLength")
xmls_maxlength            = _universal_abbrev("http://www.w3.org/2001/XMLSchema#maxLength")
xmls_pattern              = _universal_abbrev("http://www.w3.org/2001/XMLSchema#pattern")
xmls_whitespace           = _universal_abbrev("http://www.w3.org/2001/XMLSchema#whiteSpace")
xmls_maxinclusive         = _universal_abbrev("http://www.w3.org/2001/XMLSchema#maxInclusive")
xmls_maxexclusive         = _universal_abbrev("http://www.w3.org/2001/XMLSchema#maxExclusive")
xmls_mininclusive         = _universal_abbrev("http://www.w3.org/2001/XMLSchema#minInclusive")
xmls_minexclusive         = _universal_abbrev("http://www.w3.org/2001/XMLSchema#minExclusive")
xmls_totaldigits          = _universal_abbrev("http://www.w3.org/2001/XMLSchema#totalDigits")
xmls_fractiondigits       = _universal_abbrev("http://www.w3.org/2001/XMLSchema#fractionDigits")
owl_propertychain         = _universal_abbrev("http://www.w3.org/2002/07/owl#propertyChainAxiom")

_universal_abbrev("http://www.w3.org/2002/07/owl#TransitiveProperty")
_universal_abbrev("http://www.w3.org/2002/07/owl#SymmetricProperty")
_universal_abbrev("http://www.w3.org/2002/07/owl#AsymmetricProperty")
_universal_abbrev("http://www.w3.org/2002/07/owl#ReflexiveProperty")
_universal_abbrev("http://www.w3.org/2002/07/owl#IrreflexiveProperty")
_universal_abbrev("http://www.w3.org/2002/07/owl#backwardCompatibleWith")
_universal_abbrev("http://www.w3.org/2002/07/owl#deprecated")
_universal_abbrev("http://www.w3.org/2002/07/owl#incompatibleWith")
_universal_abbrev("http://www.w3.org/2000/01/rdf-schema#isDefinedBy")
_universal_abbrev("http://www.w3.org/2002/07/owl#priorVersion")
_universal_abbrev("http://www.w3.org/2000/01/rdf-schema#seeAlso")
_universal_abbrev("http://www.w3.org/2002/07/owl#versionInfo")


HAS_SELF                  = _universal_abbrev("http://www.w3.org/2002/07/owl#hasSelf")

issubclass_python = issubclass



