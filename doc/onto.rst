Managing ontologies
===================

Creating an ontology
--------------------

A new empty ontology can be obtained with the get_ontology() function; it takes a single parameter,
the IRI of the ontology.
The IRI is a sort of URL; IRIs are used as identifier for ontologies.

::

   >>> from owlready2 import *
   
   >>> onto = get_ontology("http://test.org/onto.owl")


.. note::
   
   If an ontology has already been created for the same IRI, it will be returned.
   
.. note::
   
   Some ontologies use a # character in IRI to separate the name of the ontology from the name of the
   entities, while some others uses a /. By default, Owlready2 uses a #, if you want to use a /, the IRI
   should ends with /.

   Examples:

   ::

      >>> onto = get_ontology("http://test.org/onto.owl") # => http://test.org/onto.owl#entity

      >>> onto = get_ontology("http://test.org/onto") # => http://test.org/onto#entity
      
      >>> onto = get_ontology("http://test.org/onto/") # => http://test.org/onto/entity
  



Loading an ontology from OWL files
----------------------------------

Use the .load() method of an ontology for loading it.

The easiest way to load the ontology is to load a local copy. In this case, the IRI is the
local filename prefixed with "file://", for example:

::

   >>> onto = get_ontology("file:///home/jiba/onto/pizza_onto.owl").load()

   
If an URL is given, Owlready2 first searches for a local copy of the OWL file and,
if not found, tries to download it from the Internet. For example:

::

   >>> onto_path.append("/path/to/owlready/onto/")
   
   >>> onto = get_ontology("http://www.lesfleursdunormal.fr/static/_downloads/pizza_onto.owl").load()

The onto_path global variable contains a list of directories for searching local copies of ontologies.
It behaves similarly to sys.path (for Python modules / packages).

The get_ontology() function returns an ontology from its IRI, and creates a new empty ontology if needed.

The .load() method loads the ontology from a local copy or from Internet.
It is **safe** to call .load() several times on the same ontology.
It will be loaded only once.

.. note::
   
   Owlready2 currently reads the following file format: RDF/XML, OWL/XML, NTriples.
   The file format is automatically detected.

   NTriples is a very simple format and is natively supported by Owlready2.
   
   RDF/XML is the most common format; it is also natively supported by Owlready2 (since version 0.2).
   
   OWL/XML is supported using a specific parser integrated to Owlready2.
   This parser supports a large subset of OWL, but is not complete.
   It has been tested mostly with OWL files created with the Protégé editor or with Owlready itself.
   Consequently, preferred formats are RDF/XML and NTriples.

   
   


Accessing the content of an ontology
------------------------------------

You can access to the content of an ontology using the 'dot' notation, as usual in Python or more generally
in Object-Oriented Programming. In this way, you can access the Classes, Instances, Properties,
Annotation Properties,... defined in the ontology.
The [] syntax is also accepted.

::

   >>> print(onto.Pizza)
   onto.Pizza
   
   >>> print(onto["Pizza"])
   onto.Pizza

An ontology has the following attributes:

 * .base_iri : base IRI for the ontology
 * .imported_ontologies : the list of imported ontologies (see below)

and the following methods:

 * .classes() : returns a generator for the Classes defined in the ontology (see :doc:`class`)
 * .individuals() : returns a generator for the individuals (or instances) defined in the ontology (see :doc:`class`)
 * .object_properties() : returns a generator for ObjectProperties defined in the ontology (see :doc:`properties`)
 * .data_properties() : returns a generator for DataProperties defined in the ontology (see :doc:`properties`)
 * .annotation_properties() : returns a generator for AnnotationProperties defined in the ontology (see :doc:`annotations`)
 * .properties() : returns a generator for all Properties (object-, data- and annotation-) defined in the ontology
 * .disjoint_classes() : returns a generator for AllDisjoint constructs for Classes defined in the ontology (see :doc:`disjoint`)
 * .disjoint_properties() : returns a generator for AllDisjoint constructs for Properties defined in the ontology (see :doc:`disjoint`)
 * .disjoints() : returns a generator for AllDisjoint constructs (for Classes and Properties) defined in the ontology
 * .different_individuals() : returns a generator for AllDifferent constructs for individuals defined in the ontology (see :doc:`disjoint`)
 * .get_namepace(base_iri) : returns a namespace for the ontology and the given base IRI (see namespaces below, in the next section)
   
.. note::

   Many methods returns a generator. Generators allows iterating over the values without creating a list,
   which can improve performande. However, they are often not very convenient when exploring the ontology:

   ::

      >>> onto.classes()
      <generator object _GraphManager.classes at 0x7f854a677728>
      
   A generator can be trandformed into a list with the list() Python function:

   ::
      
      >>> list(onto.classes())
      [pizza_onto.CheeseTopping, pizza_onto.FishTopping, pizza_onto.MeatTopping,
      pizza_onto.Pizza, pizza_onto.TomatoTopping, pizza_onto.Topping,
      pizza_onto.NonVegetarianPizza]
      
      
The IRIS pseudo-dictionary can be used for accessing an entity from its full IRI:

::

   >>> IRIS["http://www.lesfleursdunormal.fr/static/_downloads/pizza_onto.owl#Pizza"]
   pizza_onto.Pizza


Ontologies can also define entities located in other namespaces, for example
Gene Ontology (GO) has the following IRI: 'http://purl.obolibrary.org/obo/go.owl',
but the IRI of GO entities are of the form 'http://purl.obolibrary.org/obo/GO_entity' (note the missing 'go.owl#').
See :doc:`namespace` to learn how to access such entities.


Simple queries
--------------


Simple queries can be performed with the .search() method of the ontology. It expects one or several keyword
arguments. The supported keywords are:

* **iri**, for searching entities by its full IRI
* **type**, for searching Individuals of a given Class
* **subclass_of**, for searching subclasses of a given Class
* **is_a**, for searching both Individuals and subclasses of a given Class
* **subproperty_of**, for searching subproperty of a given Property
* any object, data or annotation property name

Special arguments are:

* **_use_str_as_loc_str**: whether to treats plain Python strings as strings in any language (default is True)
* **_case_sensitive**: whether to take lower/upper case into consideration (default is True)
* **_bm25**: if True, returns a list of (entity, relevance) pairs instead of just the entities (default is False)

The value associated to each keyword can be a single value or a list of several values.
A star * can be used as a jocker in string values.

.. warning::

   .search() does not perform any kind of reasoning, it just searches in asserted facts.
   In addition, it cannot find Classes through SOME or ONLY restrictions.

For example, for searching for all entities with an IRI ending with 'Topping':

::

   >>> onto.search(iri = "*Topping")
   [pizza_onto.CheeseTopping, pizza_onto.FishTopping, pizza_onto.MeatTopping,
   pizza_onto.TomatoTopping, pizza_onto.Topping]

In addition, the special value "*" can be used as a wildcard for any object.
For example, the following line searches for all individuals that are related
to another one with the 'has_topping' relation (NB there is none in the default pizza_onto.owl file):

::

   >>> onto.search(has_topping = "*")

When a single return value is expected, the .search_one() method can be used. It works similarly:

::

   >>> onto.search_one(label = "my label")
   

Owlready classes and individuals can be used as values within search(), as follows:

::

   >>> onto.search_one(is_a = onto.Pizza)
   
   
Finally, search() can be nested, as in the following example:

::

   >>> onto.search(is_a = onto.Pizza, has_topping = onto.search(is_a = onto.TomatoTopping))

Owlready automatically combines nested searches in a single, optimized, search.

For more complex queries, SQPARQL can be used with RDFlib (see :doc:`world`).


Ontology metadata
-----------------

The metadata of the ontology can be accessed with .metadata, in read and write access:

::

   >>> print(onto.metadata.comment)
   [...]
   >>> onto.metadata.comment.append("my first comment")

Any annotation can be used with .metadata.


Importing other ontologies
--------------------------

An ontology can import other ontologies, like a Python module can import other modules.

The imported_ontologies attribute of an ontology is a list of the ontology it imports. You can add
or remove items in that list:

::

   >>> onto.imported_ontologies.append(owlready_ontology)


Saving an ontology to an OWL file
---------------------------------

The .save() method of an ontology can be used to save it.
It will be saved in the first directory in onto_path.

::

   >>> onto.save()
   >>> onto.save(file = "filename or fileobj", format = "rdfxml")

.save() accepts two optional parameters: 'file', a file object or a filename for saving the ontology,
and 'format', the file format (default is RDF/XML).

.. note::
   
   Owlready2 currently writes the following file format: "rdf/xml", "ntriples".
   
   NTriples is a very simple format and is natively supported by Owlready2.
   
   RDF/XML is the most common format; it is also natively supported by Owlready2 (since version 0.2).
   
   OWL/XML is not yet supported for writing.
