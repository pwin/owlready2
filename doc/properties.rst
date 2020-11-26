Properties
==========


Creating a new class of property
--------------------------------

A new property can be created by sublcassing the ObjectProperty or DataProperty class.
The 'domain' and 'range' properties can be used to specify the domain and the range of the property.
Domain and range must be given in list, since OWL allows to specify several domains or ranges for a given
property (if multiple domains or ranges are specified, the domain or range is the intersection of them,
*i.e.* the items in the list are combined with an AND logical operator).

The following example creates two Classes, Drug and Ingredient, and then an ObjectProperty that relates them.

::

   >>> from owlready2 import *
   
   >>> onto = get_ontology("http://test.org/onto.owl")

   >>> with onto:
   ...     class Drug(Thing):
   ...         pass
   ...     class Ingredient(Thing):
   ...         pass
   ...     class has_for_ingredient(ObjectProperty):
   ...         domain    = [Drug]
   ...         range     = [Ingredient]

In addition, the 'domain >> range' syntax can be used when creating property. It replaces the ObjectProperty
or DataProperty parent Class, as follows:

::

   >>> with onto:
   ...     class has_for_ingredient(Drug >> Ingredient):
   ...         pass

   


In addition, the following subclasses of Property are available: FunctionalProperty, InverseFunctionalProperty,
TransitiveProperty, SymmetricProperty, AsymmetricProperty, ReflexiveProperty, IrreflexiveProperty.
They should be used in addition to ObjectProperty or DataProperty (or the 'domain >> range' syntax).


Getting domain and range
------------------------

The .domain and .range attributes of a Property can be used to query its domain and range.
They returns a list.

::

   >>> has_for_ingredient.domain
   [Drug]
   
   >>> has_for_ingredient.range
   [Ingredient]




Creating a relation
-------------------

A relation is a triple (subject, property, object) where property is a Property class, and subject and object
are instances (or literal, such as string or numbers) which are subclasses of the domain and range
defined for the property class.
A relation can be get or set using Python attribute of the subject, the attribute name being the same as
the Property class name: 

::

   >>> my_drug = Drug("my_drug")
   
   >>> acetaminophen = Ingredient("acetaminophen")
   
   >>> my_drug.has_for_ingredient = [acetaminophen]

The attribute contains a list of the subjects:

::

   >>> print(my_drug.has_for_ingredient)
   [onto.acetaminophen]

This list can be modifed *in place* or set to a new value;
Owlready2 will automatically add or delete RDF triples in the quadstore as needed:

::

   >>> codeine = Ingredient("codeine")
   
   >>> my_drug.has_for_ingredient.append(codeine)
   
   >>> print(my_drug.has_for_ingredient)
   [onto.acetaminophen, onto.codeine]
   

Data Property
-------------

Data Properties are Properties with a data type in their range. The following data types
are currently supported by Owlready2:

 * int
 * float
 * bool
 * str (string)
 * owlready2.normstr (normalized string, a single-line string)
 * owlready2.locstr  (localized string, a string with a language associated)
 * datetime.date
 * datetime.time
 * datetime.datetime

Here is an example of a string Data Property:

::

   >>> with onto:
   ...     class has_for_synonym(DataProperty):
   ...         range = [str]

   >>> acetaminophen.has_for_synonym = ["acetaminophen", "paracétamol"]

The 'domain >> range' syntax can also be used:

::

   >>> with onto:
   ...     class has_for_synonym(Thing >> str):
   ...         pass


Inverse Properties
------------------

Two properties are inverse if they express the same meaning, but in a reversed way. 
For example the 'is_ingredient_of' Property is the inverse of the 'has_for_ingredient' Property created above:
saying "a drug A has for ingredient B" is equivalent to "B is ingredient of drug A".

In Owlready2, inverse Properties are defined using the 'inverse_property' attribute.

::

   >>> with onto:
   ...     class is_ingredient_of(ObjectProperty):
   ...         domain           = [Ingredient]
   ...         range            = [Drug]
   ...         inverse_property = has_for_ingredient

Owlready automatically handles Inverse Properties. It will automatically set has_for_ingredient.inverse_property,
and automatically update relations when the inverse relation is modified.

::

   >>> my_drug2 = Drug("my_drug2")
   
   >>> aspirin = Ingredient("aspirin")
   
   >>> my_drug2.has_for_ingredient.append(aspirin)
   
   >>> print(my_drug2.has_for_ingredient)
   [onto.aspirin]
   
   >>> print(aspirin.is_ingredient_of)
   [onto.my_drug2]


   >>> aspirin.is_ingredient_of = []

   >>> print(my_drug2.has_for_ingredient)
   []

.. note::

   This won't work for the drug created previously, because we created the inverse property
   **after** we created the relation between my_drug and acetaminophen.


Functional and Inverse Functional properties
--------------------------------------------

A functional property is a property that has a single value for a given instance. Functional properties
are created by inheriting the FunctionalProperty class.

::

   >>> with onto:
   ...     class has_for_cost(DataProperty, FunctionalProperty): # Each drug has a single cost
   ...         domain    = [Drug]
   ...         range     = [float]
   
   >>> my_drug.has_for_cost = 4.2
   
   >>> print(my_drug.has_for_cost)
   4.2

Contrary to other properties, a functional property returns
a single value instead of a list of values. If no value is defined, they returns None.

::

   >>> print(my_drug2.has_for_cost)
   None

Owlready2 is also able to guess when a Property is functional with respect to a given class.
In the following example, the 'prop' Property is not functional, but Owlready2 guesses that, for Individuals
of Class B, there can be only a single value. Consequently, Owlready2 considers prop as functional
for Class B.

::

   >>> with onto:
   ...     class prop(ObjectProperty): pass
   ...     class A(Thing): pass
   ...     class B(Thing):
   ...         is_a = [ prop.max(1) ]

   >>> A().prop
   []
   >>> B().prop
   None
   
An Inverse Functional Property is a property whose inverse property is functional.
They are created by inheriting the InverseFunctionalProperty class.


Creating a subproperty
----------------------

A subproperty can be created by subclassing a Property class.

::

   >>> with onto:
   ...     class ActivePrinciple(Ingredient):
   ...         pass
   ...     class has_for_active_principle(has_for_ingredient):
   ...         domain    = [Drug]
   ...         range     = [ActivePrinciple]

.. note::
   
   Owlready2 currently does not automatically update parent properties when a child property is defined.
   This might be added in a future version, though.

   
Obtaining indirect relations (considering subproperty, transitivity, etc)
-------------------------------------------------------------------------

Property name can be prefixed by "INDIRECT_" to obtain all indirectly
related entities. It takes into account:

 * transitive, symmetric and reflexive properties,
 * property inheritance (i.e. subproperties),
 * classes of an individual (i.e. values asserted at the class level),
 * class inheritance (i.e. parent classes).
 * equivalences (i.e. equivalent classes, identical "same-as" individuals,...)

::

   >>> with onto:
   ...     class BodyPart(Thing): pass
   ...     class part_of(BodyPart >> BodyPart, TransitiveProperty): pass
   ...     abdomen          = BodyPart("abdomen")
   ...     heart            = BodyPart("heart"           , part_of = [abdomen])
   ...     left_ventricular = BodyPart("left_ventricular", part_of = [heart])
   ...     kidney           = BodyPart("kidney"          , part_of = [abdomen])
    
   ... print(left_ventricular.part_of)
   [heart]
   
   ... print(left_ventricular.INDIRECT_part_of)
   [heart, abdomen]


.. _associating-python-alias-name-to-properties:

Associating Python alias name to Properties
-------------------------------------------

In ontologies, properties are usually given long names, *e.g.* "has_for_ingredient", while in programming
languages like Python, shorter attribute names are more common, *e.g.* "ingredients" (notice also the use
of a plural form, since it is actually a list of several ingredients).

Owlready2 allows to rename Properties with more Pythonic name through the 'python_name' annotation (defined
in the Owlready ontology, file 'owlready2/owlready_ontology.owl' in Owlready2 sources, URI http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl):

::

   >>> has_for_ingredient.python_name = "ingredients"
   
   >>> my_drug3 = Drug()
   
   >>> cetirizin = Ingredient("cetirizin")
   
   >>> my_drug3.ingredients = [cetirizin]
   
.. note::
   
   The Property class is still considered to be called 'has_for_ingredient', for example it is still
   available as 'onto.has_for_ingredient', but not as 'onto.ingredients'.

For more information about the use of annotations, see :doc:`annotations`.

The 'python_name' annotations can also be defined in ontology editors like Protégé, by importing the Owlready
ontology (file 'owlready2/owlready_ontology.owl' in Owlready2 sources, URI http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl).


Getting relation instances
--------------------------

The list of relations that exist for a given property can be obtained by the .get_relations() method.
It returns a generator that yields (subject, object) tuples.

::
   
   >>> onto.has_for_active_principle.get_relations()

.. warning::
   
   The quadstore is not indexed for the .get_relations() method. Thus, it can be slow on huge ontologies.
