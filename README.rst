Owlready2
=========

Owlready2 is a module for ontology-oriented programming in Python 3, including an optimized RDF quadstore.

Owlready2 can:

 - Import OWL 2.0 ontologies in NTriples, RDF/XML or OWL/XML format.

 - Export OWL 2.0 ontologies to NTriples or RDF/XML.

 - Manipulates ontology classes, instances and properties transparently,
   as if they were normal Python objects.

 - Add Python methods to ontology classes.

 - Perform automatic classification of classes and instances, using the HermiT reasoner.

 - In addition, the quadstore is compatible with the RDFlib Pyton module, which can be used to perform SPARQL queries.
   
Owlready has been created by Jean-Baptiste Lamy at the LIMICS reseach lab.
It is available under the GNU LGPL licence v3.
In case of trouble, please contact Jean-Baptiste Lamy
<jean-baptiste.lamy *@* univ-paris13 *.* fr>

::

  LIMICS
  University Paris 13, Sorbonne Paris Cité
  Bureau 149
  74 rue Marcel Cachin
  93017 BOBIGNY
  FRANCE

  
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
  * Fix breaklines in literal when exporting to NTriples

version 2 - 0.3
***************

* Add destroy_entity() global function
* Greatly improve performance for individual creation
* When searching, allow to use "*" as a jocker for any object
* Bugfixes:
  * Fix nested intersections and unions
  * Fix boolean
  * Fix bug when removing parent properties
  * Fix parsing of rdf:ID
  * Fix multiple loading of the same ontology whose IRI is modified by OWL file, using an ontology alias table
  * Fix ClassConstruct.subclasses()
  * Check for properties with multiple incompatible classes (e.g. ObjectProperty and Annotation Property)


Links
-----

Owlready2 on BitBucket (development repository): https://bitbucket.org/jibalamy/owlready2

Owlready2 on PyPI (Python Package Index, stable release): https://pypi.python.org/pypi/Owlready2

Documentation: http://pythonhosted.org/Owlready2

Forum/Mailing list: http://owlready.8326.n8.nabble.com


Mail me for any comment, problem, suggestion or help !

Jiba -- Jean-Baptiste LAMY -- jibalamy @ free.fr
