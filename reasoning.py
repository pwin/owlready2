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

import re, tempfile

import owlready2
from owlready2.base            import *
from owlready2.prop            import *
from owlready2.namespace       import *
from owlready2.class_construct import *
from owlready2.individual      import *

_HERMIT_RESULT_REGEXP = re.compile("^([A-Za-z]+)\\( ((?:<(?:[^>]+)>\s*)+) \\)$", re.MULTILINE)
_HERMIT_PROP_REGEXP   = re.compile("^<([^>]+)> \\(known instances:\s*(.*?)(?:\s*\\|\s*)possible instances:\s*(.*?)\s*\\)", re.MULTILINE)

_PELLET_PROP_REGEXP      = re.compile("^PROPINST: ([^ ]+) ([^ ]+) ([^ ]+)$", re.MULTILINE)
_PELLET_DATA_PROP_REGEXP = re.compile("^DATAPROPVAL: ([^ ]+) ([^ ]+) literal\((.*?),(.*?),(.*?)\)$", re.MULTILINE)


_HERE = os.path.dirname(__file__)
_HERMIT_CLASSPATH = os.pathsep.join([os.path.join(_HERE, "hermit"), os.path.join(_HERE, "hermit", "HermiT.jar")])

_PELLET_CLASSPATH = os.pathsep.join(
  os.path.join(_HERE, "pellet", p) for p in os.listdir(os.path.join(_HERE, "pellet")) if p.endswith(".jar"))


_HERMIT_2_OWL = {
  "SubClassOf"                 : rdfs_subclassof,
  "SubPropertyOf"              : rdfs_subpropertyof,
  "SubObjectPropertyOf"        : rdfs_subpropertyof,
  "SubDataPropertyOf"          : rdfs_subpropertyof,
  "Type"                       : rdf_type,
  "EquivalentClasses"          : owl_equivalentclass,
  "EquivalentObjectProperties" : owl_equivalentproperty,
  "EquivalentDataProperties"   : owl_equivalentproperty,
}

_OWL_2_TYPE = {
  rdfs_subclassof          : "class",
  rdfs_subpropertyof       : "property",
  rdf_type                 : "individual",
  owl_equivalentclass      : "class",
  owl_equivalentproperty   : "property",
  owl_equivalentindividual : "individual",
}
_TYPE_2_IS_A = {
  "class"                 : rdfs_subclassof,
  "property"              : rdfs_subpropertyof,
  "individual"            : rdf_type,
}
_TYPE_2_EQUIVALENT_TO = {
  "class"                 : owl_equivalentclass,
  "property"              : owl_equivalentproperty,
  "individual"            : owl_equivalentindividual,
}

_INFERRENCES_ONTOLOGY = "http://inferrences/"

_IS_A_RELATIONS  = {"SubClassOf", "SubObjectPropertyOf", "SubDataPropertyOf", "Type"}
_EQUIV_RELATIONS = {"EquivalentClasses", "EquivalentObjectProperties", "EquivalentDataProperties"}

_TYPES = { FunctionalProperty, InverseFunctionalProperty, TransitiveProperty, SymmetricProperty, AsymmetricProperty, ReflexiveProperty, IrreflexiveProperty }


def _keep_most_specific(s, consider_equivalence = True):
  if consider_equivalence:
    testsubclass = issubclass
  else:
    testsubclass = issubclass_python
  r = set()
  for i in s:
    if isinstance(i, ClassConstruct):
      r.add(i)
    else:
      for j in s:
        if (i is j) or isinstance(j, ClassConstruct): continue
        if testsubclass(j, i): break
      else:
        r.add(i)
  return r


def sync_reasoner_hermit(x = None, infer_property_values = False, debug = 1, keep_tmp_file = False):
  if   isinstance(x, World):    world = x
  elif isinstance(x, Ontology): world = x.world
  elif isinstance(x, list):     world = x[0].world
  else:                         world = owlready2.default_world
  
  locked = world.graph.has_write_lock()
  if locked: world.graph.release_write_lock() # Not needed during reasoning
  
  try:
    if   isinstance(x, Ontology):  ontology = x
    elif CURRENT_NAMESPACES.get(): ontology = CURRENT_NAMESPACES.get()[-1].ontology
    else:                          ontology = world.get_ontology(_INFERRENCES_ONTOLOGY)
    
    tmp = tempfile.NamedTemporaryFile("wb", delete = False)
    if isinstance(x, list):
      for o in x: o.save(tmp, format = "ntriples", commit = False)
    else:
      world.save(tmp, format = "ntriples")
    tmp.close()
    command = [owlready2.JAVA_EXE, "-Xmx2000M", "-cp", _HERMIT_CLASSPATH, "org.semanticweb.HermiT.cli.CommandLine", "-c", "-O", "-D", "-I", "file:///%s" % tmp.name.replace('\\','/')]
    if infer_property_values: command.append("-Y")
    if debug:
      import time
      print("* Owlready2 * Running HermiT...", file = sys.stderr)
      print("    %s" % " ".join(command), file = sys.stderr)
      t0 = time.time()
      
    try:
      output = subprocess.check_output(command, stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      if (e.returncode == 1) and (b"Inconsistent ontology" in e.output):
        raise OwlReadyInconsistentOntologyError()
      else:
        raise OwlReadyJavaError("Java error message is:\n%s" % e.stderr.decode("utf8"))
    
    output = output.decode("utf8").replace("\r","")
    if debug:
      print("* Owlready2 * HermiT took %s seconds" % (time.time() - t0), file = sys.stderr)
      if debug > 1:
        print("* Owlready2 * HermiT output:", file = sys.stderr)
        print(output, file = sys.stderr)
        
        
    new_parents = defaultdict(list)
    new_equivs  = defaultdict(list)
    entity_2_type = {}
    for relation, concept_iris in _HERMIT_RESULT_REGEXP.findall(output):
      concept_storids = [ontology._abbreviate(x) for x in concept_iris[1:-1].split("> <")]
      owl_relation = _HERMIT_2_OWL[relation]
    
      if  relation in _IS_A_RELATIONS:
        if concept_iris[0].startswith("http://www.w3.org/2002/07/owl"): continue
        
        new_parents[concept_storids[0]].append(concept_storids[1])
        entity_2_type[concept_storids[0]] = _OWL_2_TYPE[owl_relation]
      
      elif relation in _EQUIV_RELATIONS:
        if "http://www.w3.org/2002/07/owl#Nothing" in concept_iris:
          for concept_iri, concept_storid in zip(concept_iris, concept_storids):
            if concept_iri.startswith("http://www.w3.org/2002/07/owl"): continue
            if concept_storid == owl_nothing: continue
            
            new_equivs[concept_storid].append(owl_nothing)
            entity_2_type[concept_storid] = _OWL_2_TYPE[owl_relation]
          
        else:
          for concept_iri1, concept_storid1 in zip(concept_iris, concept_storids):
            if concept_iri1.startswith("http://www.w3.org/2002/07/owl"): continue
            for concept_iri2, concept_storid2 in zip(concept_iris, concept_storids):
              if concept_iri1 == concept_iri2: continue
              new_equivs[concept_storid1].append(concept_storid2)
              entity_2_type[concept_storid1] = _OWL_2_TYPE[owl_relation]
            
    if infer_property_values:
      inferred_obj_relations = []
      for prop_iri, knowns, possibles in _HERMIT_PROP_REGEXP.findall(output):
        prop = world[prop_iri]
        if prop is None: continue
        knowns = knowns[1:-1] # Remove first and last parenthesese
        if not knowns.strip(): continue
        for pair in knowns.split(")("):
          a, b = pair[1:-1].split(">, <", 1)
          a_storid = ontology._abbreviate(a, False)
          b_storid = ontology._abbreviate(b, False)
          if ((not a_storid is None) and (not b_storid is None) and
              (not world._has_obj_triple_spo(a_storid, prop.storid, b_storid)) and
             ((not prop._inverse_property) or (not world._has_obj_triple_spo(b_storid, prop._inverse_storid, a_storid)))):
            inferred_obj_relations.append((a_storid, prop, b_storid))
          
    if not keep_tmp_file: os.unlink(tmp.name)
    
  finally:
    if locked: world.graph.acquire_write_lock() # re-lock when applying results
    
  _apply_reasoning_results(world, ontology, debug, new_parents, new_equivs, entity_2_type)
  if infer_property_values:
    _apply_inferred_obj_relations(world, ontology, debug, inferred_obj_relations)
  
  if debug: print("* Owlready * (NB: only changes on entities loaded in Python are shown, other changes are done but not listed)", file = sys.stderr)

sync_reasoner = sync_reasoner_hermit


def sync_reasoner_pellet(x = None, infer_property_values = False, infer_data_property_values = False, debug = 1, keep_tmp_file = False):
  if   isinstance(x, World):    world = x
  elif isinstance(x, Ontology): world = x.world
  elif isinstance(x, list):     world = x[0].world
  else:                         world = owlready2.default_world
  
  locked = world.graph.has_write_lock()
  if locked: world.graph.release_write_lock() # Not needed during reasoning
  
  try:
    if   isinstance(x, Ontology):  ontology = x
    elif CURRENT_NAMESPACES.get(): ontology = CURRENT_NAMESPACES.get()[-1].ontology
    else:                          ontology = world.get_ontology(_INFERRENCES_ONTOLOGY)
    
    tmp = tempfile.NamedTemporaryFile("wb", delete = False)
    if isinstance(x, list):
      for o in x: o.save(tmp, format = "ntriples", commit = False)
    else:
      world.save(tmp, format = "ntriples")
    tmp.close()
    command = [owlready2.JAVA_EXE, "-Xmx2000M", "-cp", _PELLET_CLASSPATH, "pellet.Pellet", "realize", "--ignore-imports", tmp.name]
    if infer_property_values:      command.insert(-2, "--infer-prop-values")
    if infer_data_property_values: command.insert(-2, "--infer-data-prop-values")
  
    if debug:
      import time
      print("* Owlready2 * Running Pellet...", file = sys.stderr)
      print("    %s" % " ".join(command), file = sys.stderr)
      t0 = time.time()
    
    try:
      output = subprocess.run(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, check = True).stdout
    except subprocess.CalledProcessError as e:
      if (e.returncode == 1) and (b"ERROR: Ontology is inconsistent" in e.stderr): # XXX
        raise OwlReadyInconsistentOntologyError()
      else:
        raise OwlReadyJavaError("Java error message is:\n%s" % e.stderr.decode("utf8"))
      
    output = output.decode("utf8").replace("\r","")
    if debug:
      print("* Owlready2 * Pellet took %s seconds" % (time.time() - t0), file = sys.stderr)
      if debug > 1:
        print("* Owlready2 * Pellet output:", file = sys.stderr)
        print(output, file = sys.stderr)
      
      
    new_parents = defaultdict(list)
    new_equivs  = defaultdict(list)
    entity_2_type = {}
    stack = []
    for line in output.split("\n"):
      if not line: continue
      line2 = line.lstrip()
      depth = len(line) - len(line2)
      splitted = line2.split(" - ", 1)
      class_storids = [ontology._abbreviate(class_iri) for class_iri in splitted[0].split(" = ")]
      
      if len(class_storids) > 1:
        for class_storid1 in class_storids:
          for class_storid2 in class_storids:
            if not class_storid1 is class_storid2:
              new_equivs[class_storid1].append(class_storid2)
            
      while stack and (stack[-1][0] >= depth): del stack[-1]
      if len(stack) > 1: # if len(stack) == 1, it only contains Thing => not interesting
        for class_storid in class_storids:
          entity_2_type[class_storid] = "class"
          new_parents[class_storid].extend(stack[-1][1])
      else:
        for class_storid in class_storids:
          entity_2_type[class_storid] = "class"
      stack.append((depth, class_storids))
    
      if len(splitted) == 2:
        ind_iris = splitted[1][1:-1].split(", ")
        for ind_iri in ind_iris:
          ind_storid = ontology._abbreviate(ind_iri)
          entity_2_type[ind_storid] = "individual"
          new_parents[ind_storid].extend(class_storids)
        
    if infer_property_values:
      inferred_obj_relations = []
      for a_iri, prop_iri, b_iri in _PELLET_PROP_REGEXP.findall(output):
        prop = world[prop_iri]
        if prop is None: continue
        a_storid = ontology._abbreviate(a_iri, False)
        b_storid = ontology._abbreviate(b_iri.strip(), False)
        if ((not a_storid is None) and (not b_storid is None) and
            (not world._has_obj_triple_spo(a_storid, prop.storid, b_storid)) and
           ((not prop._inverse_property) or (not world._has_obj_triple_spo(b_storid, prop._inverse_storid, a_storid)))):
          inferred_obj_relations.append((a_storid, prop, b_storid))
        
    if infer_data_property_values:
      inferred_data_relations = []
      for a_iri, prop_iri, value, lang, datatype in _PELLET_DATA_PROP_REGEXP.findall(output):
        prop = world[prop_iri]
        if prop is None: continue
        a_storid = ontology._abbreviate(a_iri, False)
        if lang and (lang != "()"):
          datatype = "@%s" % lang
        else:
          datatype = ontology._abbreviate(datatype)
          python_datatype = owlready2.base._universal_abbrev_2_datatype.get(datatype)
          if   python_datatype is int:   value = int  (value)
          elif python_datatype is float: value = float(value)
        if ((not a_storid is None) and
            (not world._has_data_triple_spod(a_storid, prop.storid, value))):
          inferred_data_relations.append((a_storid, prop, value, datatype))
        
      
    if not keep_tmp_file: os.unlink(tmp.name)

  finally:
    if locked: world.graph.acquire_write_lock() # re-lock when applying results
    
  _apply_reasoning_results(world, ontology, debug, new_parents, new_equivs, entity_2_type)
  if infer_property_values:      _apply_inferred_obj_relations (world, ontology, debug, inferred_obj_relations)
  if infer_data_property_values: _apply_inferred_data_relations(world, ontology, debug, inferred_data_relations)
  
  if debug: print("* Owlready * (NB: only changes on entities loaded in Python are shown, other changes are done but not listed)", file = sys.stderr)



def _apply_reasoning_results(world, ontology, debug, new_parents, new_equivs, entity_2_type):
  new_parents_loaded = defaultdict(list)
  new_equivs_loaded  = defaultdict(list)

  for child_storid, parent_storids in new_parents.items():
    for parent_storid in parent_storids:
      owl_relation = _TYPE_2_IS_A[entity_2_type[child_storid]]
      if not ontology.world._has_obj_triple_spo(child_storid, owl_relation, parent_storid):
        ontology._add_obj_triple_spo(child_storid, owl_relation, parent_storid)
        
    child = world._entities.get(child_storid)
    if not child is None:
      l = new_parents_loaded[child] = []
      for parent_storid in parent_storids:
        parent = world._get_by_storid(parent_storid)
        if parent is None:
          print("* Owlready2 * Warning: Cannot find new parent '%s'" % parent_storid, file = sys.stderr)
        else:
          l.append(parent)
          
  for concept1_storid, concept2_storids in new_equivs.items():
    for concept2_storid in concept2_storids:
      owl_relation = _TYPE_2_EQUIVALENT_TO[entity_2_type[concept1_storid]]
      if not ontology.world._has_obj_triple_spo(concept1_storid, owl_relation, concept2_storid):
        ontology._add_obj_triple_spo(concept1_storid, owl_relation, concept2_storid)
        
      if concept2_storid == owl_nothing:
        concept1 = world._entities.get(concept1_storid)
        if not concept1 is None: new_equivs_loaded[concept1].append(Nothing)
      else:
        concept1 = world._entities.get(concept1_storid)
        concept2 = world._entities.get(concept2_storid)
        if concept1 or concept2:
          concept1 = concept1 or world._get_by_storid(concept1_storid)
          concept2 = concept2 or world._get_by_storid(concept2_storid)
          if not concept1 is concept2: new_equivs_loaded[concept1].append(concept2)
        
  
  with LOADING: # Because triples were asserted above => only modify Python objects WITHOUT creating new triples!
    for concept1, concepts2 in new_equivs_loaded.items():
      for concept2 in concepts2:
        if debug: print("* Owlready * Equivalenting:", concept1, concept2, file = sys.stderr)
        concept1.equivalent_to._append(concept2)
        
    for child, parents in new_parents_loaded.items():
      old = set(parent for parent in child.is_a if not isinstance(parent, ClassConstruct))
      new = set(parents)
      
      #new.update([parent_eq for parent in new for parent_eq in parent.equivalent_to.indirect() if not isinstance(parent, ClassConstruct)])
      
      new.update(old & _TYPES) # Types are not shown by HermiT
      if old == new: continue
      new = _keep_most_specific(new, consider_equivalence = False)
      if old == new: continue
      
      if debug: print("* Owlready * Reparenting %s:" % child, old, "=>", new, file = sys.stderr)
      new_is_a = list(child.is_a)
      for removed in old - new: new_is_a.remove(removed)
      for added   in new - old: new_is_a.append(added)
      
      child.is_a.reinit(new_is_a)
            
      for child_eq in child.equivalent_to.indirect():
        if isinstance(child_eq, ThingClass):
          if debug: print("* Owlready * Reparenting %s (since equivalent):" % child_eq, old, "=>", new, file = sys.stderr)
          new_is_a = list(child_eq.is_a)
          for removed in old - new:
            if removed in new_is_a: new_is_a.remove(removed)
          for added   in new - old:
            if not added in new_is_a: new_is_a.append(added)
          child_eq.is_a.reinit(new_is_a)

          
def _apply_inferred_obj_relations(world, ontology, debug, relations):
  for a_storid, prop, b_storid in relations:
    ontology._add_obj_triple_spo(a_storid, prop.storid, b_storid)
    
    a = world._entities.get(a_storid)
    if not a is None:
      if debug:
        b = world._entities.get(b_storid)
        if not b is None: print("* Owlready * Adding relation %s %s %s" % (a, prop.name, b))
      if prop._python_name in a.__dict__:
        delattr(a, prop._python_name)
        
    if prop._inverse_property:
      b = world._entities.get(b_storid)
      if not b is None:
        if prop._inverse_property._python_name in b.__dict__:
          delattr(b, prop._inverse_property._python_name)
          
          
def _apply_inferred_data_relations(world, ontology, debug, relations):
  for a_storid, prop, value, datatype in relations:
    ontology._add_data_triple_spod(a_storid, prop.storid, value, datatype)
    
    a = world._entities.get(a_storid)
    if not a is None:
      if debug:
        b = world._entities.get(b_storid)
        if not b is None: print("* Owlready * Adding relation %s %s %s" % (a, prop.name, value))
      if prop._python_name in a.__dict__:
        delattr(a, prop._python_name)
        
