Owlready2
=========

.. image:: https://readthedocs.org/projects/owlready2/badge/?version=latest
   :target: http://owlready2.readthedocs.io/en/latest/
   :alt: documentation

.. image:: http://www.lesfleursdunormal.fr/static/_images/owlready_downloads.svg
   :target: http://www.lesfleursdunormal.fr/static/informatique/pymod_stat_en.html
   :alt: download stats


         
Owlready2 is a module for ontology-oriented programming in Python 3, including an optimized RDF quadstore.

Owlready2 can:

 - Import OWL 2.0 ontologies in NTriples, RDF/XML or OWL/XML format.

 - Export OWL 2.0 ontologies to NTriples or RDF/XML.

 - Manipulates ontology classes, instances and properties transparently,
   as if they were normal Python objects.

 - Add Python methods to ontology classes.

 - Perform automatic classification of classes and instances, using the HermiT reasoner.

 - Tested up to 100 millions of RDF triples (but can potentially support more).

 - In addition, the quadstore is compatible with the RDFlib Pyton module, which can be used to perform SPARQL queries.
   
Owlready has been created by Jean-Baptiste Lamy at the LIMICS reseach lab.
It is available under the GNU LGPL licence v3.
If you use Owlready in scientific works, **please cite the following article**:

   **Lamy JB**.
   `Owlready: Ontology-oriented programming in Python with automatic classification and high level constructs for biomedical ontologies. <http://www.lesfleursdunormal.fr/_downloads/article_owlready_aim_2017.pdf>`_
   **Artificial Intelligence In Medicine 2017**;80:11-28
   
In case of troubles, questions or comments, please use this Forum/Mailing list: http://owlready.8326.n8.nabble.com


  
What can I do with Owlready2?
-----------------------------

Load an ontology from a local repository, or from Internet:

::

  >>> from owlready2 import *
  >>> onto_path.append("/path/to/your/local/ontology/repository")
  >>> onto = get_ontology("http://www.lesfleursdunormal.fr/static/_downloads/pizza_onto.owl")
  >>> onto.load()

Create new classes in the ontology, possibly mixing OWL constructs and Python methods:

::

  >>> class NonVegetarianPizza(onto.Pizza):
  ...   equivalent_to = [
  ...     onto.Pizza
  ...   & ( onto.has_topping.some(onto.MeatTopping)
  ...     | onto.has_topping.some(onto.FishTopping)
  ...     ) ]
  ...   def eat(self): print("Beurk! I'm vegetarian!")

Access ontology class, and create new instances / individuals:

::

  >>> onto.Pizza
  pizza_onto.Pizza
  >>> test_pizza = onto.Pizza("test_pizza_owl_identifier")
  >>> test_pizza.has_topping = [ onto.CheeseTopping(),
  ...                            onto.TomatoTopping(),
  ...                            onto.MeatTopping  () ]

Export to RDF/XML file:

::

  >>> test_onto.save()

Perform reasoning, and classify instances and classes:

::

   >>> test_pizza.__class__
   onto.Pizza
   
   >>> # Execute HermiT and reparent instances and classes
   >>> sync_reasoner()
   
   >>> test_pizza.__class__
   onto.NonVegetarianPizza
   >>> test_pizza.eat()
   Beurk! I'm vegetarian !

For more documentation, look at the doc/ directories in the source.

Changelog
---------

version 1 - 0.2
***************

* Fix sync_reasonner and Hermit call under windows (thanks Clare Grasso)

version 1 - 0.3
***************

* Add warnings
* Accepts ontologies files that do not ends with '.owl'
* Fix a bug when loading ontologies including concept without a '#' in their IRI

version 2 - 0.1
***************

* Full rewrite, including an optimized quadstore

version 2 - 0.2
***************

* Implement RDFXML parser and generator in Python (no longer use rapper or rdflib)
* Property chain support
* Add ntriples_diff.py utility
* Bugfixes:
  - Fix breaklines in literal when exporting to NTriples

version 2 - 0.3
***************

* Add destroy_entity() global function
* Greatly improve performance for individual creation
* When searching, allow to use "*" as a jocker for any object
* Bugfixes:
  - Fix nested intersections and unions
  - Fix boolean
  - Fix bug when removing parent properties
  - Fix parsing of rdf:ID
  - Fix multiple loading of the same ontology whose IRI is modified by OWL file, using an ontology alias table
  - Fix ClassConstruct.subclasses()
  - Check for properties with multiple incompatible classes (e.g. ObjectProperty and Annotation Property)

version 2 - 0.4
***************

* Add methods for querying the properties defined for a given individuals, the inverse properties
  and the relation instances (.get_properties(), .get_inverse_properties() and .get_relations())
* Add .indirect() method to obtain indirect relations (considering subproperties, transivitity,
  symmetry and reflexibity)
* search() now takes into account inheritance and inverse properties
* search() now accepts 'None' for searching for entities without a given relation
* Optimize ontology loading by recreating SQL index from scratch
* Optimize SQL query for transitive quadstore queries, using RECURSIVE Sqlite3 statements
* Optimize SQL query for obtaining the number of RDF triples (ie len(default_world.graph))
* Add Artificial Intelligence In Medicine scientific article in doc and Readme 
* Bugfixes:
  - Fix properties loading when reusing an ontology from a disk-stored quadstore
  - Fix _inherited_property_value_restrictions() when complement (Not) is involved
  - Fix restrictions with cardinality
  - Fix doc on AllDisjoint / AllDifferent

version 2 - 0.5
***************

* Add individual/instance editor (require EditObj3, still largely untested)
* Add support for hasSelf restriction
* Optimize XML parsers
* Check for cyclic subclass of/subproperty of, and show warning
* PyPy 3 support (devel version of PyPy 3)
* Bugfixes:
  - Fix search() for '*' value on properties with inverse
  - Fix individual.annotation = "..." and property.annotation = "..."
  - Fix PlainLiteral annotation with no language specified
  - Fix doc for Creating classes dynamically
  - Fix loading ontologies with python_name annotations
  - Fix _inherited_property_value_restrictions when multiple is-a / equivalent-to are present
  - Align Python floats with xsd:double rather than xsd:decimal
  - Rename module 'property' as 'prop', to avoid name clash with Python's 'property()' type

version 2 - 0.6
***************

* Add set_datatype_iri() global function for associating a Python datatype to an IRI
* Add nquads ontology format (useful for debugging)
* Add support for dir() on individuals
* Add support for ontology using https: protocol (thanks Samourkasidis Argyrios)
* Add observe module (for registering callback when the ontology is modified)
* Improve docs
* Bugfixes:
  - Align Python floats with xsd:decimal rather than xsd:double, finally, because decimal accepts int too
  - Fix Class.instances() so as it returns instances of subclasses (as indicated in the doc)
  - Fix direct assignation to Ontology.imported_ontologies
  - Fix a bug in reasoning, when adding deduced facts between one loaded and one non-loaded entity

version 2 - 0.7
***************

* Bugfixes:
  - Restore HermiT compiled with older Java compilator (higher compatibility)
  
version 2 - 0.8
***************

* Bugfixes:
  - REALLY restore HermiT compiled with older Java compilator (higher compatibility)
  - Fix search(prop = "value") when value is a string and the ontology uses localized string
  

Links
-----

Owlready2 on BitBucket (development repository): https://bitbucket.org/jibalamy/owlready2

Owlready2 on PyPI (Python Package Index, stable release): https://pypi.python.org/pypi/Owlready2

Documentation: http://owlready2.readthedocs.io/

Forum/Mailing list: http://owlready.8326.n8.nabble.com


Contact "Jiba" Jean-Baptiste Lamy:

::

  <jean-baptiste.lamy *@* univ-paris13 *.* fr>
  LIMICS
  University Paris 13, Sorbonne Paris Cite
  Bureau 149
  74 rue Marcel Cachin
  93017 BOBIGNY
  FRANCE
