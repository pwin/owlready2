Welcome to Owlready2's documentation!
*************************************

Owlready2 is a module for ontology-oriented programming in Python. It can load OWL 2.0 ontologies
as Python objects, modify them, save them, and perform reasoning via HermiT
(included). Owlready2 allows a transparent access to OWL ontologies (contrary
to usual Java-based API).

Owlready version 2 includes an optimized triplestore / quadstore, based on SQLite3.
This quadstore is optimized both for performance and memory consumption. Controray to version 1,
Owlready2 can deal with big ontologies.

Owlready2 has been created at the LIMICS reseach lab,
University Paris 13, Sorbonne Paris Cité, INSERM UMRS 1142, Paris 6 University, by
Jean-Baptiste Lamy. It was developed during the VIIIP research project funded by ANSM, the French Drug Agency;
this is why some examples in this documentation relate to drug ;).

Owlready2 is available under the GNU LGPL licence v3.
A forum/mailing list is available for Owlready on Nabble: http://owlready.8326.n8.nabble.com


Table of content
----------------

.. toctree::
   intro.rst
   onto.rst
   class.rst
   properties.rst
   restriction.rst
   disjoint.rst
   mixing_python_owl.rst
   reasoning.rst
   annotations.rst
   namespace.rst
   world.rst
   porting1.rst
