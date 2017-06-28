Classes and Individuals (Instances)
===================================

Creating a Class
----------------

A new Class can be created in an ontology by inheriting the owlready2.Thing class.

The ontology class attribute can be used to associate your class to the given ontology. If not specified,
this attribute is inherited from the parent class (in the example below, the parent class is Thing,
which is defined in the 'owl' ontology).

::

   >>> from owlready2 import *
   
   >>> onto = get_ontology("http://test.org/onto.owl")
   
   >>> class Drug(Thing):
   ...     namespace = onto

The namespace Class attribute is used to build the full IRI of the Class,
and can be an ontology or a namespace (see :doc:`namespace`).
The 'with' statement can also be used to provide the ontology (or namespace):

::

   >>> onto = get_ontology("http://test.org/onto.owl")
   
   >>> with onto:
   >>>     class Drug(Thing):
   ...         pass


The .iri attribute of the Class can be used to obtain the full IRI of the class.

::

   >>> print(Drug.iri)
   http://test.org/onto.owl#Drug

.name and .iri attributes are writable and can be modified (this allows to change the IRI of an entity,
which is sometimes called "refactoring").

   
Creating and managing subclasses
--------------------------------

Subclasses can be created by inheriting an ontology class. Multiple inheritance is supported.

::

   >>> class DrugAssociation(Drug): # A drug associating several active principles
   ...     pass

Owlready2 provides the .is_a attribute for getting the list of superclasses (__bases__ can be used, but
with some limits described in :doc:`restriction`). It can also be modified for adding or removing superclasses.

::

   >>> print(DrugAssociation.is_a)
   [onto.Drug]

The .descendants() and .ancestors() Class methods return a set of the descendant and ancestor Classes
(including self, but excluding non-entity classes such as restrictions).

::

   >>> DrugAssociation.ancestors()
   {onto.DrugAssociation, owl.Thing, onto.Drug}


Creating classes dynamically
----------------------------

The 'types' Python module can be used to create classes and subclasses dynamically:

::

   >>> import types

   >>> NewClass = types.new_class("NewClassName", (SuperClass,), kwds = { "namespace" : my_ontology })

   
Creating equivalent classes
---------------------------

The .equivalent_to Class attribute is a list of equivalent classes. It behaves like .is_a.


Creating Individuals
--------------------

Individuals are instances in ontologies. They are created as any other Python instances.
The first parameter is the name (or identifier) of the Individual;
it corresponds to the .name attribute in Owlready2.
If not given, the name if automatically generated from the Class name and a number.

::
   
   >>> my_drug = Drug("my_drug")
   >>> print(my_drug.name)
   my_drug
   >>> print(my_drug.iri)
   http://test.org/onto.owl#my_drug

   >>> unamed_drug = Drug()
   >>> print(unamed_drug.name)
   drug_1

Additional keyword parameters can be given when creating an Individual, and they will be associated to the
corresponding Properties (for more information on Properties, see :doc:`properties`).

::

   my_drug = Drug("my_drug2", namespace = onto, has_for_active_principle = [],...)


The Instances are immediately available in the ontology:

::

   >>> print(onto.drug_1)
   onto.drug_1
   
The .instances() class method can be used to iterate through all Instances of a Class (including its
subclasses). It returns a generator.

::

   >>> for i in Drug.instances(): print(i)

Finally, Individuals also have the .equivalent_to attribute.
   

Mutli-Class Individuals
-----------------------

In ontologies, an Individual can belong to more than one Class. This is supported in Owlready2.

Individuals have a .is_a atribute that behaves similarly to Class .is_a,
but with the Classes of the Individual. In order to create a mutli-Class Individual,
you need to create the Individual as a single-Class Instance first,
and then to add the other Class(ses) in its .is_a attribute:

::
   
   >>> class BloodBasedProduct(Thing):
   ...     ontology = onto
   
   >>> a_blood_based_drug = Drug()
   >>> a_blood_based_drug.is_a.append(BloodBasedProduct)

Owlready2 will automatically create a hidden Class that inherits from both Drug and BloodBasedProduct. This
hidden class is visible in a_blood_based_drug.__class__, but not in a_blood_based_drug.is_a.
   

Destroying entities
-------------------

The destroy_entity() global function can be used to destroy an entity, i.e. to remove it from the ontology and
the quad store.
Owlready2 behaves similarly to Protege4 when destroying entities: all relations involving the destroyed entity
are destroyed too, as well as all class constructs and blank nodes that refer it.

::

   >>> destroy_entity(individual)
   >>> destroy_entity(Klass)
   >>> destroy_entity(Property)
