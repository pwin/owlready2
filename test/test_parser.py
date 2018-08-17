import sys, os

HERE = os.path.dirname(__file__)

def rm(f):
  try:    os.unlink(f)
  except: pass
  

def do(c):
  #print(c)
  r = os.system(c)
  if r: raise Exception("Error when running:'%s'!" % c)

def make_variants(orig_filename, force_variant = None):
  control(orig_filename)
  
  if (not force_variant) or (force_variant == "original"):
    print("Test %s %s ..." % (orig_filename, "original"))
    rm("/tmp/t.rdf")
    b = open(orig_filename, "rb").read()
    open("/tmp/t.rdf", "wb").write(b)
    yield "original"
    
  if (not force_variant) or (force_variant == "owlready2-ntriples"):
    print("Test %s %s ..." % (orig_filename, "owlready2-ntriples"))
    rm("/tmp/t.rdf")
    do("""python -c 'from owlready2 import *;\
    onto = get_ontology("file://%s").load();\
    onto.save("/tmp/t.rdf",  format = "ntriples");\
    '""" % orig_filename)
    yield "owlready2-ntriples"
    
  if (not force_variant) or (force_variant == "owlready2-rdfxml"):
    print("Test %s %s ..." % (orig_filename, "owlready2-rdfxml"))
    rm("/tmp/t.rdf")
    do("""python -c 'from owlready2 import *;\
    onto = get_ontology("file://%s").load();\
    onto.save("/tmp/t.rdf", format = "rdfxml");\
    '""" % orig_filename)
    yield "owlready2-rdfxml"
    
  if (not force_variant) or (force_variant == "rapper-ntriples"):
    print("Test %s %s ..." % (orig_filename, "rapper-ntriples"))
    rm("/tmp/t.rdf")
    do("rapper %s > /tmp/t.rdf 2> /dev/null" % orig_filename)
    yield "rapper-ntriples"
    
  if (not force_variant) or (force_variant == "rapper-rdfxml"):
    print("Test %s %s ..." % (orig_filename, "rapper-rdfxml"))
    rm("/tmp/t.rdf")
    do("rapper %s -o rdfxml > /tmp/t.rdf 2> /dev/null" % orig_filename)
    yield "rapper-rdfxml"
    
  if (not force_variant) or (force_variant == "rapper-rdfxml-abbrev"):
    print("Test %s %s ..." % (orig_filename, "rapper-rdfxml-abbrev"))
    rm("/tmp/t.rdf")
    do("rapper %s -o rdfxml-abbrev > /tmp/t.rdf 2> /dev/null" % orig_filename)
    yield "rapper-rdfxml-abbrev"
    
  if (not force_variant) or (force_variant == "owlapi-rdfxml"):
    print("Test %s %s ..." % (orig_filename, "owlapi-rdfxml"))
    rm("/tmp/t.rdf")
    owlapi(orig_filename, "/tmp/t.rdf", "rdf")
    rapper("/tmp/t.rdf", "/tmp/control.nt")
    yield "owlapi-rdfxml"
    
  if (not force_variant) or (force_variant == "owlapi-owlxml"):
    print("Test %s %s ..." % (orig_filename, "owlapi-owlxml"))
    rm("/tmp/t.rdf")
    owlapi(orig_filename, "/tmp/t.rdf", "owl")

    owlapi("/tmp/t.rdf", "/tmp/control.rdf", "rdf")
    rapper("/tmp/control.rdf", "/tmp/control.nt")
    yield "owlapi-owlxml"

def rapper(filename, dest):
  rm(dest)
  do("rapper %s -g > %s 2> /dev/null" % (filename, dest))
  b = open(dest, "rb").read()
  lb = b.split(b"\n")
  #ls = [i.replace(b"\\" + b"\"", b"\\\\" + b"\"").decode("unicode-escape").replace("\n", "\\n").replace("\\", "\\\\") for i in lb]
  ls = []
  for i in lb:
    if not i: continue
    s,p,o = i.split(None, 2)
    if o.startswith(b'"'):
      v, d = o[1:].rsplit(b'"', 1)
      v = v.decode("unicode-escape").replace('\\', '\\\\').replace("\n", "\\n").replace('"', '\\"').encode("utf8")
      i = b'%s %s "%s"%s' % (s, p, v, d)
    ls.append(i)
  s = b"\n".join(ls)
  open(dest, "wb").write(s)


def owlapi(orig, dest, format):
  #do("java -cp ./antibio_arcenciel/owlready_cas_dut_1/owlapi-3.4.3.jar:%s/test Save %s %s %s 2> /dev/null" % (HERE, orig, format, dest))
  do("java -cp %s/../hermit/HermiT.jar:%s Save %s %s %s 2> /dev/null" % (HERE, HERE, orig, format, dest))
  

def control(filename): rapper(filename, "/tmp/control.nt")
  
def test(filename, variant):
  rm("/tmp/py.nt")
  rm("/tmp/py.rdf")
  #do("python ./owlready2/rdfxml_2_ntriples.py %s > /tmp/py.nt 2> /dev/null" % tmp_filename)
  do("""python -c 'from owlready2 import *;\
  onto = get_ontology("file:///tmp/t.rdf").load();\
  onto.save("/tmp/py.nt",  format = "ntriples");\
  onto.save("/tmp/py.rdf", format = "rdfxml");\
  '""")
  
  rm("/tmp/log")
  do("python %s/../ntriples_diff.py /tmp/control.nt /tmp/py.nt > /tmp/log" % HERE)
  s = open("/tmp/log").read()
  if s.strip() != "":
    print("    FAILED (ntriples)")
    return 0
  
  rm("/tmp/py.nt")
  rapper("/tmp/py.rdf", "/tmp/py.nt")
  
  rm("/tmp/log")
  do("python %s/../ntriples_diff.py /tmp/control.nt /tmp/py.nt > /tmp/log" % HERE)
  s = open("/tmp/log").read()
  if s.strip() != "":
    print("    FAILED (rdfxml)")
    return 0
  
  return 1
  

if   len(sys.argv) > 2:
  rdf_files     = [sys.argv[1]]
  force_variant =  sys.argv[2]
  
elif len(sys.argv) > 1:
  rdf_files     = [sys.argv[1]]
  force_variant = None
  
else:
  rdf_files = [
    "/home/jiba/src/owlready2/test/test.owl",
    "/home/jiba/src/owlready2/test/test_ns.owl",
    "/home/jiba/src/owlready2/test/test_breakline.owl",
    "/home/jiba/telechargements/base_med/aeo.owl",
    "/home/jiba/telechargements/base_med/agro.owl",
    "/home/jiba/telechargements/base_med/bfo.owl",
    "/home/jiba/telechargements/base_med/bfo-1.1.owl",
    "/home/jiba/telechargements/base_med/obi.owl",
    "/home/jiba/telechargements/base_med/uberon.owl",
    "/home/jiba/telechargements/base_med/vto.owl",
    "/home/jiba/telechargements/base_med/go.owl",
  ]
  force_variant = None
  

nb_ok = nb_test = 0
for filename in rdf_files:
  for variant in make_variants(filename, force_variant):
    nb_test += 1
    nb_ok   += test(filename, variant)

print("%s/%s tests passed" % (nb_ok, nb_test))


