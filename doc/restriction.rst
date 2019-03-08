Class constructs, restrictions and logical operators
====================================================

Restrictions are special types of Classes in ontology.

Restrictions on a Property
--------------------------

::

   >>> from owlready2 import *
   
   >>> onto = get_ontology("http://test.org/onto.owl")
   
   >>> with onto:
   ...     class Drug(Thing):
   ...         pass
   ...     class ActivePrinciple(Thing):
   ...         pass
   ...     class has_for_active_principle(Drug >> ActivePrinciple):
   ...         pass


For example, a non-Placebo Drug is a Drug with an Active Principle:

::
   
   >>> class NonPlaceboDrug(Drug):
   ...     equivalent_to = [Drug & has_for_active_principle.some(ActivePrinciple)]

 
And a Placebo is a Drug with no Active Principle:

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
 * has_self : Property.has_self(Boolean value)

When defining classes, restrictions can be used in class definition (i.e. 'equivalent_to ='),
but also as superclasses, using 'is_a =', as in the following example:

::

   >>> with onto:
   ...     class MyClass(Thing):
   ...         is_a = [my_property.some(Value)]
   
In addition, restrictions can be added to existing classes by adding them to .is_a or .equivalent_to,
as in the two following examples:

::

   >>> MyClass.is_a.append(my_property.some(Value))

   >>> MyClass.equivalent_to.append(my_property.some(Value))


Restrictions can be modified *in place* (Owlready2 updates the quadstore automatically), using the
following attributes: .property, .type (SOME, ONLY, MIN, MAX, EXACTLY or VALUE), .cardinality
and .value (a Class, an Individual, a class contruct or another restriction).

Finally, the Inverse(Property) construct can be used as the inverse of a given Property.


Restrictions as class properties
--------------------------------

Owlready allows to access restriction as class properties.

By default, existential restrictions (i.e. SOME restrictions and VALUES restrictions) can be accessed
as if they were class properties in Owlready. For example:

::
   
   >>> NonPlaceboDrug.has_for_active_principle
   [onto.ActivePrinciple]

These class attributes can also be modified (e.g. NonPlaceboDrug.has_for_active_principle.append(...) ).

The .class_property_type attribute of Properties allows to indicate how to handle class properties.
It is a list made of the following values:

 * "some": handle class properties as existential restrictions (i.e. SOME restrictions and VALUES restrictions).
 * "only": handle class properties as universal restrictions (i.e. ONLY restrictions).
 * "relation": handle class properties as relations (i.e. simple RDF triple, as in Linked Data).

When more than one value is specified, all the specified method are used when defining the value of the property
for a class.
 
The .class_property_type attribute corresponds to the "http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#class_property_type"
annotation.

The set_default_class_property_type(types) global function allows to set the default type of class property used,
when no type is specified for a given property. The default value is ["some"].


Restrictions as class properties in defined classes
---------------------------------------------------

Defined classes are classes that are defined by an "equivalent to" relation, such as Placebo and NonPlaceboDrug above.

The .defined_class Boolean attribute can be used to mark a class as "defined".
It corresponds to the "http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#defined_class" annotation.

When a class is marked as "defined", Owlready automatically generates an equivalent_to formula, taking into account
the class parents and the class properties.

The following program shows an example. It creates a drug ontology, with a Drug class and several HealthConditions.
In addition, two properties are created, for indiciations and contraindications. Here, we choose to manage indications
with SOME restrictions and contraindication with ONLY restrictions.

Then, the program creates two subclasses of Drug: Antalgic and Aspirin. Thoses subclasses are marked as defined (with
defined_class = True), and their properties are defined also.

::

   >>> onto2 = get_ontology("http://test.org/onto2.owl")
   
   >>> with onto2:
   ...     class Drug(Thing): pass
   ...     class ActivePrinciple(Thing): pass
   ...     class has_for_active_principle(Drug >> ActivePrinciple): pass
      
   ...     class HeathCondition(Thing): pass
   ...     class Pain(HeathCondition): pass
   ...     class ModeratePain(Pain): pass
   ...     class CardiacDisorder(HeathCondition): pass
   ...     class Hypertension(CardiacDisorder): pass
      
   ...     class Pregnancy(HeathCondition): pass
   ...     class Child(HeathCondition): pass
   ...     class Bleeding(HeathCondition): pass
      
   ...     class has_for_indications      (Drug >> HeathCondition): class_property_type = ["some"]
   ...     class has_for_contraindications(Drug >> HeathCondition): class_property_type = ["only"]
  
   ...     class Antalgic(Drug): 
   ...         defined_class = True
   ...         has_for_indications = [Pain]
   ...         has_for_contraindications = [Pregnancy, Child, Bleeding]
        
   ...     class Aspirin(Antalgic):
   ...         defined_class = True
   ...         has_for_indications = [ModeratePain]
   ...         has_for_contraindications = [Pregnancy, Bleeding]


Owlready automatically produces the appropriate equivalent_to formula, as we can verify:

::

   >>> print(Antalgic.equivalent_to)
   [onto.Drug
   & onto.has_for_indications.some(onto.Pain)
   & onto.has_for_contraindications.only(onto.Child | onto.Pregnancy | onto.Bleeding)]
   
   >>> print(Aspirin.equivalent_to)
   [onto.Antalgic
   & onto.has_for_indications.some(onto.ModeratePain)
   & onto.has_for_contraindications.only(onto.Pregnancy | onto.Bleeding)]


Notice that this mapping between class properties and definition is bidirectional: one can also use it to access
an existing definition as class properties. The following example illustrates that:

::

   >>> with onto2:
   ...     class Antihypertensive(Drug):
   ...         equivalent_to = [Drug
   ...                          & has_for_indications.some(Hypertension)
   ...                          &has_for_contraindications.only(Pregnancy)]
   
   >>> print(Antihypertensive.has_for_indications)
   [onto.Hypertension]
   
   >>> print(Antihypertensive.has_for_contraindications)
   [onto.Pregnancy]


   
Logical operators (intersection, union and complement)
------------------------------------------------------

Owlready provides the following operators between Classes
(normal Classes but also class constructs and restrictions):

 * '&' : And operator (intersection). For example: Class1 & Class2.
   It can also be written: And([Class1, Class2])
 * '|' : Or operator (union). For example: Class1 | Class2.
   It can also be written: Or([Class1, Class2])
 * Not() : Not operator (negation or complement). For example: Not(Class1)

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

