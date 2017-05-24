Class constructs, restrictions and logical operators
====================================================

Restrictions are special types of Classes in ontology.

Restrictions on a Property
--------------------------

::

   >>> from owlready2 import *
   
   >>> onto = Ontology("http://test.org/onto.owl")
   
   >>> with onto:
   ...     class Drug(Thing):
   ...         pass
   ...     class ActivePrinciple(Thing):
   ...         pass
   ...     class has_for_active_principle(Drug >> ActivePrinciple):
   ...         pass

For example, a Placebo is a Drug with no Active Principle:

::

   >>> class Placebo(Drug):
   ...     equivalent_to = [Drug & Not(has_for_active_principle.some(ActivePrinciple))]

In the example above, 'has_for_active_principle.some(ActivePrinciple)' is the Class of all
objects that have at least one Active Principle.
The Not() function returns the negation (or complement) of a Class.
The & operator returns the intersection of two Classes.

Another example, an Association Drug is a Drug that associates two or more Active Principle:

::

   >>> with onto:
   ...     class DrugAssociation(Drug):
   ...         equivalent_to = [Drug & has_for_active_principle.min(2, ActivePrinciple)]

Owlready provides the following types of restrictions (they have the same names than in Protégé):

 * some : Property.some(Range_Class)
 * only : Property.only(Range_Class)
 * min : Property.min(cardinality, Range_Class)
 * max : Property.max(cardinality, Range_Class)
 * exactly : Property.exactly(cardinality, Range_Class)
 * value : Property.value(Range_Individual / Literal value)

In addition, the Inverse(Property) construct can be used as the inverse of a given Property.

Restrictions can be modified *in place* (Owlready2 updates the quadstore automatically), using the
following attributes: .property, .type (SOME, ONLY, MIN, MAX, EXACTLY or VALUE), .cardinality
and .value (a Class, an Individual, a class contruct or another restriction).


Logical operators (intersection, union and complement)
------------------------------------------------------

Owlready provides the following operators between Classes
(normal Classes but also class constructs and restrictions):

 * '&' : and operator (intersection). For example: Class1 & Class2
 * '|' : or operator (union). For example: Class1 | Class2
 * Not() : not operator (negation or complement). For example: Not(Class1)

The Classes used with logical operators can be normal Classes (inheriting from Thing), restrictions or
other logical operators. 

Intersections, unions and complements can be modified *in place* using
the .Classes (intersections and unions) or .Class (complement) attributes.


One-Of constructs
-----------------

In ontologies, a 'One Of' statement is used for defining a Class by extension, *i.e.* by listing its Instances
rather than by defining its properties.

::
   
   >>> with onto:
   ...     class DrugForm(Thing):
   ...         pass
   
   >>> tablet     = DrugForm()
   >>> capsule    = DrugForm()
   >>> injectable = DrugForm()
   >>> pomade     = DrugForm()
   
   # Assert that there is only four possible drug forms
   >>> DrugForm.is_a.append(OneOf([tablet, capsule, injectable, pomade]))
   
The construct be modified *in place* using the .instances attribute.


Inverse-of constructs
---------------------

Inverse-of constructs produces the inverse of a property, without creating a new property.

::
   
   Inverse(has_for_active_principle)
   
The construct be modified *in place* using the .property attribute.


ConstrainedDatatype
-------------------

A constrained datatype is a data whose value is restricted, for example an integer between 0 and 20.

The global function ConstrainedDatatype() create a constrained datatype from a base datatype,
and one or more facets:

* length
* min_length
* max_length
* pattern
* white_space
* max_inclusive
* max_exclusive
* min_inclusive
* min_exclusive
* total_digits
* fraction_digits

For example:

::

   ConstrainedDatatype(int, min_inclusive = 0, max_inclusive = 20)
   ConstrainedDatatype(str, max_length = 100)
  

Property chain
--------------

Property chain allows to chain two properties (this is sometimes noted prop1 o prop2).
The PropertyChain() function allows to create a new property chain from a list of properties:

::
   
   PropertyChain([prop1, prop2])
   
The construct be modified *in place* using the .properties attribute.
