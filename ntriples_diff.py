# -*- coding: utf-8 -*-
# Owlready
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

#cp -f ./owlready2/test/test.owl /tmp/t.owl
#cp -f ./owlready2/test/test_inverse.owl /tmp/t.owl
#cp -f ./owlready2/test/test_reasoning.owl /tmp/t.owl
#cp -f ./owlready2/test/test_breakline.owl /tmp/t.owl
#cp -f ~/telechargements/base_med/obi.owl /tmp/t.owl

#rapper /tmp/t.owl > /tmp/rap.nt   ; python -c 'b = open("/tmp/rap.nt", "rb").read(); lb = b.split(b"\n"); ls = [i.replace(b"\\" + b"\"", b"\\\\" + b"\"").decode("unicode-escape").replace("\n", "\\n") for i in lb]; s = "\n".join(ls); open("/tmp/rap2.nt", "w").write(s)'
#python ./owlready2/rdfxml_2_ntriples.py /tmp/t.owl > /tmp/py.nt
#python ./owlready2/ntriples_diff.py /tmp/rap.nt /tmp/py.nt --short

"""ntriples_diff.py

Compute the differences between 2 NTriples files. Take care of symmetric relations
and different blank node naming.

Usage:

  ntriple_diff.py onto.nt : canonize the NTriples file.

  ntriple_diff.py onto1.nt onto2.nt : compare the two NTriples files.

Options:

  --short : shortify IRI and literal (more Human readable).
"""

import sys, os, warnings


def shortify(triples):
  triples2 = []
  for s,p,o, l in triples:
    if "#" in s: s = "<%s" % s.split("#", 1)[-1]
    if "#" in p: p = "<%s" % p.split("#", 1)[-1]
    if o.startswith('"'):
      o = o[1:].rsplit('"', 1)[0]
    elif "#" in o:
      o = "<%s" % o.split("#", 1)[-1]
    triples2.append((s,p,o, l))
  return triples2


symmetric_predicates = {
  "<http://www.w3.org/2002/07/owl#complementOf>",
  "<http://www.w3.org/2002/07/owl#inverseOf>",
  "<http://www.w3.org/2002/07/owl#equivalentClass>",
  "<http://www.w3.org/2002/07/owl#equivalentProperty>",
  "<http://www.w3.org/2002/07/owl#sameAs>",
  "<http://www.w3.org/2002/07/owl#disjointWith>",
  }

useless_triples = {
  ("<http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral>", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", "<http://www.w3.org/2000/01/rdf-schema#Datatype>"),
  ("<http://www.w3.org/2000/01/rdf-schema#Literal>", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", "<http://www.w3.org/2000/01/rdf-schema#Datatype>"),
  ("<http://www.w3.org/2001/XMLSchema#float>", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", "<http://www.w3.org/2000/01/rdf-schema#Datatype>"),
  ("<http://www.w3.org/2001/XMLSchema#integer>", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", "<http://www.w3.org/2000/01/rdf-schema#Datatype>"),
  ("<http://www.w3.org/2001/XMLSchema#nonNegativeInteger>", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", "<http://www.w3.org/2000/01/rdf-schema#Datatype>"),
  ("<http://www.w3.org/2001/XMLSchema#string>", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", "<http://www.w3.org/2000/01/rdf-schema#Datatype>"),

  }

class Blank(object):
  def __init__(self):
    self.triples = set()
    self.name    = None
    
  def add_triple(self, s,p,o):
    if isinstance(s, Blank): s = "_"
    if isinstance(o, Blank): o = "_"
    self.triples.add((s,p,o))
    
  def get_name(self):
    if not self.name: self.name = "_:%s" % hash(frozenset(self.triples))
    return self.name
  
  
def canonize(nt):
  triples = []
  blanks  = {}
  l       = 0
  nt = nt.replace("/>", ">") # Owlready remove trailing /
  for line in nt.split("\n"):
    if not line: continue
    l += 1
    #print(l, line)
    if line.startswith("#") or not line: continue
    line = line[:-1].strip()
    s,p,o = line.split(None, 2)
    if o.endswith("^^<http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral>"): o = o.rsplit("^^", 1)[0]
    if s.startswith("_"): s = blanks.get(s) or Blank()
    if o.startswith("_"): o = blanks.get(o) or Blank()
    if isinstance(s, Blank): s.add_triple(s,p,o)
    if isinstance(o, Blank): o.add_triple(s,p,o)
    triples.append((s,p,o, l))
    if p in symmetric_predicates:
      if isinstance(s, Blank): s.add_triple(o,p,s)
      if isinstance(o, Blank): o.add_triple(o,p,s)
      triples.append((o,p,s, 0))
      
      
  triples2 = []
  for s,p,o, l in triples:
    if isinstance(s, Blank): s = s.get_name()
    if isinstance(o, Blank): o = o.get_name()
    triples2.append((s,p,o, l))
    
  #triples2.sort()
  return triples2
  

def diff(nt1, nt2):
  triples1 = canonize(nt1)
  triples2 = canonize(nt2)
  
  triples1_set = set((s,p,o) for (s,p,o, l) in triples1)
  triples2_set = set((s,p,o) for (s,p,o, l) in triples2)
  
  removed = []
  added   = []
  
  for s,p,o, l in triples1:
    if (s,p,o) in useless_triples: continue
    if not (s,p,o) in triples2_set:
      removed.append((s,p,o, l))
      
  for s,p,o, l in triples2:
    if (s,p,o) in useless_triples: continue
    if not (s,p,o) in triples1_set:
      added.append((s,p,o, l))
      
  return removed, added


if __name__ == "__main__":
  
  if "--short" in sys.argv:
    sys.argv.remove("--short")
    short = True
  else:
    short = False
    
  if   len(sys.argv) == 2:
    nt = open(sys.argv[1]).read()
    triples = canonize(nt)
    
    if short: triples = shortify(triples)
    
    for s,p,o in sorted(triples):
      print(s,p,o, ".")
      
  elif len(sys.argv) == 3:
    nt1 = open(sys.argv[1]).read()
    nt2 = open(sys.argv[2]).read()
    removed, added = diff(nt1, nt2)
    
    if short:
      removed = shortify(removed)
      added   = shortify(added)
      
    for s,p,o, l in removed:
      if l: print("-", s, p, o, ". # line", l)
    print()
    for s,p,o, l in added:
      if l: print("+", s, p, o, ". # line", l)
    
