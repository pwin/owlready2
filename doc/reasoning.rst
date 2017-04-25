Reasoning
=========

OWL reasoners can be used to check the *consistency* of an ontology, and to deduce new fact in the ontology,
typically be *reclassing* Individuals to new Classes, and Classes to new superclasses,
depending on their relations.

Several OWL reasoners exist; Owlready2 includes a modified version of the `HermiT reasoner <http://hermit-reasoner.com/>`_,
developed by the department of Computer Science of the University of Oxford, and released under the LGPL licence.
HermiT is written in Java, and thus you need a Java Vitual Machine to perform reasoning in Owlready2.

Setting up everything
---------------------

Before performing reasoning, you need to create all Classes, Properties and Instances, and
to ensure that restrictions and disjointnesses / differences have been defined too.

Here is an example creating a 'reasoning-ready' ontology:

::

   >>> from owlready2 import *
   
   >>> onto = Ontology("http://test.org/onto.owl")
   
   >>> with onto:
   ...     class Drug(Thing):
   ...         def take(self): print("I took a drug")
   
   ...     class ActivePrinciple(Thing):
   ...         pass
   
   ...     class has_for_active_principle(Drug >> ActivePrinciple):
   ...         python_name = "active_principles"

   ...     class Placebo(Drug):
   ...         equivalent_to = [Drug & Not(has_for_active_principle.some(ActivePrinciple))]
   ...         def take(self): print("I took a placebo")

   ...     class SingleActivePrincipleDrug(Drug):
   ...         equivalent_to = [Drug & has_for_active_principle.exactly(1, ActivePrinciple)]
   ...         def take(self): print("I took a drug with a single active principle")
   
   ...     class DrugAssociation(Drug):
   ...         equivalent_to = [Drug & has_for_active_principle.min(2, ActivePrinciple)]
   ...         def take(self): print("I took a drug with %s active principles" % len(self.active_principles))
   
   >>> acetaminophen   = ActivePrinciple("acetaminophen")
   >>> amoxicillin     = ActivePrinciple("amoxicillin")
   >>> clavulanic_acid = ActivePrinciple("clavulanic_acid")
   
   >>> AllDifferent(acetaminophen, amoxicillin, clavulanic_acid)

   >>> drug1 = Drug(active_principles = [acetaminophen])
   >>> drug2 = Drug(active_principles = [amoxicillin, clavulanic_acid])
   >>> drug3 = Drug(active_principles = [])
   
   >>> close_world(Drug)


Running the reasoner
--------------------

The reasoner is simply run by calling the sync_reasoner() global function:

::

   >>> sync_reasoner()

By default, sync_reasoner() places all inferred facts in a special ontology, 'http://inferrences/'.
You can control in which ontology the inferred facts are placed using the 'with ontology' statement
(remember, all triples asserted inside a 'with ontology' statement go inside this ontology).
For example, for placing all inferred facts in the 'onto' ontology:

::

   >>> with onto:
   ...     sync_reasoner()


This allows saving the ontology with the inferred facts (using onto.save() as usual).

Results of the automatic classification
---------------------------------------

Owlready automatically gets the results of the reasoning from HermiT and reclassifies Individuals and Classes,
*i.e* Owlready changes the Classes of Individuals and the superclasses of Classes.

::

   >>> print("drug2 new Classes:", drug2.__class__)
   drug2 new Classes: onto.DrugAssociation
   
   >>> drug1.take()
   I took a drug with a single active principle

   >>> drug2.take()
   I took a drug with 2 active principles

   >>> drug3.take()
   I took a placebo

In this example, drug1, drug2 and drug3 Classes have changed!
The reasoner *deduced* that drug2 is an Association Drug, and that drug3 is a Placebo.

Also notice how the example combines automatic classification of OWL Classes with polymorphism on Python Classes.
