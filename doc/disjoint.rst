Disjointness, open and local closed world reasoning
===================================================

By default, OWL considers the world as 'open', *i.e.* everything that is not stated in the ontology is
not 'false' but 'possible' (this is known as *open world assumption*).
Therfore, things and facts that are 'false' or 'impossible' must be clearly stated as so in the ontology.

Disjoint Classes
----------------

Two (or more) Classes are disjoint if there is no Individual belonging to all these Classes (remember that,
contrary to Python instances, an Individual can have several Classes, see :doc:`class`).

A Classes disjointness is created with the AllDisjoint() function, which takes a list of Classes
as parameter. In the example below, we have two Classes, Drug and ActivePrinciple, and we assert that they
are disjoint (yes, we need to specify that explicitely -- sometimes ontologies seem a little dumb!).

::

   >>> from owlready2 import *
   
   >>> onto = get_ontology("http://test.org/onto.owl")
   
   >>> with onto:
   ...     class Drug(Thing):
   ...         pass
   ...     class ActivePrinciple(Thing):
   ...         pass
   ...     AllDisjoint([Drug, ActivePrinciple])


Disjoint Properties
-------------------

OWL also introduces Disjoint Properties.
Disjoint Properties can also be created using AllDisjoint().


Different Individuals
---------------------

Two Individuals are different if they are distinct. In OWL, two Individuals might be considered as being actually
the same, single, Individual, unless they are stated different.
Difference is to Individuals what disjointness is to Classes.

The following example creates two active principles and asserts that they are different (yes, we also need
to state explicitely that acetaminophen and aspirin are not the same!)

::

   >>> acetaminophen = ActivePrinciple("acetaminophen")
   >>> aspirin       = ActivePrinciple("aspirin")
   
   >>> AllDifferent([acetaminophen, aspirin])

.. note::

   In Owlready2, AllDifferent is actually the same function as AllDisjoint -- the exact meaning depends on the
   parameters (AllDisjoint if you provide Classes, AllDifferent if you provide Instances,
   and disjoint Properties if you provide Properties).
   
   
Querying and modifying disjoints
--------------------------------

The .disjoints() method returns a generator for iterating over AllDisjoint constructs involving the given Class
or Property. For Individuals, .differents() behaves similarly.

::

   >>> for d in Drug.disjoints():
   ...     print(d.entities)
   [onto.Drug, onto.ActivePrinciple]

The 'entities' attribute of an AllDisjoint is writable, so you can modify the AllDisjoint construct by adding
or removing entities.

OWL also provides the 'disjointWith' and 'propertyDisjointWith' relations for pairwise disjoints (involving
only two elements). Owlready2 exposes **all** disjoints as AllDisjoints, *including* those declared with 
the 'disjointWith' or 'propertyDisjointWith' relations. In the quad store (or when saving OWL files),
disjoints involving 2 entities are defined using the 'disjointWith' or 'propertyDisjointWith' relations,
while others are defined using AllDisjoint or AllDifferent.


Closing Individuals
-------------------

The open world assumption also implies that the properties of a given Individual are not limited to the
ones that are explicitely stated. For example, if you create a Drug Individual with a single Active
Principle, it does not mean that it has *only* a single Active Principle.

::

   >>> with onto:
   ...     class has_for_active_principle(Drug >> ActivePrinciple): pass
   
   >>> my_acetaminophen_drug = Drug(has_for_active_principle = [acetaminophen])

In the example above, 'my_acetaminophen_drug' has an acetaminophen Active Principle (this fact is true) and it
may have other Active Principle(s) (this fact is possible).

If you want 'my_acetaminophen_drug' to be a Drug with acetaminophen and no other Active Principle, you have to
state it explicitely using a restriction (see :doc:`restriction`):

::

   >>> my_acetaminophen_drug.is_a.append(has_for_active_principle.only(OneOf([acetaminophen])))

Notice that we used OneOf() to 'turn' the acetaminophen Individual into a Class that we can use in the restriction.

You'll quickly find that the open world assumption often leads to tedious and long lists
of AllDifference and Restrictions. Hopefully, Owlready2 provides the close_world() function for automatically
'closing' an Individual. close_world() will automatically add ONLY restrictions as needed; it accepts an
optional parameter: a list of the Properties to 'close' (defaults to all Properties whose domain is
compatible with the Individual).

::

   >>> close_world(my_acetaminophen_drug)


Closing Classes
---------------

close_world() also accepts a Class. In this case, it closes the Class, its subclasses, and all their Individuals.

By default, when close_world() is not called, the ontology performs **open world reasoning**.
By selecting the Classes and the Individuals you want to 'close',
the close_world() function enables **local closed world reasoning** with OWL.

Closing an ontology
-------------------

Finally, close_world() also accepts an ontology. In this case, it closes all the Classes defined in the ontology.
This corresponds to fully **closed world reasoning**.

