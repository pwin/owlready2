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

 - Import OWL 2.0 ontologies in NTriples, RDF/XML or OWL/XML format

 - Export OWL 2.0 ontologies to NTriples or RDF/XML

 - Manipulates ontology classes, instances and properties transparently, as if they were normal Python objects

 - Add Python methods to ontology classes

 - Perform automatic classification of classes and instances, using the HermiT or Pellet reasoner (included)

 - Load DBpedia or UMLS (for medical terminology, using the integrated PyMedTermino2 submodule)

 - Tested up to 1 billion of RDF triples! (but can potentially support more)

 - In addition, the quadstore is compatible with the RDFlib Python module, which can be used to perform SPARQL queries
 
 - Finally, Owlready2 can also be used as an ORM (Object-Relational mapper) -- as a graph/object database, it beats Neo4J, MongoDB, SQLObject and SQLAlchemy in terms of performances
  
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
  >>> with onto:
  ...     class NonVegetarianPizza(onto.Pizza):
  ...       equivalent_to = [
  ...         onto.Pizza
  ...       & ( onto.has_topping.some(onto.MeatTopping)
  ...         | onto.has_topping.some(onto.FishTopping)
  ...         ) ]
  ...       def eat(self): print("Beurk! I'm vegetarian!")

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

Access to medical terminologies from UMLS:

::

  >>> from owlready2 import *
  >>> from owlready2.pymedtermino2.umls import *
  >>> default_world.set_backend(filename = "pym.sqlite3")
  >>> import_umls("umls-2018AB-full.zip", terminologies = ["ICD10", "SNOMEDCT_US", "CUI"])
  >>> default_world.save()
  
  >>> PYM = get_ontology("http://PYM/").load()
  >>> ICD10       = PYM["ICD10"]
  >>> SNOMEDCT_US = PYM["SNOMEDCT_US"]
  
  >>> SNOMEDCT_US[186675001]
  SNOMEDCT_US["186675001"] # Viral pharyngoconjunctivitis
  
  >>> SNOMEDCT_US[186675001] >> ICD10   # Map to ICD10
  Concepts([
    ICD10["B30.9"] # Viral conjunctivitis, unspecified
  ])
  
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
  
version 2 - 0.9
***************

* PostgresQL backend (in addition to SQLite3)
* Add 'exclusive = False' option for SQLite3 backend (slower, but allows multiple uses)
* Use unique index in sqlite3 quadstore on resources table
* Optimize sqlite3 quadstore by caching IRI dict (5% faster)
* Add == support for class construct
* Add get_namespace() support on World
* Add 'existential restrictions as class properties' feature
* Bugfixes:
  - Fix imported ontologies
  - Fix saving ontologies in onto_path
  - Fix clear() on CallbackList
  - Fix bug in Class IRI in ontologies whose base IRI ends with a /
  - Fix imported ontologies in ontologies whose base IRI ends with a /
  
version 2 - 0.10
****************

* Add Ontology.metadata for adding/querying ontology metadata
* Allows multiple individual creations with the same name/IRI, now returning the same individuals
* Add OwlReadyInconsistentOntologyError and Word.inconsistent_classes()
* Implement RDF/XML and OWL/XML parsing in Cython (25% speed boost for parsing)
* Small optimization
* Extend individual.prop.indirect() to include relations asserted at the class level
* Add .query_owlready() method to RDF graph 
* Bugfixes:
  - Fix reasoning when obtaining classes equivalent to nothing
  - Fix World creation with backend parameters
  - Fix error when adding property at the class definition level
  - Fix loading of ontology files with no extension from onto_path
  - Fix properties defined with type 'RDF Property' and subproperty of 'OWL Data/Object/Annotation Property'
  - Support old SQLite3 versions that do not accept WITHOUT ROWID
  - Fix reference to undeclared entities (they were replaced by None, now by their IRI)
  - Fix loading and saving ontologies whose base IRI ends with /
  - Fix RDF query using string
    
version 2 - 0.11
****************

* Optimized Full-Text Search
* Support Pellet reasoner in addition to HermiT
* Support loading of huge OWL files (incremental load)
* Use Class.property.indirect() for indirect Class property (instead of Class.property)
* Add reload and reload_if_newer parameters to Ontology.load()
* search() is now much faster on properties that have inverse
* Add shortcut for SOME ConstrainedDatatype: e.g. age >= 65
* Bugfixes:
  - Fix creation of an individual that already exists in the quadstore
  - Fix missing import of EntityClass in class_construct.py
  - Fix World.save() with RDF/XML format
  - Fix Thing.subclasses() and Thing.descendants()
  - Fix ontology's update time for ontologies created de novo in Python with Owlready
  - Fix reasoning when asserting new parents with equivalent classes
    
version 2 - 0.12
****************

* New quadstore
* Numerical search (NumS, e.g. all patients with age > 65)
* Nested searches
* Synchronization for multithreading support
* Add Class.inverse_restrictions() and Class.direct_instances()
* Drop PostgresQL support (little interest: more complex and slower than Sqlite3)
* Bugfixes:
  - Fix call to _get_by_storid2
  - Fix rdfs_subclassof in doc
  - Fix FTS triggers
  - Fix boolean in RDFlib / SPARQL
  - Fix bug when destroying an AnnotationProperty

version 2 - 0.13
****************

* Bugfixes:
  - Fix performance regression due to suboptimal index in the quadstore
  - Fix messing up with IRI ending with a /
  - Fix error in World cloning
  - Fix the addition of Thing in class's parent when redefining a class with Thing as the only parent
  - Fix inverse_resctriction()
  - Add error message when creating an existent quadstore

version 2 - 0.14
****************

* UMLS support (owlready2.pymedtermino2 package)
* Can infer object property values when reasoning (thanks W Zimmer)
* New implementation of property values; use INDIRECT_prop to get indirect values
* Support several class property types : some, only, some + only, and direct relation
* Automatically create defined classes via class properties
* Support anonymous individuals, e.g. Thing(0)
* Optimize search() when only the number of returned elements is used
* Optimize FTS search() when using also non-FTS statements
* Can restrict reasoning to a list of ontologies
* Union searches (i.e. default_world.search(...) | default_world.search(...))
* Bugfixes:
  - Fix functional class properties with inheritance
  - Fix dupplicated instance list restrictions when calling close_world(ontology)
  - Fix use of '*' in search
  - Fix synchronization, using contextvars for global variables

version 2 - 0.15
****************

* Can infer data property values when reasoning with Pellet
* Optimize searches with 'type =', 'subclass_of =', or 'is_a =' parameters
* Add Property.range_iri
* Add _case_sensitive parameter to search()
* Add inverse property support in RDFlib support
* Show Java error message when reasoners crash
* Bugfixes:
  - Consider inverse property in get_properties()
  - Fix parsing bug in reasoning with HermiT and infer_property_values = True
  - Namespace prefix support in RDFlib binding
  - Fix dupplicates values when a relation involving a property with inverse is asserted in both directions
  - Better workaround in case of metaclass conflict
  - Fix 'sqlite3.OperationalError: too many SQL variables' in searches with 'type =', 'subclass_of =', or 'is_a =' parameters
    
version 2 - 0.16
****************

* Optimize nested searches
* search(sublclass_of = xxx) now returns xxx itself in the results
* Support "with long_ontology_name as onto" syntax
* In UMLS import, add optional parameters for preventing extraction of attributes, relations, etc
* Support SPARQL INSERT queries
* Optimize Pymedtermino mapping
* Doc for PyMedTermino2
* Bugfixes:
  - Fix 'Cannot release un-acquired lock' error when reasoning on inconsistent ontologies inside a 'with' statement
  - Fix bug when loading a property that refers to another property from a quadstore stored on disk
  - Fix RDF triple suppression with RDFlib when object is a datatype

version 2 - 0.17
****************

* SWRL rule support
* Allows importing UMLS suppressed terms
* Uncache entities when relaoding an ontology
* Bugfixes:
  - Fix PyMedTermino2 installation
  - Fix data property value inferrence with debug = 1
  - Fix sort() in LazyList (thanks fiveop!)
  - Fix World.get() and add World.get_if_loaded()
  - Add appropriate error message when importing UMLS with Python 3.6
  - Fix individuals belonging to multiple, equivalent, classes after reasoning
   
version 2 - 0.18
****************

* Add UNIQUE constraints for preventing dupplicated RDF triples in the quadstore
* Add Individual.INDIRECT_is_a / Individual.INDIRECT_is_instance_of
* Add isinstance_python() (faster than isinstance(), but do not consider equivalent_to relations)
* Bugfixes:
  - Force UTF-8 encoding when importing UMLS
  - Be more tolerant when loading OWL file
   
version 2 - 0.19
****************

* Consider symmetric properties as their own inverse properties
* Update Python objects after basic SPARQL update/delete queries (works on user-defined properties, hierarchical properties (type/subclassof) and equivalence properties)
* Add individual.INVERSE_property
* Add Class.INDIRECT_is_a
* INDIRECT_is_a / INDIRECT_is_instance_of now include class contructs. ancestors() has a 'include_constructs' parameter, which defaults to False.
* Add more aliases for XMLSchema datatypes
* Add is_a property to class constructs
* Add bottomObjectProperty and bottomDataProperty
* Support ReflexiveProperties in individual.INDIRECT_property
* Optimize Thing.subclasses()
* Optimize search() with multiple criteria, including those done by PyMedTermino
* Add support for destroy_entity(SWRL_rule)
* Add support for UMLS "metathesaurus" format in addition to "full" format
* Bugfixes:
  - After reasoning, keep all equivalent classes as parents of individuals (as they may have methods)
  - Fix IndividualPropertyAtom when creating SWRL rule
  - Fix SWRL parser
  - Fix RDF serialization for nested RDF lists
  - Fix removing inverse property (i.e. Prop.inverse = None)
  - Fix datetime parsing for date with time zone or milliseconds
  
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
