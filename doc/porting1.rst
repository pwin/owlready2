Differences between Owlready version 1 and 2
============================================

This section summarizes the major differences between Owlready version 1 and 2.


Creation of Classes, Properties and Individuals
-----------------------------------------------

The 'ontology' parameters is now called 'namespace' in Owlready2. It accepts a namespace or an ontology.

Owlready 1:

::

   >>> class Drug(Thing):
   ...     ontology = onto

Owlready 2:

::

   >>> class Drug(Thing):
   ...     namespace = onto


Generated Individual names
--------------------------

Owlready 1 permitted to generate dynamically Individual names, depending on their relations.
This is no longer possible in Owlready 2, due to the different architecture.


Functional properties
---------------------

In Owlready 1, functional properties had default values depending on their range. For example,
if the range was float, the default value was 0.0.

In Owlready 2, functional properties always returns None if not relation has been asserted.


Creation of restrictions
------------------------

In Owlready 1, restrictions were created by calling the property:

::
   
   >> Property(SOME, Range_Class)
   >> Property(ONLY, Range_Class)
   >> Property(MIN, cardinality, Range_Class)
   >> Property(MAX, cardinality, Range_Class)
   >> Property(EXACTLY, cardinality, Range_Class)
   >> Property(VALUE, Range_Instance)

In Owlready 2, they are created by calling the .some(), .only(), .min(), .max(), .exactly() and .value()
methods of the Property:

::
   
   >> Property.some(Range_Class)
   >> Property.only(Range_Class)
   >> Property.min(cardinality, Range_Class)
   >> Property.max(cardinality, Range_Class)
   >> Property.exactly(cardinality, Range_Class)
   >> Property.value(Range_Individual)

   
Logical operators and 'One of' constructs
-----------------------------------------

In Owlready 1, the negation was called 'NOT()'.
In Owlready 2, the negation is now called 'Not()'.

In Owlready 1, the logical operators (Or and And) and the one_of construct expect several values as parameters.

::

   >>> Or(ClassA, ClassB,...)
   
In Owlready 2, the logical operators (Or and And) and the OneOf construct expect a list of values.

::

   >>> Or([ClassA, ClassB,...])


Reasoning
---------

In Owlready 1, the reasoner was executed by calling ontology.sync_reasoner().

::

   >>> onto.sync_reasoner()

In Owlready 2, the reasoner is executed by calling sync_reasoner(). The reasoning can involve several ontologies
(all those that have been loaded). sync_reasoner() actually acts on a World (see :doc:`world`).

::

   >>> sync_reasoner()


Annotations
-----------

In Owlready 1, annotations were available through the ANNOTATIONS pseudo-dictionary.

::

   >>> ANNOTATIONS[Drug]["label"] = "Label for Class Drug"

   

In Owlready 2, annotations are available as normal attributes.

::

   >>> Drug.label = "Label for Class Drug"

