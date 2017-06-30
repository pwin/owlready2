Introduction
============

Owlready2 is a module for manipulating OWL 2.0 ontologies in Python. It can load, modify, save ontologies, and
it supports reasoning via HermiT (included). Owlready allows a transparent access to OWL ontologies.

Owlready2 can:

 - Import ontologies in RDF/XML, OWL/XML or NTriples format.

 - Manipulates ontology classes, instances and annotations as if they were Python objects.

 - Add Python methods to ontology classes.

 - Re-classify instances automatically, using the HermiT reasoner.


Short example: What can I do with Owlready?
-------------------------------------------

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
   
Access the classes of the ontology, and create new instances / individuals:

::
   
   >>> onto.Pizza
   pizza_onto.Pizza
   
   >>> test_pizza = onto.Pizza("test_pizza_owl_identifier")
   >>> test_pizza.has_topping = [ onto.CheeseTopping(),
   ...                            onto.TomatoTopping() ]

In Owlready2, almost any lists can be modified *in place*,
for example by appending/removing items from lists.
Owlready2 automatically updates the RDF quadstore.

::

   >> test_pizza.has_topping.append(onto.MeatTopping())
   
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

Export to OWL file:

::

  >>> onto.save()
  

Architecture
------------

Owlready2 maintains a RDF quadstore in an optimized SQLite3 database,
either in memory or on the disk (see :doc:`world`). It provides a high-level access to the Classes and the
objects in the ontology (aka. ontology-oriented programming). Classes and Invididuals are loaded
dynamically from the quadstore as needed, cached in memory and destroyed when no longer needed.


Contact and links
-----------------

A forum/mailing list is available for Owlready on Nabble: http://owlready.8326.n8.nabble.com

In case of trouble, please write to the forum or contact Jean-Baptiste Lamy <jean-baptiste.lamy *@* univ-paris13 *.* fr>

::

  LIMICS
  University Paris 13, Sorbonne Paris Cité
  Bureau 149
  74 rue Marcel Cachin
  93017 BOBIGNY
  FRANCE

Owlready on BitBucket (development repository): https://bitbucket.org/jibalamy/owlready
