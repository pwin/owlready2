Worlds
======

Owlready2 stores every triples in a 'World' object, and it can handles several Worlds
in parallel. 'default_world' is the World used by default.


Persistent world: storing the quadstore in an SQLite3 file database
-------------------------------------------------------------------

Owlready2 uses an optimized quadstore. By default, the quadstore is stored in memory, but it can also be
stored in an SQLite3 file. This allows persistance: all ontologies loaded and created are stored in the file,
and can be reused later.
This is interesting for big ontologies: loading huge ontologies can take time, while opening the SQLite3 file
takes only a fraction of second, even for big files.
It also avoid to load huge ontologies in memory, if you only need to access a few
entities from these ontologies.

The .set_backend() method of World sets the SQLite3 filename associated to the quadstore,
for example:

::

   >>> default_world.set_backend(filename = "/path/to/your/file.sqlite3")

.. note::
   
   If the quad store is not empty when calling .set_backend(), RDF triples are automatically copied.
   However, this operation can have a high performance cost (especially if there are many triples).


When using persistence, the .save() method of World must be called for saving the actual
state of the quadstore in the SQLite3 file:

::

   >>> default_world.save()

Storing the quadstore in a file does not reduce the performance of Owlready2 (actually,
it seems that Owlready2 performs a little *faster* when storing the quadstore on the disk).

To reload an ontology stored in the quadstore (when the corresponding OWL file has been updated),
the reload and reload_if_newer optional parameters of .load() can be used (the former reload the ontology,
and the latter reload it only if the OWL file is more recent).

By default, Owlready2 opens the SQLite3 database in exclusive mode. This mode is faster, but it does not allow
several programs to use the same database simultaneously. If you need to have several Python programs that
access simultaneously the same Owlready2 quadstore, you can disable the exclusive mode as follows:

::

   >>> default_world.set_backend(filename = "/path/to/your/file.sqlite3", exclusive = False)



Using several isolated Worlds
-----------------------------

Owlready2 can support several, isolated, Worlds.
This is interesting if you want to load several version
of the same ontology, for example before and after reasoning.

A new World can be created using the World class:

::

   >>> my_world = World()
   >>> my_second_world = World(filename = "/path/to/quadstore.sqlite3")

Ontologies are then created and loaded using the .get_ontology() methods of the World
(when working with several Worlds, this method replaces the get_ontology() global function):

::

   >>> onto = my_world.get_ontology("http://test.org/onto/").load()

The World object can be used as a pseudo-dictionary for accessing entities using their IRI.
(when working with several Worlds, this method replaces the IRIS global pseudo-dictionary):
   
::

   >>> my_world["http://test.org/onto/my_iri"]

Finally, the reasoner can be executed on a specific World:
   
::

   >>> sync_reasoner(my_world)


Working with RDFlib for performing SPARQL queries
-------------------------------------------------

Owlready2 uses an optimized RDF quadstore. This quadstore can also be accessed
as an RDFlib graph as follows:

::

   >>> graph = default_world.as_rdflib_graph()


In particular, the RDFlib graph can be used for performing SPARQL queries:

::

   >>> r = list(graph.query("""SELECT ?p WHERE {
     <http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza> <http://www.semanticweb.org/jiba/ontologies/2017/0/test#price> ?p .
   }"""))




The results can be automatically converted to Python and Owlready using the .query_owlready() method instead of .query():

::

   >>> r = list(graph.query_owlready("""SELECT ?p WHERE {
     <http://www.semanticweb.org/jiba/ontologies/2017/0/test#ma_pizza> <http://www.semanticweb.org/jiba/ontologies/2017/0/test#price> ?p .
   }"""))


Owlready blank nodes can be created with the graph.BNode() method:

::

   >>> bn = graph.BNode()
   >>> with onto:
   ...     graph.add((bn, rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), rdflib.URIRef("http://www.w3.org/2002/07/owl#Class"))) 
