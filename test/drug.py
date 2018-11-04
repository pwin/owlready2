# Entire source code for the example of the use case,
# including the creation of the ontology from scratch,
# the five steps described in the paper,
# the creation of the reasoning classes and the execution of the reasoner,
# and the generation of a table similar to table 4 (bottom).

# Import OwlReady

from owlready2 import *


# Create the ontology from scratch

onto = get_ontology("http://test.org/onto.owl")

with onto:
    class Drug(Thing):
        def take(self): print("I took a drug")

    class ActivePrinciple(Thing):
        pass

    class has_for_active_principle(Drug >> ActivePrinciple):
        python_name = "active_principles"

    class Placebo(Drug):
        equivalent_to = [Drug & Not(has_for_active_principle.some(ActivePrinciple))]
        def take(self): print("I took a placebo")

    class SingleActivePrincipleDrug(Drug):
        equivalent_to = [Drug & has_for_active_principle.exactly(1, ActivePrinciple)]
        def take(self): print("I took a drug with a single active principle")

    class DrugAssociation(Drug):
        equivalent_to = [Drug & has_for_active_principle.min(2, ActivePrinciple)]
        def take(self): print("I took a drug with %s active principles" % len(self.active_principles))

acetaminophen   = ActivePrinciple("acetaminophen")
amoxicillin     = ActivePrinciple("amoxicillin")
clavulanic_acid = ActivePrinciple("clavulanic_acid")

AllDifferent([acetaminophen, amoxicillin, clavulanic_acid])

drug1 = Drug(active_principles = [acetaminophen])
drug2 = Drug(active_principles = [amoxicillin, clavulanic_acid])
drug3 = Drug(active_principles = [])

close_world(Drug)

sync_reasoner_pellet()

print("drug2 new Classes:", drug2.__class__)

drug1.take()

drug2.take()

drug3.take()

