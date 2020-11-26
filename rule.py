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

import owlready2
from owlready2.base       import *
from owlready2.namespace  import *
from owlready2.individual import *
from owlready2.prop       import *

swrl = owl_world.get_ontology("http://www.w3.org/2003/11/swrl#")

class Variable(Thing):
  namespace = swrl
  
  def __str__(self): return repr(self)
  def __repr__(self): return "?%s" % self.name
  
  def __init__(self, name = None, namespace = None, **kargs):
    if LOADING:
      super().__init__(name, namespace, **kargs)
    else:
      with LOADING: # Avoid declaring variables as individuals
        super().__init__(name, namespace, **kargs)
        
      for parent in self.is_a:
        self.namespace.ontology._add_obj_triple_spo(self.storid, rdf_type, parent.storid)
        

class body(ObjectProperty):
  namespace = swrl
    
class head(ObjectProperty):
  namespace = swrl

class classPredicate(ObjectProperty, FunctionalProperty):
  namespace = swrl
classPredicate.python_name = "class_predicate"
  
class propertyPredicate(ObjectProperty, FunctionalProperty):
  namespace = swrl
propertyPredicate.python_name = "property_predicate"

#class argument1(ObjectProperty, FunctionalProperty):
#  namespace = swrl

#class argument2(ObjectProperty, FunctionalProperty):
#  namespace = swrl

class arguments(ObjectProperty):
  namespace = swrl

class builtin(ObjectProperty, FunctionalProperty):
  namespace = swrl

_DATARANGES = { int : "int", float : "decimal", str : "string", normstr : "normalizedString" }
_NAME_2_DATARANGE = { v : k for k, v in _DATARANGES.items() }
  
class Imp(Thing):
  namespace = swrl
  
  def __str__(self): return repr(self)
  def __repr__(self):
    return "%s -> %s" % (", ".join(_repr_swrl(i) for i in self.body), ", ".join(_repr_swrl(i) for i in self.head))
  
  def __init__(self, name = 0, namespace = None, **kargs): # Use a blanck node by default
    super().__init__(name, namespace, **kargs)
    
  def __getattr__(self, attr):
    if   attr == "body":
      bn = self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_body)
      if bn is None:
        bn = self.namespace.world.new_blank_node()
        self.namespace.ontology._add_obj_triple_spo(self.storid, swrl_body, bn)
        self.namespace.ontology._set_list(bn, [])
      l = OrderedValueList(bn, self, body)
      object.__setattr__(self, attr, l)
      return l
    elif attr == "head":
      bn = self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_head)
      if bn is None:
        bn = self.namespace.world.new_blank_node()
        self.namespace.ontology._add_obj_triple_spo(self.storid, swrl_head, bn)
        self.namespace.ontology._set_list(bn, [])
      l = OrderedValueList(bn, self, head)
      object.__setattr__(self, attr, l)
      return l
    return super().__getattr__(attr)
  
  # Not needed: super implementation is ok!
  #def __setattr__(self, attr, value):
  #  if   attr == "body": self.body.reinit(value)
  #  elif attr == "head": self.head.reinit(value)
  #  else: return super().__setattr__(attr, value)
  
  def get_variable(self, name, create = True):
    namespace = self.namespace.ontology.get_namespace("urn:swrl#")
    variable = namespace[name[1:]]
    if (variable is None) and create:
      variable = Variable(name[1:], namespace = namespace)
    return variable
  
  def set_as_rule(self, rule, namespaces = None):
    if namespaces is None: namespaces = [self.namespace]
    if not _RULE_PARSER: _create_rule_parser()
    r = _RULE_PARSER[1].parse(_RULE_PARSER[0].lex(rule))
    
    ls = []
    with self.namespace:
      for atoms in r:
        l = []
        for atom in atoms:
          atom, args = atom
          atom = atom.value
          if atom in _BUILTINS:           atom = BuiltinAtom(builtin = atom)
          elif atom.casefold() == "SameAs".casefold():          atom = SameIndividualAtom()
          elif atom.casefold() == "DifferentFrom".casefold():   atom = DifferentIndividualsAtom()
          elif atom in _NAME_2_DATARANGE: atom = DataRangeAtom(datarange = _NAME_2_DATARANGE[atom])
          else:
            entity = _find_entity(atom, namespaces)
            if   isinstance(entity, ThingClass):          atom = ClassAtom             (class_predicate    = entity)
            elif isinstance(entity, ObjectPropertyClass): atom = IndividualPropertyAtom(property_predicate = entity)
            elif isinstance(entity, DataPropertyClass):   atom = DatavaluedPropertyAtom(property_predicate = entity)
            
          arguments = []
          for arg in args:
            if   arg.name == "VAR":   arguments.append(self.get_variable(arg.value))
            elif arg.name == "NAME":  arguments.append(_find_entity(arg.value, namespaces))
            else:                     arguments.append(arg.value)
            
          atom.arguments = arguments
          l.append(atom)
        ls.append(l)
        
      self.body, self.head = ls
    return self

  def __destroy__(self, objs, datas):
    vars = set()
    for atom in self.head + self.body:
      for arg in atom.arguments:
        if isinstance(arg, Variable): vars.add(arg)
      atom.__destroy__()
    for bn in (self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_body), self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_head)):
      if not bn is None:
        self.namespace.ontology._del_list(bn)
    for var in vars:
      if not self.namespace.world._has_obj_triple_spo(o = var.storid):
        destroy_entity(var)
        
def _find_entity(name, namespaces):
  if ":" in name:
    entity = namespaces[0].world[name]
    if not entity is None: return entity
  for namespace in namespaces:
    entity = namespace[name]
    if not entity is None: return entity
  raise ValueError("Cannot find entity '%s'!" % name)
  
  
    
class _FixedArguments(object):
  def __init__(self, name = 0, namespace = None, **kargs): # Use a blanck node by default
    super().__init__(name, namespace, **kargs)
    
  def __str__(self): return repr(self)
  
  def __getattr__(self, attr):
    if   attr == "arguments":
      bn = self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_arguments)
      l = ArgumentValueList(self)
      object.__setattr__(self, attr, l)
      return l
    return super().__getattr__(attr)  
  
  def __destroy__(self):
    bn = self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_arguments)
    if not bn is None:
      self.namespace.ontology._del_obj_triple_spo(bn, None, None)
      self.namespace.ontology._del_data_triple_spod(bn, None, None, None)
    self.namespace.ontology._del_obj_triple_spo(self.storid, None, None)
    self.namespace.ontology._del_data_triple_spod(self.storid, None, None, None)
    
    
class ClassAtom(_FixedArguments, Thing):
  namespace = swrl
  
  def __repr__(self):
    return "%s(%s)" % (self.class_predicate.name, ", ".join(_repr_swrl(i) for i in self.arguments))
    
  
class DataRangeAtom(_FixedArguments, Thing):
  namespace = swrl
  
  def __repr__(self):
    datarange = _DATARANGES[self.datarange]
    return "%s(%s)" % (datarange, ", ".join(_repr_swrl(i) for i in self.arguments))
  
  def __getattr__(self, attr):
    if attr == "datarange":
      datarange = self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_datarange)
      if datarange in owlready2.base._universal_abbrev_2_datatype:
        datarange = owlready2.base._universal_abbrev_2_datatype[datarange]
      else:
        datarange = self.namespace.world._get_by_storid(datarange)
      object.__setattr__(self, attr, datarange)
      return datarange
    return super().__getattr__(attr)
  
  def __setattr__(self, attr, value):
    if attr == "datarange":
      object.__setattr__(self, attr, value)
      value = owlready2.base._universal_datatype_2_abbrev.get(value) or value
      if hasattr(value, "storid"): value = value.storid
      self.namespace.ontology._set_obj_triple_spo(self.storid, swrl_datarange, value)
    else: super().__setattr__(attr, value)
    
class SameIndividualAtom(_FixedArguments, Thing):
  namespace = swrl
  
  def __repr__(self):
    return "SameAs(%s)" % (", ".join(_repr_swrl(i) for i in self.arguments))

class DifferentIndividualsAtom(_FixedArguments, Thing):
  namespace = swrl
  
  def __repr__(self):
    return "DifferentFrom(%s)" % (", ".join(_repr_swrl(i) for i in self.arguments))
  
class DatavaluedPropertyAtom(_FixedArguments, Thing):
  namespace = swrl
  
  def __init__(self, name = 0, namespace = None, **kargs): # Use a blanck node by default
    super().__init__(name, namespace, **kargs)
    
  def __repr__(self):
    return "%s(%s)" % (self.property_predicate.name, ", ".join(_repr_swrl(i) for i in self.arguments))
  
class IndividualPropertyAtom(_FixedArguments, Thing):
  namespace = swrl
  
  def __init__(self, name = 0, namespace = None, **kargs): # Use a blanck node by default
    super().__init__(name, namespace, **kargs)
    
  def __repr__(self):
    return "%s(%s)" % (self.property_predicate.name, ", ".join(_repr_swrl(i) for i in self.arguments))


_BUILTINS = { "equal", "notEqual", "lessThan", "lessThanOrEqual", "greaterThan", "greaterThanOrEqual",
              "add", "subtract", "multiply", "divide", "integerDivide", "mod", "pow", "unaryPlus", "unaryMinus",
              "abs", "ceiling", "floor", "round", "roundHalfToEven", "sin", "cos", "tan",
              "booleanNot", "stringEqualIgnoreCase", "stringConcat", "substring", "stringLength",
              "normalizeSpace", "upperCase", "lowerCase", "translate", "contains", "containsIgnoreCase",
              "startsWith", "endsWith", "substringBefore", "substringAfter", "matches", "replace", "tokenize",
              "yearMonthDuration", "dayTimeDuration", "dateTime", "date", "time", "addYearMonthDurations",
              "subtractYearMonthDurations", "multiplyYearMonthDuration", "divideYearMonthDurations",
              "addDayTimeDurations", "subtractDayTimeDurations", "multiplyDayTimeDurations",
              "divideDayTimeDuration", "subtractDates", "subtractTimes", "addYearMonthDurationToDateTime",
              "addDayTimeDurationToDateTime", "subtractYearMonthDurationFromDateTime",
              "subtractDayTimeDurationFromDateTime", "addYearMonthDurationToDate", "addDayTimeDurationToDate",
              "subtractYearMonthDurationFromDate", "subtractDayTimeDurationFromDate", "addDayTimeDurationToTime",
              "subtractDayTimeDurationFromTime", "subtractDateTimesYieldingYearMonthDuration",
              "subtractDateTimesYieldingDayTimeDuration", "resolveURI", "anyURI",
              "listConcat", "listIntersection", "listSubtraction", "member", "length", "first", "rest", "sublist",
              "empty",
}

class BuiltinAtom(Thing):
  namespace = swrl
  
  def __init__(self, name = 0, namespace = None, **kargs): # Use a blanck node by default
    super().__init__(name, namespace, **kargs)
    
  def __str__(self): return repr(self)
  def __repr__(self):
    b = self.builtin
    if isinstance(b, str): b = b[b.rfind("#") + 1:]
    else:                  b = b.name
    return "%s(%s)" % (b, ", ".join(_repr_swrl(i) for i in self.arguments))
  
  def __getattr__(self, attr):
    if   attr == "arguments":
      bn = self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_arguments)
      if bn is None:
        bn = self.namespace.world.new_blank_node()
        self.namespace.ontology._add_obj_triple_spo(self.storid, swrl_arguments, bn)
        self.namespace.ontology._set_list(bn, [])
      l = OrderedValueList(bn, self, arguments)
      object.__setattr__(self, attr, l)
      return l
    elif attr == "builtin":
      builtin = self.namespace.world._unabbreviate(self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_builtin))
      builtin = builtin[builtin.rfind("#") + 1:]
      object.__setattr__(self, attr, builtin)
      return builtin
    return super().__getattr__(attr)
  
  def __setattr__(self, attr, value):
    if attr == "builtin":
      object.__setattr__(self, attr, value)
      self.namespace.ontology._set_obj_triple_spo(self.storid, swrl_builtin, self.namespace.world._abbreviate("http://www.w3.org/2003/11/swrlb#%s" % value))
    else: super().__setattr__(attr, value)
    
  def __destroy__(self):
    bn = self.namespace.world._get_obj_triple_sp_o(self.storid, swrl_arguments)
    if not bn is None: self.namespace.ontology._del_list(bn)
    self.namespace.ontology._del_obj_triple_spo(self.storid, None, None)
    self.namespace.ontology._del_data_triple_spod(self.storid, None, None, None)
    
    

class OrderedValueList(CallbackList):
  __slots__ = ["_Prop", "_bn"]
  def __init__(self, bn, obj, Prop):
    list.__init__(self, obj.namespace.world._parse_list(bn))
    self._bn   = bn
    self._obj  = obj
    self._Prop = Prop
    
  def _callback(self, obj, old):
    self._obj.namespace.ontology._del_list(self._bn)
    self._obj.namespace.ontology._set_list(self._bn, self)

class ArgumentValueList(CallbackList):
  __slots__ = []
  def __init__(self, obj):
    l = []
    for swrl_argument in [swrl_argument1, swrl_argument2]:
      o = obj.namespace.world._get_obj_triple_sp_o(obj.storid, swrl_argument)
      if o is None:
        r = obj.namespace.world._get_data_triple_sp_od(obj.storid, swrl_argument)
        if r is None: break
        o = obj.namespace.world._to_python(*r)
      else:
        o = obj.namespace.world._to_python(o)
      l.append(o)
    list.__init__(self, l)
    self._obj  = obj
    
  def _callback(self, obj, old):
    for i, swrl_argument in enumerate([swrl_argument1, swrl_argument2]):
      if (i <  len(self)) and (i <  len(old)) and (self[i] is old[i]): continue
      if (i >= len(self)) and (i >= len(old)): continue
      if (i >= len(self)):
        if hasattr(old[i], "storid"):
          self._obj.namespace.ontology._del_obj_triple_spo(self._obj.storid, swrl_argument, None)
        else:
          self._obj.namespace.ontology._del_data_triple_spod(self._obj.storid, swrl_argument, None)
      else:
        if hasattr(self[i], "storid"):
          self._obj.namespace.ontology._set_obj_triple_spo(self._obj.storid, swrl_argument, self[i].storid)
        else:
          self._obj.namespace.ontology._set_data_triple_spod(self._obj.storid, swrl_argument, *self._obj.namespace.world._to_rdf(self[i]))
          

def _repr_swrl(x):
  if isinstance(x, bool):
    if x: return "true"
    return "false"
  return repr(x)

          
_RULE_PARSER = None
def _create_rule_parser():
  global _RULE_PARSER
  import owlready2.rply as rply
  
  lg = rply.LexerGenerator()
  lg.add("(", r"\(")
  lg.add(")", r"\)")
  lg.add(",", r",")
  lg.add("IMP", r"->")
  lg.add("FLOAT", r"-[0-9]*\.[0-9]+")
  lg.add("FLOAT", r"[0-9]*\.[0-9]+")
  lg.add("INT", r"-[0-9]+")
  lg.add("INT", r"[0-9]+")
  lg.add("STR", r'".*?"')
  lg.add("STR", r"'.*?'")
  lg.add("BOOL", r"true")
  lg.add("BOOL", r"false")
  lg.add("VAR", r"\?[a-zA-Z0-9_]+")
  lg.add("NAME", r'[a-zA-Z][a-zA-Z0-9_:/.#]*')
  
  lg.ignore(r"\s+")
  
  lexer = lg.build()
  pg = rply.ParserGenerator([rule.name for rule in lg.rules])
  
  @pg.production("main : atoms IMP atoms")
  def f(p): return p[0], p[2]
  
  @pg.production("atoms : ")
  def f(p): return []
  @pg.production("atoms : atom")
  def f(p): return p
  @pg.production("atoms : atom , atoms")
  def f(p): return [p[0]] + p[-1]
  
  @pg.production("atom : NAME ( args )")
  def f(p): return p[0], p[-2]
  
  @pg.production("args : ")
  def f(p): return []
  @pg.production("args : arg")
  def f(p): return p
  @pg.production("args : arg , args")
  def f(p): return [p[0]] + p[-1]

  @pg.production("arg : INT")
  def f(p): p[0].value = int(p[0].value); return p[0]
  @pg.production("arg : FLOAT")
  def f(p): p[0].value = float(p[0].value); return p[0]
  @pg.production("arg : BOOL")
  def f(p): p[0].value = p[0].value == "true"; return p[0]
  @pg.production("arg : VAR")
  @pg.production("arg : NAME")
  def f(p): return p[0]
  @pg.production("arg : STR")
  def f(p):
    p[0].value = p[0].value[1:-1]
    return p[0]
  
  parser = pg.build()
  
  _RULE_PARSER = lexer, parser
