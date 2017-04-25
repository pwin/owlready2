Namespaces
==========

In Owlready2, a namespace represent a given base IRI inside a given ontology,
for example 'http://test.org/onto/pharmaco' inside the ontology 'http://test.org/onto'.
However, notice that the Semantic Web allows all ontologies to share namespaces;
thus the base IRI of the namespace **does not** need to be a subdirectory of the
base IRI of the ontology.


Creating classes in a specific namespace
----------------------------------------

When creating a Class or a Property,
the namespace attribute is used to build the full IRI of the Class,
and to define in which ontology the Class is defined
(RDF triples are added to this ontology).
The Class IRI is equals to the namespace's base IRI (base_iri) + the Class name.

An ontology can always be used as a namespace, as seen in :doc:`class`.
A namespace object can be used if you want to locate the Class at a different IRI.
For example:

::

   >>> onto      = get_ontology("http://test.org/onto/")
   >>> namespace = onto.get_namespace("http://test.org/onto/pharmaco")
   
   >>> class Drug(Thing):
   ...     namespace = namespace


In the example above, the Drug Class IRI is "http://test.org/pharmaco/Drug", but the Drug Class
belongs to the 'http://test.org/onto' ontology.

Owlready2 proposes 3 methods for indicating the namespace:

 * the 'namespace' Class attribute
 * the 'with namespace' statement
 * if not provided, the namespace is inherited from the first parent Class

The following examples illustrate the 3 methods:
   
::

   >>> class Drug(Thing):
   ...     namespace = namespace

   >>> with namespace:
   ...     class Drug(Thing):
   ...         pass

   >>> class Drug2(Drug):
   ...     # namespace is implicitely Drug.namespace
   ...     pass

   
Modifying a class defined in another ontology
---------------------------------------------

In OWL, an ontology can also *modify* a Class already defined in another ontology.

In Owlready2, this can be done using the 'with namespace' statement.
Every RDF triples added (or deleted) inside a 'with namespace' statement
goes in the ontology corresponding to the namespace of the 'with namespace' statement.

The following example creates the Drug Class in a first ontology,
and then asserts that Drug is a subclass of Substance in a second ontology.

::
   
   >>> onto1 = get_ontology("http://test.org/my_first_ontology.owl")
   >>> onto2 = get_ontology("http://test.org/my_second_ontology.owl")
   
   >>> with onto1:
   ...     class Drug(Thing):
   ...         pass

   >>> with onto2:
   ...     class Substance(Thing):
   ...         pass
   
   ...     Drug.is_a.append(Substance)

