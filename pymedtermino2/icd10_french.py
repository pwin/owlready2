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


import sys, os, io, types, zipfile, urllib.request
from collections import defaultdict, Counter
from owlready2 import *


def import_icd10_french(atih_data = "https://www.atih.sante.fr/plateformes-de-transmission-et-logiciels/logiciels-espace-de-telechargement/telecharger/gratuit/11616/456"):
  PYM  = get_ontology("http://PYM/").load()
  ICD10 = PYM["ICD10"]
  
  print("Importing CIM10 from %s..." % atih_data)
  if atih_data.startswith("http:") or atih_data.startswith("https:"):
    f = urllib.request.urlopen(atih_data)
    f = io.BytesIO(f.read())
  else:
    f = open(atih_data, "rb")
  
  parents = []
  
  onto = get_ontology("http://atih/cim10/")
  with onto:
    class mco_had(AnnotationProperty): pass
    class psy    (AnnotationProperty): pass
    class ssr    (AnnotationProperty): pass
    
  with onto.get_namespace("http://PYM/SRC/"):
    ICD10_FRENCH = types.new_class("CIM10", (PYM["SRC"],))
    onto._set_obj_triple_spo  (ICD10_FRENCH.storid, PYM.terminology.storid, PYM["SRC"].storid)
    onto._set_data_triple_spod(ICD10_FRENCH.storid, label.storid, "CIM10", "@fr")
    
  with onto.get_namespace("http://PYM/CIM10/"):
    for line in open(os.path.join(os.path.dirname(__file__), "icd10_french_group_name.txt")).read().split(u"\n"):
      line = line.strip()
      if line and not line.startswith("#"):
        code, term = line.split(" ", 1)
        icd10 = ICD10[code]
        if not icd10:
          icd10 = ICD10["%s.9" % code]
          if not icd10:
            if   code == "B95-B98": icd10 = ICD10["B95-B97.9"]
            elif code == "G10-G14": icd10 = ICD10["G10-G13.9"]
            elif code == "J09-J18": icd10 = ICD10["J10-J18.9"]
            elif code == "K55-K64": icd10 = ICD10["K55-K63.9"]
            elif code == "O94-O99": icd10 = ICD10["O95-O99.9"]
            
        if icd10 is None:
          if not code in {"C00-C75", "V01-X59", "U00-U99", "U00-U49", "U82-U85", "U90-U99"}:
            print("WARNING: cannot align %s (%s) with ICD10 in UMLS!" % (code, term))
            
        start, end = code.split("-")
        end = "%s.99" % end
        for parent_start, parent_end, parent in parents:
          if (start >= parent_start) and (end <= parent_end):
            break
        else:
          if not code in {'F00-F99', 'H60-H95', 'E00-E90', 'R00-R99', 'L00-L99', 'O00-O99', 'C00-D48', 'M00-M99', 'U00-U99', 'S00-T98', 'K00-K93', 'G00-G99', 'I00-I99', 'H00-H59', 'N00-N99', 'V01-Y98', 'Q00-Q99', 'P00-P96', 'Z00-Z99', 'A00-B99', 'D50-D89', 'J00-J99'}:
            print("WARNING: cannot find parent for %s (%s)!" % (code, term))
          parent = ICD10_FRENCH
          
        icd10_french = types.new_class(code, (parent,))
        icd10_french.label = locstr(term, "fr")
        onto._set_obj_triple_spo(icd10_french.storid, PYM.terminology.storid, ICD10_FRENCH.storid)
        if icd10:
          icd10.unifieds = icd10.unifieds
          #with PYM:
          for cui in icd10.unifieds: cui.originals.append(icd10_french)
            
        parents.append((start, end, icd10_french))
        
        
    with zipfile.ZipFile(f, "r") as atih_zip:
      for line in atih_zip.open("LIBCIM10MULTI.TXT", "r"):
        if isinstance(line, bytes): line = line.decode("latin")
        line = line.strip()
        code, mco_had, ssr, psy, term_court, term = line.split("|")
        code = code.strip()
        if len(code) > 3: code = "%s.%s" % (code[:3], code[3:])
        

        if "+" in code:
          parent_code = code.split("+", 1)[0]
        else:
          parent_code = code[:-1]
          if parent_code.endswith("."): parent_code = code[:-2]
        parent = ICD10_FRENCH[parent_code]
        
        if not parent:
          code2 = code.split("+", 1)[0]
          for parent_start, parent_end, parent in reversed(parents):
            if (code2 >= parent_start) and (code2 <= parent_end):
              break
          else:
            print("WARNING: cannot find parent for %s (%s)!" % (code, term))
            parent = None
            
        icd10 = ICD10[code]
        
        if term.startswith("*** SU16 *** "): term = term.replace("*** SU16 *** ", "")
        
        icd10_french = types.new_class(code, (parent,))
        onto._set_obj_triple_spo(icd10_french.storid, PYM.terminology.storid, ICD10_FRENCH.storid)
        icd10_french.label = locstr(term, "fr")
        icd10_french.mco_had = [int(mco_had)]
        icd10_french.ssr     = [ssr]
        icd10_french.psy     = [int(psy)]
        if icd10:
          icd10_french.unifieds = icd10.unifieds
          #with PYM:
          for cui in icd10.unifieds: cui.originals.append(icd10_french)
          
  default_world.save()
        
