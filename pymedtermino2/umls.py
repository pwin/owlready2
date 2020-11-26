# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2019 Jean-Baptiste LAMY
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


import sys, os, types, zipfile, gzip, io
from collections import defaultdict, Counter
from owlready2 import *

iso_3_letter_2_2_letter_lang = {'ABK': 'ab', 'AAR': 'aa', 'AFR': 'af', 'ALB': 'sq', 'SQI': 'sq', 'AMH': 'am', 'ARA': 'ar', 'ARG': 'an', 'ARM': 'hy', 'HYE': 'hy', 'ASM': 'as', 'AVE': 'ae', 'AYM': 'ay', 'AZE': 'az', 'BAK': 'ba', 'BAQ': 'eu', 'EUS': 'eu', 'BEL': 'be', 'BEN': 'bn', 'BIH': 'bh', 'BIS': 'bi', 'BOS': 'bs', 'BRE': 'br', 'BUL': 'bg', 'BUR': 'my', 'MYA': 'my', 'CAT': 'ca', 'CHA': 'ch', 'CHE': 'ce', 'CHI': 'zh', 'ZHO': 'zh', 'CHU': 'cu', 'CHV': 'cv', 'COR': 'kw', 'COS': 'co', 'SCR': 'hr', 'HRV': 'hr', 'CZE': 'cs', 'CES': 'cs', 'DAN': 'da', 'DIV': 'dv', 'DUT': 'nl', 'NLD': 'nl', 'DZO': 'dz', 'ENG': 'en', 'EPO': 'eo', 'EST': 'et', 'FAO': 'fo', 'FIJ': 'fj', 'FIN': 'fi', 'FRE': 'fr', 'FRA': 'fr', 'GLA': 'gd', 'GLG': 'gl', 'GEO': 'ka', 'KAT': 'ka', 'GER': 'de', 'DEU': 'de', 'GRE': 'el', 'ELL': 'el', 'GRN': 'gn', 'GUJ': 'gu', 'HAT': 'ht', 'HAU': 'ha', 'HEB': 'he', 'HER': 'hz', 'HIN': 'hi', 'HMO': 'ho', 'HUN': 'hu', 'ICE': 'is', 'ISL': 'is', 'IDO': 'io', 'IND': 'id', 'INA': 'ia', 'ILE': 'ie', 'IKU': 'iu', 'IPK': 'ik', 'GLE': 'ga', 'ITA': 'it', 'JPN': 'ja', 'JAV': 'jv', 'KAL': 'kl', 'KAN': 'kn', 'KAS': 'ks', 'KAZ': 'kk', 'KHM': 'km', 'KIK': 'ki', 'KIN': 'rw', 'KIR': 'ky', 'KOM': 'kv', 'KOR': 'ko', 'KUA': 'kj', 'KUR': 'ku', 'LAO': 'lo', 'LAT': 'la', 'LAV': 'lv', 'LIM': 'li', 'LIN': 'ln', 'LIT': 'lt', 'LTZ': 'lb', 'MAC': 'mk', 'MKD': 'mk', 'MLG': 'mg', 'MAY': 'ms', 'MSA': 'ms', 'MAL': 'ml', 'MLT': 'mt', 'GLV': 'gv', 'MAO': 'mi', 'MRI': 'mi', 'MAR': 'mr', 'MAH': 'mh', 'MOL': 'mo', 'MON': 'mn', 'NAU': 'na', 'NAV': 'nv', 'NDE': 'nd', 'NBL': 'nr', 'NDO': 'ng', 'NEP': 'ne', 'SME': 'se', 'NOR': 'no', 'NOB': 'nb', 'NNO': 'nn', 'NYA': 'ny', 'OCI': 'oc', 'ORI': 'or', 'ORM': 'om', 'OSS': 'os', 'PLI': 'pi', 'PAN': 'pa', 'PER': 'fa', 'FAS': 'fa', 'POL': 'pl', 'POR': 'pt', 'PUS': 'ps', 'QUE': 'qu', 'ROH': 'rm', 'RUM': 'ro', 'RON': 'ro', 'RUN': 'rn', 'RUS': 'ru', 'SMO': 'sm', 'SAG': 'sg', 'SAN': 'sa', 'SRD': 'sc', 'SCC': 'sr', 'SRP': 'sr', 'SNA': 'sn', 'III': 'ii', 'SND': 'sd', 'SIN': 'si', 'SLO': 'sk', 'SLK': 'sk', 'SLV': 'sl', 'SOM': 'so', 'SOT': 'st', 'SPA': 'es', 'SUN': 'su', 'SWA': 'sw', 'SSW': 'ss', 'SWE': 'sv', 'TGL': 'tl', 'TAH': 'ty', 'TGK': 'tg', 'TAM': 'ta', 'TAT': 'tt', 'TEL': 'te', 'THA': 'th', 'TIB': 'bo', 'BOD': 'bo', 'TIR': 'ti', 'TON': 'to', 'TSO': 'ts', 'TSN': 'tn', 'TUR': 'tr', 'TUK': 'tk', 'TWI': 'tw', 'UIG': 'ug', 'UKR': 'uk', 'URD': 'ur', 'UZB': 'uz', 'VIE': 'vi', 'VOL': 'vo', 'WLN': 'wa', 'WEL': 'cy', 'CYM': 'cy', 'FRY': 'fy', 'WOL': 'wo', 'XHO': 'xh', 'YID': 'yi', 'YOR': 'yo', 'ZHA': 'za', 'ZUL': 'zu'}

#ordered_srcs = ['SRC', 'SNOMEDCT_US', 'ICD10', 'ICPC', 'MDR', 'LNC', 'MSH', 'AIR', 'ALT', 'AOD', 'AOT', 'ATC', 'BI', 'CCC', 'CCPSS', 'CCS', 'CCS_10', 'CDT', 'CHV', 'COSTAR', 'CPM', 'CPT', 'CSP', 'CST', 'CVX', 'DDB', 'DRUGBANK', 'DSM-5', 'DXP', 'FMA', 'GO', 'GS', 'HCDT', 'HCPCS', 'HCPT', 'HGNC', 'HL7V2.5', 'HL7V3.0', 'HPO', 'ICD10AE', 'ICD10AM', 'ICD10AMAE', 'ICD10CM', 'ICD10PCS', 'ICD9CM', 'ICF', 'ICF-CY', 'ICNP', 'ICPC2EENG', 'ICPC2ICD10ENG', 'ICPC2P', 'JABL', 'LCH', 'LCH_NW', 'MCM', 'MED-RT', 'MEDCIN', 'MEDLINEPLUS', 'MMSL', 'MMX', 'MTH', 'MTHCMSFRF', 'MTHHH', 'MTHICD9', 'MTHICPC2EAE', 'MTHICPC2ICD10AE', 'MTHMST', 'MTHSPL', 'MVX', 'NANDA-I', 'NCBI', 'NCI', 'NCI_BRIDG', 'NCI_BioC', 'NCI_CDC', 'NCI_CDISC', 'NCI_CDISC-GLOSS', 'NCI_CRCH', 'NCI_CTCAE', 'NCI_CTCAE_3', 'NCI_CTCAE_5', 'NCI_CTEP-SDC', 'NCI_CTRP', 'NCI_CareLex', 'NCI_DCP', 'NCI_DICOM', 'NCI_DTP', 'NCI_FDA', 'NCI_GAIA', 'NCI_GENC', 'NCI_ICH', 'NCI_JAX', 'NCI_KEGG', 'NCI_NCI-GLOSS', 'NCI_NCI-HGNC', 'NCI_NCI-HL7', 'NCI_NCPDP', 'NCI_NICHD', 'NCI_PI-RADS', 'NCI_PID', 'NCI_RENI', 'NCI_UCUM', 'NCI_ZFin', 'NDDF', 'NDFRT', 'NDFRT_FDASPL', 'NDFRT_FMTSME', 'NEU', 'NIC', 'NOC', 'NUCCPT', 'OMIM', 'OMS', 'PCDS', 'PDQ', 'PNDS', 'PPAC', 'PSY', 'QMR', 'RAM', 'RCD', 'RCDAE', 'RCDSA', 'RCDSY', 'RXNORM', 'SNM', 'SNMI', 'SNOMEDCT_VET', 'SOP', 'SPN', 'ULT', 'UMD', 'USP', 'USPMG', 'UWDA', 'VANDF', 'WHO']
#terminology_2_priority = { terminology : i * 2 for i, terminology in enumerate(ordered_srcs) }


def create_model():
  PYM = get_ontology("http://PYM/")
  PYM.python_module = "owlready2.pymedtermino2.model"
  
  with PYM:
    class Concept(Thing): pass
    
    class originals(Concept >> Concept):
      class_property_type = ["some", "only"]
      
    class unifieds(Concept >> Concept):
      class_property_type = ["some", "only"]
      inverse = originals
      
    class SemanticType(Thing): pass
    
    class Group(Thing): pass
    
    class groups(Concept >> Group): pass
    
    class synonyms(AnnotationProperty): pass
    
    class terminology(AnnotationProperty): pass
    
    class definitions(AnnotationProperty): pass
    
  return PYM



normstr_storid = default_world._abbreviate("http://www.w3.org/2001/XMLSchema#normalizedString")
bool_storid    = default_world._abbreviate("http://www.w3.org/2001/XMLSchema#boolean")


def parse_mrrank(PYM, terminologies, langs, importer, f, remnant = ""):
  for line in f:
    if remnant: line = "%s%s" % (remnant, line); remnant = ""
    try:
      rank, terminology, tty, suppress, _dropit = line.split("|")
    except: return line
    
    if (importer.terminologies and (not terminology in importer.terminologies) and (terminology != "SRC")): continue
    if suppress in importer.remove_suppressed: continue
    
    importer.tty_2_priority[terminology, tty] = int(rank)
  
    
def parse_mrconso(PYM, terminologies, langs, importer, f, remnant = ""):
  for line in f:
    if remnant: line = "%s%s" % (remnant, line); remnant = ""
    try:
      cui, lang, ts, lui, stt, sui, is_pref, aui, saui, scui, \
        sdui, terminology, tty, orig_code, term, srl, suppress, cvf, _dropit = line.split("|")
    except: return line
    
    lang = iso_3_letter_2_2_letter_lang[lang]
    
    if langs and (not lang in importer.langs): continue
    
    if (terminology == "SRC") and orig_code.startswith("V-"): orig_code = orig_code[2:]
    if (importer.terminologies and (not terminology in importer.terminologies)):
      if not ((terminology == "SRC") and ((orig_code == "SRC") or (orig_code in importer.terminologies))):
        continue
    
    if   orig_code == "NOCODE":
      orig_code = importer.next_arbitrary_code
      importer.next_arbitrary_code += 1
    elif orig_code == "R40-F46.9": orig_code = "R40-R46.9" # Error in UMLS!
    elif orig_code == "R90-F94.9": orig_code = "R90-R94.9" # Error in UMLS!
    
    if importer.extract_cui:
      cui               = importer._abbreviate("http://PYM/CUI/%s" % cui)
    orig                = importer._abbreviate("http://PYM/%s/%s" % (terminology, orig_code))
    
    importer.aui_2_orig[aui] = orig
    
    if suppress in importer.remove_suppressed: continue
    
    if not terminology in importer.created_terminologies:
      importer.created_terminologies.add(terminology)
      importer.terminology_2_parents[terminology] = defaultdict(set)
      
    if importer.extract_cui:
      if not cui in importer.cui_2_origs:
        importer.objs.append((cui, rdf_type, owl_class))
        #importer.objs.append((cui, rdfs_subclassof, PYM.UnifiedConcept.storid))
        importer.objs.append((cui, rdfs_subclassof, importer.CUI))
        importer.objs.append((cui, PYM.terminology.storid, importer.CUI))
        importer.cui_2_origs   [cui] = { orig }
        importer.cui_2_terms   [cui] = []
      else:
        importer.cui_2_origs[cui].add(orig)
        
    if not orig in importer.orig_2_terminology:
      terminology_storid = importer._abbreviate("http://PYM/SRC/%s" % terminology)
      importer.objs.append((orig, rdf_type, owl_class))
      importer.objs.append((orig, PYM.terminology.storid, terminology_storid))
      importer.orig_2_terminology[orig] = terminology      
      importer.orig_2_terms      [orig] = []
      if importer.extract_cui: importer.orig_2_cuis[orig] = set()
      
      if (terminology == "SRC") and (orig_code != "SRC"):
        importer.terminology_2_parents["SRC"][orig].add(importer._abbreviate("http://PYM/SRC/SRC"))
        
    label_priority = importer.tty_2_priority[terminology, tty]
    importer.orig_2_terms[orig].append((label_priority, term, lang))
    
    if importer.extract_cui:
      importer.cui_2_terms[cui].append((label_priority, term, lang))
      if not cui in importer.orig_2_cuis[orig]:
        importer.orig_2_cuis[orig].add(cui)
        importer.restrict(orig, SOME, PYM.unifieds.storid,  cui)
        importer.restrict(cui,  SOME, PYM.originals.storid, orig)
        
    importer.check_insert()

  
# def parse_mrhier(PYM, terminologies, langs, importer, f, remnant = ""):
#   for line in f:
#     if remnant: line = "%s%s" % (remnant, line); remnant = ""
#     try:
#       cui1, aui1, cxn, parent_aui, terminology, rela, hier, hcd, cvf, _dropit = line.split("|")
#     except: return line
    
#     parent_aui = hier.rsplit(".", 1)[-1]
    
#     child_orig  = importer.aui_2_orig.get(aui1)
#     if not child_orig: continue
#     parent_orig = importer.aui_2_orig.get(parent_aui)
#     if not parent_orig: continue
    
#     if (child_orig != parent_orig) and (child_orig in importer.orig_2_terminology):
#       importer.terminology_2_parents[importer.orig_2_terminology[child_orig]] [child_orig].add(parent_orig)
      
#     importer.check_insert()
    

def parse_mrrel(PYM, terminologies, langs, importer, f, remnant_previous = ""):
  if remnant_previous == "":
    remnant = ""
    previous = [None] * 17
  else:
    remnant, previous = remnant_previous
    
  for line in f:
    if remnant: line = "%s%s" % (remnant, line); remnant = ""
    current = line.split("|")
    if len(current) < 17: return line, previous
    
    current = [current[i] or previous[i] for i in range(len(previous))]
    cui1, aui1, stype1, rel, cui2, aui2, stype2, rela, rui, srui, \
      terminology, sl, group_i, direct, suppress, cvf, _dropit = current
    
    if suppress in importer.remove_suppressed:
      previous = current
      continue
    
    cui1 = cui1 or previous[0]
    direct = direct == "Y"
    
    if (rel == "PAR") or (rel == "CHD"):
      if rel == "PAR": cui1, aui1, stype1 = cui2, aui2, stype2
      
      if aui1 and aui2:
        orig1 = importer.aui_2_orig.get(aui1)
        orig2 = importer.aui_2_orig.get(aui2)
        if orig1 and (orig1 != orig2) and (orig2 in importer.orig_2_terminology):
          importer.terminology_2_parents[importer.orig_2_terminology[orig2]] [orig2].add(orig1)
          
    elif importer.extract_relations:
      orig1 = importer.aui_2_orig.get(aui1)
      orig2 = importer.aui_2_orig.get(aui2)
      if orig1 and orig2:
        if (not orig1 in importer.orig_2_terminology) or (not orig2 in importer.orig_2_terminology): continue
        prop = importer.get_prop((rela or rel), owl_object_property)
        importer.mkrel(orig2, prop, orig1, group_i, direct)
        
    importer.check_insert()
    previous = current
    
    
def parse_mrsat(PYM, terminologies, langs, importer, f, remnant_previous = ""):
  if remnant_previous == "":
    remnant = ""
    previous = [None] * 14
  else:
    remnant, previous = remnant_previous
    
  for line in f:
    if remnant: line = "%s%s" % (remnant, line); remnant = ""
    current = line.split("|")
    if len(current) < 14: return line, previous
    
    if not current[0]: current = [current[i] or previous[i] for i in range(len(previous))]
    cui, lui, sui, metaui, stype, code, atui, satui, atn, terminology, atv, suppress, cvf, _dropit = current
    
    if suppress in importer.remove_suppressed:
      previous = current
      continue
    if importer.terminologies and (not terminology in importer.terminologies):
      previous = current
      continue
    
    prop = importer.get_prop(atn.lower(), owl_annotation_property)
    
    if   metaui == "":
      if importer.extract_cui:
        cui = importer._abbreviate("http://PYM/CUI/%s" % cui)
        importer.datas.append((cui, prop, atv, 0))
        
    elif metaui.startswith("A"):
      orig = importer.aui_2_orig.get(metaui)
      if not orig is None:
        importer.datas.append((orig, prop, atv, 0))
        
    importer.check_insert()
    previous = current
    
    
def parse_mrdef(PYM, terminologies, langs, importer, f, remnant = ""):
  for line in f:
    if remnant: line = "%s%s" % (remnant, line); remnant = ""
    try:
      cui, aui, atui, satui, terminology, defin, suppress, cvf, _dropit = line.split("|")
    except: return line
    
    if (importer.terminologies and (not terminology in importer.terminologies)): continue
    if suppress in importer.remove_suppressed: continue

    orig = importer.aui_2_orig.get(aui)
    if not orig is None:
      importer.datas.append((orig, PYM.definitions.storid, defin, 0))
      
    importer.check_insert()


def parse_mrsty(PYM, terminologies, langs, importer, f, remnant = ""):
  for line in f:
    if remnant: line = "%s%s" % (remnant, line); remnant = ""
    try:
      cui, tui, stn, sty, atui, cvf, _dropit = line.split("|")
    except: return line
    
    sem = importer.semantic_types.get(tui)
    if sem is None:
      sem = importer._abbreviate("http://PYM/TUI/%s" % tui)
      importer.semantic_types[tui] = sem
      importer.datas.append((sem, label.storid, sty, 0))
      
    importer.objs.append((cui, rdfs_subclassof, sem))
    
    importer.check_insert()
    
def parse_srdef(PYM, terminologies, langs, importer, f, remnant = ""):
  for line in f:
    if remnant: line = "%s%s" % (remnant, line); remnant = ""
    try:
      rt, tui, term, stn, defin, ex, un, nh, abr, inv, _dropit = line.split("|")
    except: return line
    
    sem = importer._abbreviate("http://PYM/TUI/%s" % tui)
    importer.semantic_types[tui] = sem
    importer.datas.append((sem, label.storid, term, "@en"))
    importer.datas.append((sem, PYM.synonyms.storid, abr, "@en"))
    importer.datas.append((sem, PYM.definitions.storid, defin, 0))
    
    if inv:
      importer.objs.append((sem, owl_inverse_property, ))
      
    importer.check_insert()


    
def break_cycles(parents, terminology = ""):
  equivalences = set()
  
  nb = 0
  already = set()
  for node in parents:
    if node in already: continue
    nb += 1
    
    paths = [[node]]
    explored_paths = ""
    while paths:
      new_paths = []
      for path in paths:
        already.add(path[-1])
        next_nodes = parents.get(path[-1], [])
        for next_node in next_nodes:
          if next_node in path: # Cycle found
            cycle = frozenset(path[path.index(next_node):] + [next_node])
            equivalences.add(cycle)
          else:
            new_paths.append(path + [next_node])
      paths = new_paths

  equivalences2 = []
  for cycle in equivalences:
    for other in equivalences:
      if other == cycle: continue
      if other.issuperset(cycle): break
    else: # No superset
      equivalences2.append(cycle)
      
  
  del equivalences
  nb_cycles = len(equivalences2)
  print("   ", terminology, ":", nb_cycles, "cycles found:", ", ".join(str(set(i)) for i in equivalences2))
  
  new_parents = { k : set(v) for k, v in parents.items() }
  equivalences3 = []
  for cycle in equivalences2:
    d = Counter()
    if isinstance(next(iter(parents.values())), Counter):
      for i in cycle:
        for p in parents[i]:
          if p in cycle: d[p] += parents[i][p]
    else:
      for i in cycle:
        for p in parents[i]:
          if p in cycle: d[p] += 1
    mosts = d.most_common()
    if mosts[0][1] >= 2 * mosts[1][1]:
      print("        Breaking cycle", mosts, "by considering", mosts[0][0], "as parent of the others")
      for i in cycle:
        for j in cycle:
          if j in new_parents[i]: new_parents[i].remove(j)
      for i in cycle:
        if i == mosts[0][0]: continue
        new_parents[i].add(mosts[0][0])
        
    else:
      print("        Breaking cycle", mosts, "by considering all concepts as equivalent")
      for i in cycle:
        for j in cycle:
          if j in new_parents[i]: new_parents[i].remove(j)
      cycle_parents = set()
      for i in cycle: cycle_parents.update(new_parents[i])
      for i in cycle: new_parents[i].update(cycle_parents)
      
      equivalences3.append(cycle)
      
  return new_parents, equivalences3, nb_cycles


def finalize(PYM, importer):
  # print("Breaking CUI cycles...")
  # #open("/tmp/parents.txt", "w").write("parents = %s" % importer.cui_parents)
  # parents, equivalences = break_cycles(importer.cui_parents)
  # print("   ", len(equivalences), "cycles found")
  
  # for cui in importer.cui_parents:
  #   cui_parents = parents.get(cui)
  #   if cui_parents:
  #     for parent in cui_parents:
  #       importer.objs.append((cui, rdfs_subclassof, parent))
  #   else:
  #     importer.objs.append((cui, rdfs_subclassof, PYM.UnifiedConcept.storid))
  # importer.check_insert()
  
  # for cycle in equivalences:
  #   cycle = list(cycle)
  #   for other in cycle[1:]:
  #     importer.objs.append((cycle[0], owl_equivalentclass, other))
  # importer.check_insert()
  
  
  print("Breaking ORIG cycles...")
  terminology_2_origs = { terminology : [] for terminology in importer.terminology_2_parents }
  for orig, terminology in importer.orig_2_terminology.items():
    terminology_2_origs[terminology].append(orig)
    
  for terminology, parents in importer.terminology_2_parents.items():
    #open("/tmp/parents2.txt", "w").write("parents = %s" % parents)
    parents, equivalences, nb_cycles = break_cycles(parents, terminology)
    for orig in terminology_2_origs[terminology]:
      orig_parents = parents.get(orig)
      if orig_parents:
        for parent in orig_parents:
          importer.objs.append((orig, rdfs_subclassof, parent))
      else:
        terminology = importer.orig_2_terminology[orig]
        if terminology == "SRC":
          importer.objs.append((orig, rdfs_subclassof, PYM.Concept.storid))
        else:
          importer.objs.append((orig, rdfs_subclassof, importer._abbreviate("http://PYM/SRC/%s" % terminology)))
          
    importer.check_insert()

    for cycle in equivalences:
      cycle = list(cycle)
      for other in cycle[1:]:
        importer.objs.append((cycle[0], owl_equivalentclass, other))
    importer.check_insert()
  del importer.terminology_2_parents
  terminology_2_origs = None

  
  print("Finalizing only properties and restrictions...")
  for (x, prop), ys in importer.onlys.items():
    if   len(ys) == 1:
      importer.restrict(x, ONLY, prop, ys[0])
    elif ys:
      l  = importer.create_rdf_obj_list(ys)
      bn = importer.new_blank_node()
      importer.objs.append((bn, rdf_type, owl_class))
      importer.objs.append((bn, owl_unionof, l))
      importer.restrict(x, ONLY, prop, bn)
  del importer.onlys
  
  for prop in set(importer.direct_props.keys()) | set(importer.indirect_props.keys()):
    if importer.indirect_props[prop] > importer.direct_props[prop]:
      importer.datas.append((prop, owlready_class_property_type, "only", 0))
  del importer.direct_props
  del importer.indirect_props
      
      
  print("Finalizing CUI - ORIG mapping...")
  if importer.extract_cui:
    for cui, cui_origs in importer.cui_2_origs.items():
      cui_origs = list(cui_origs)
    
      if   len(cui_origs) == 1:
        importer.restrict(cui, ONLY, PYM.originals.storid, cui_origs[0])
        
      elif len(cui_origs)  > 0:
        l  = importer.create_rdf_obj_list(cui_origs)
        bn = importer.new_blank_node()
        importer.objs.append((bn, rdf_type, owl_class))
        importer.objs.append((bn, owl_unionof, l))
        importer.restrict(cui, ONLY, PYM.originals.storid, bn)
        
      importer.check_insert()
    del importer.cui_2_origs
    
    for orig, orig_cuis in importer.orig_2_cuis.items():
      orig_cuis = list(orig_cuis)
      
      if   len(orig_cuis) == 1:
        importer.restrict(orig, ONLY, PYM.unifieds.storid, orig_cuis[0])
        
      elif len(orig_cuis)  > 0:
        l  = importer.create_rdf_obj_list(orig_cuis)
        bn = importer.new_blank_node()
        importer.objs.append((bn, rdf_type, owl_class))
        importer.objs.append((bn, owl_unionof, l))
        importer.restrict(orig, ONLY, PYM.unifieds.storid, bn)
        
      importer.check_insert()
    del importer.orig_2_cuis
    
class _Importer(object):
  def __init__(self, PYM, terminologies, langs, extract_groups, extract_attributes, extract_relations, extract_definitions, remove_suppressed):
    self.PYM          = PYM
    self.terminologies = terminologies
    self.langs         = langs
    self.extract_groups      = extract_groups
    self.extract_attributes  = extract_attributes
    self.extract_relations   = extract_relations
    self.extract_definitions = extract_definitions
    self.remove_suppressed   = remove_suppressed
    
    self.tty_2_priority = defaultdict(int)
    self.created_terminologies = set()
    self.cui_2_origs = {}
    self.orig_2_cuis = {}
    self.orig_2_terminology = {}
    self.aui_2_orig  = {}
    self.props = set()
    self.terminology_2_parents = {}
    self.cui_parents = {}
    self.next_arbitrary_code = 1
    
    
    self.orig_2_terms = {}
    self.cui_2_terms  = {}
    self.partial_relations = {}
    self.relations = set()
    self.semantic_types = {}
    self.groups = {}
    self.extract_cui = (not terminologies) or ("CUI" in terminologies)
    self.onlys = defaultdict(list)
    self.indirect_props = Counter()
    self.direct_props   = Counter()
    
    self.objs, self.datas, self.on_prepare_obj, self.on_prepare_data, self.insert_objs, self.insert_datas, self.new_blank_node, self._abbreviate, self.on_finish = PYM.graph.create_parse_func(delete_existing_triples = False)
    
    if self.extract_cui:
      self.CUI = self._abbreviate("http://PYM/SRC/CUI")
      self.objs .append((self.CUI, rdfs_subclassof, PYM.Concept.storid))
      self.objs .append((self.CUI, PYM.terminology.storid, self._abbreviate("http://PYM/SRC/SRC")))
      self.datas.append((self.CUI, label.storid, "UMLS unified concepts (CUI)", 0))
      
      
  def after(self, parser): # Free some memory
    self.check_insert()
    if   parser == "MRCONSO":
      for orig, terms in self.orig_2_terms.items():
        terms.sort()
        self.datas.append((orig, label.storid, terms[-1][1], "@%s" % terms[-1][2]))
        for priority, term, lang in terms[:-1]:
          self.datas.append((orig, self.PYM.synonyms.storid, term, "@%s" % lang))
        self.check_insert()
      del self.orig_2_terms
      
      for cui, terms in self.cui_2_terms.items():
        terms.sort()
        self.datas.append((cui, label.storid, terms[-1][1], "@%s" % terms[-1][2]))
        for priority, term, lang in terms[:-1]:
          self.datas.append((cui, self.PYM.synonyms.storid, term, "@%s" % lang))
        self.check_insert()
        
      #for cui, origs in self.cui_2_origs.items():
      #  terms = []
      #  for orig in origs:
      #    terms.extend(self.orig_2_terms[orig])
      #  terms.sort()
      #  self.datas.append((cui, label.storid, terms[-1][1], "@%s" % terms[-1][2]))
      #  for priority, term, lang in terms[:-1]:
      #    self.datas.append((cui, self.PYM.synonyms.storid, term, "@%s" % lang))
      #  self.check_insert()
      
      del self.cui_2_terms
      
    elif parser == "MRREL":
      del self.relations
      del self.partial_relations
      del self.groups
      
    elif parser == "MRSAT":
      del self.aui_2_orig
      
  def get_prop(self, name, type):
    prop = self._abbreviate("http://PYM/%s" % name)
    if not prop in self.props:
      self.objs.append((prop, rdf_type, type))
      self.props.add(prop)
    return prop
  
  def get_group(self, orig, i):
    group = self.groups.get((orig, i))
    if group is None:
      group = self.groups[orig, i] = self._abbreviate("http://PYM/groups/%s_%s" % (orig, i))
      self.objs.append((group, rdf_type, owl_class))
      self.objs.append((group, rdfs_subclassof, self.PYM.Group.storid))
      self.restrict(orig, SOME, self.PYM.groups.storid, group)
    return group
  
  def mkrel(self, orig2, prop, orig1, group_i, direct):
    if direct:
      self.direct_props[prop] += 1
      if not (orig2, prop, orig1) in self.relations: # Else, already done by a relation in another group
        self.restrict(orig2, SOME, prop, orig1)
        self.relations.add((orig2, prop, orig1))
      if group_i and self.extract_groups:
        self.restrict(self.get_group(orig2, group_i), SOME, prop, orig1)
    else:
      self.indirect_props[prop] += 1
      if not (orig2, prop, orig1) in self.relations: # Else, already done by a relation in another group
        self.onlys[orig2, prop].append(orig1)
        
  def restrict(self, a, qual, prop, b):
    bn = self.new_blank_node()
    self.objs.append((a, rdfs_subclassof, bn))
    self.objs.append((bn, rdf_type, owl_restriction))
    self.objs.append((bn, owl_onproperty, prop))
    self.objs.append((bn, qual, b))
    return bn
  
  def check_insert(self):
    if len(self.objs ) > 300000: self.insert_objs ()
    if len(self.datas) > 300000: self.insert_datas()
    
  def force_insert(self):
    self.insert_objs ()
    self.insert_datas()
    
  def create_rdf_obj_list(self, l):
    bnode = bnode0 = self.new_blank_node()
    for i in range(len(l)):
      self.objs.append((bnode, rdf_first, l[i]))
      if i < len(l) - 1:
        bnode_next = self.new_blank_node()
        self.objs.append((bnode, rdf_rest, bnode_next))
        bnode = bnode_next
      else:
        self.objs.append((bnode, rdf_rest, rdf_nil))
    return bnode0
    
    
def import_umls(umls_zip_filename, terminologies = None, langs = None, fts_index = True, extract_groups = True, extract_attributes = True, extract_relations = True, extract_definitions = True, remove_suppressed = "OEY"):
  if terminologies:
    terminologies = set(terminologies)
  if langs:
    langs = set(langs)

  PYM = create_model()
  default_world.save()
  
  #default_world.graph.set_indexed(False)
  
  importer = _Importer(PYM, terminologies, langs, extract_groups, extract_attributes, extract_relations, extract_definitions, remove_suppressed)
  
  parsers = [
    ("MRRANK",  parse_mrrank),
    ("MRCONSO", parse_mrconso),
  ]
  if extract_definitions: parsers.append(("MRDEF"  , parse_mrdef))
  parsers.append(("MRREL"  , parse_mrrel))
  if extract_attributes: parsers.append(("MRSAT"  , parse_mrsat))
  #if (not terminology) or ("CUI" in terminologies): parsers["MRSTY"] = parse_mrsty
  
  remnants = defaultdict(str)
  
  remnant_mrconso = remnant_mrrel = ""
  
  previous_parser = None
  
  if os.path.isdir(umls_zip_filename):
    print("Importing UMLS from directory %s with Python version %s.%s..." % (umls_zip_filename, sys.version_info.major, sys.version_info.minor))
    inner_filenames = sorted(os.listdir(umls_zip_filename))
    print("Files found in this directory: %s" % ", ".join(inner_filenames))
    if not "MRCONSO.RRF" in inner_filenames:
      print("WARNING: file MRCONSO.RRF not found!")
    for table_name, parser in parsers:
      for inner_filename in inner_filenames:
        if ("%s.RRF" % table_name) in inner_filename:
          if previous_parser != table_name: importer.after(previous_parser)
          print("  Parsing %s as %s..." % (inner_filename, table_name))
          remnants[table_name] = parser(PYM, terminologies, langs, importer,
                                        open(os.path.join(umls_zip_filename, inner_filename)),
                                        remnants[table_name])
          importer.force_insert()
          default_world.save()
          previous_parser = table_name
  else:
    print("Importing UMLS from Zip file %s with Python version %s.%s..." % (umls_zip_filename, sys.version_info.major, sys.version_info.minor))

    def parse_umls_zip(umls_inner_zip):
      nonlocal previous_parser
      inner_filenames = sorted(umls_inner_zip.namelist())
      for table_name, parser in parsers:
        for inner_filename in inner_filenames:
          if ("/%s.RRF" % table_name) in inner_filename:
            if previous_parser != table_name: importer.after(previous_parser)
            print("  Parsing %s as %s" % (inner_filename, table_name), end = "")
            if inner_filename.lower().endswith(".gz"):
              f = gzip.open(umls_inner_zip.open(inner_filename), "rt", encoding = "UTF-8")
              print(" with encoding %s" % f.encoding)
            else:
              f = io.TextIOWrapper(umls_inner_zip.open(inner_filename), "UTF-8")
              print()
            remnants[table_name] = parser(PYM, terminologies, langs, importer,
                                          f,
                                          remnants[table_name])
            importer.force_insert()
            default_world.save()
            previous_parser = table_name
            
    
    with zipfile.ZipFile(umls_zip_filename, "r") as umls_zip:
      filenames = sorted(umls_zip.namelist())
      
      #for filename in filenames:
      #  if filename.endwiths("/META/") or filename.endwiths("/META"):
      #    full_umls = False
      #    break
      #else: full_umls = True

      #if full_umls:
      parse_umls_zip(umls_zip)
      for filename in filenames:
        if filename.endswith("-meta.nlm"):
          print("Full UMLS release - importing UMLS from inner Zip file %s..." % filename)
          fp = umls_zip.open(filename)
          if not fp.seekable():
            raise Exception("PyMedTermino2 import require Python version >= 3.7 (but after import, the quadstore can be used by Python 3.6)")
          with zipfile.ZipFile(fp, "r") as umls_inner_zip:
            parse_umls_zip(umls_inner_zip)
            
      #else:
      #  parse_inner_zip(umls_zip)
        
      #for filename in filenames:
      #  if filename.endswith("-meta.nlm"):
      #    print("Importing UMLS from Zip file %s with Python version %s..." % (filename, sys.version))
      #    
      #    fp = umls_zip.open(filename)
      #    if not fp.seekable():
      #      raise Exception("PyMedTermino2 import require Python version >= 3.7 (but after import, the quadstore can be used by Python 3.6)")
      #    with zipfile.ZipFile(fp, "r") as umls_inner_zip:
      #      parse_inner_zip(umls_inner_zip)
            #inner_filenames = sorted(umls_inner_zip.namelist())
            #for table_name, parser in parsers:
            #  for inner_filename in inner_filenames:
            #    if ("/%s.RRF" % table_name) in inner_filename:
            #      if previous_parser != table_name: importer.after(previous_parser)
            #      print("  Parsing %s as %s" % (inner_filename, table_name), end = "")
            #      f = gzip.open(umls_inner_zip.open(inner_filename), "rt", encoding = "UTF-8")
            #      print(" with encoding %s" % f.encoding)
            #      remnants[table_name] = parser(PYM, terminologies, langs, importer,
            #                                    f,
            #                                    remnants[table_name])
            #      importer.force_insert()
            #      default_world.save()
            #      previous_parser = table_name
                  
  finalize(PYM, importer)
  importer.force_insert()
  importer.on_finish()
  importer = None # Free memory
  #default_world.save()
  
  #print("Indexing...")
  #default_world.graph.set_indexed(True)
  PYM = get_ontology("http://PYM/").load()
  
  if fts_index:
    print("FTS Indexing...")
    default_world.full_text_search_properties.append(label)
    default_world.full_text_search_properties.append(PYM.synonyms)
    
  import owlready2.pymedtermino2.model
  default_world.save()
  return PYM
