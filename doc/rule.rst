SWRL rules
==========

SWRL rules can be used to integrate 'if... then...' rules in ontologies.

Note: loading SWRL rules is **only** supported from RDF/XML and NTriples files, but not from OWL/XML files.


Creating SWRL rules
-------------------

The Imp class ("Implies") represent a rule. The easiest way to create a rule is to define it
using a Protégé-like syntax, with the .set_as_rule() method.

The following example use a rule to compute the per-tablet cost of a drug:

::
   
   >>> onto = get_ontology("http://test.org/drug.owl")
   
   >>> with onto:
   ...     class Drug(Thing): pass
   ...     class number_of_tablets(Drug >> int, FunctionalProperty): pass
   ...     class price(Drug >> float, FunctionalProperty): pass
   ...     class price_per_tablet(Drug >> float, FunctionalProperty): pass
   ...
   ...     rule = Imp()
   ...     rule.set_as_rule("""Drug(?d), price(?d, ?p), number_of_tablets(?d, ?n), divide(?r, ?p, ?n) -> price_per_tablet(?d, ?r)""")

   
We can now create a drug, run the reasoner (only Pellet support inferrence on data property value)
and print the result:
::
   
   >>> drug = Drug(number_of_tablets = 10, price = 25.0)
   >>> sync_reasoner_pellet(infer_property_values = True, infer_data_property_values = True)
   >>> drug.price_per_tablet
   2.5


Displaying rules
----------------

The str() Python function can be used to format rules, for example:

::

   >>> str(rule)
   'Drug(?d), price(?d, ?p), number_of_tablets(?d, ?n), divide(?r, ?p, ?n) -> price_per_tablet(?d, ?r)'


   
Modifying rules manually
------------------------

Owlready also allows to access to the inner content of rules. Each rules have a body (= conditions)
and head (= consequences) :

::
   
   >>> rule.body
   [Drug(?d), price(?d, ?p), number_of_tablets(?d, ?n), divide(?r, ?p, ?n)]
   >>> rule.head
   [price_per_tablet(?d, ?r)]

   
Body and head are list of SWRL atoms. The attributes of each atom can be read and modified:

::

   >>> rule.body[0]
   Drug(?d)
   >>> rule.body[0].class_predicate
   drug.Drug
   >>> rule.body[0].arguments
   [?d]

Please refer to SWRL documentation for the list of atoms and their description. One notable difference is that
Owlready always use the "arguments" attributes for accessing arguments, while SWRL uses sometimes "arguments"
and sometimes "argument1" and "argument2".
