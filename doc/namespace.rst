Namespaces
==========

Ontologies can define entities located in other namespaces.
An example is Gene Ontology (GO): the ontology IRI is 'http://purl.obolibrary.org/obo/go.owl',
but the IRI of GO entities are not of the form 'http://purl.obolibrary.org/obo/go.owl#GO_entity' but
'http://purl.obolibrary.org/obo/GO_entity' (note the missing 'go.owl#').


Accessing entities defined in another namespace
-----------------------------------------------

These entities can be accessed in Owlready2 using a namespace. The get_namepace(base_iri) global function
returns a namespace for the given base IRI.

The namespace can then be used with the dot notation, similarly to the ontology.

::
   
   >>> # Loads Gene Ontology (~ 170 Mb), can take a moment!
   >>> go = get_ontology("http://purl.obolibrary.org/obo/go.owl").load()
   
   >>> print(go.GO_0000001) # Not in the right namespace
   None
   
   >>> obo = get_namespace("http://purl.obolibrary.org/obo/")
   
   >>> print(obo.GO_0000001)
   obo.GO_0000001
   
   >>> print(obo.GO_0000001.iri)
   http://purl.obolibrary.org/obo/obo.GO_0000001
   
   >>> print(obo.GO_0000001.label)
   ['mitochondrion inheritance']

   
.get_namepace(base_iri) can also be called on an Ontology, for example:

::
   
   >>> obo = go.get_namespace("http://purl.obolibrary.org/obo/")

Namespaces created on an Ontology can also be used for asserting facts and creating classes, instances,...:

::

   >>> with obo:
   >>>     class MyNewClass(Thing): pass # Create http://purl.obolibrary.org/obo/MyNewClass
   

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

