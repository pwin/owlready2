PyMedTermino2
=============

Introduction
************

PyMedTermino (Medical Terminologies for Python) is a Python module for easy access to the main medical
terminologies in Python. The following terminologies are supported:

 - All terminologies in UMLS, including:
   - SNOMED CT
   - ICD10
   - MedDRA
 - ICD10 in French (CIM10)

The main features of PyMedTermino are:

 - A single API for accessing all terminologies
 - Optimized full-text search
 - Access to terms, synonyms and translations
 - Manage concepts and relations between concepts
 - Mappings between terminologies (e.g. via UMLS or manual mapping)

PyMedTermino has been designed for "batch" access to terminologies; it is *not* a terminology browser
(althought it can be used to write a terminology browser in Python).

The first version of PyMedTermino was an independent Python package.
The second version (PyMedTermino2) is integrated with Owlready2, and store medical terminologies as OWL ontlogies.
This allows relating medical terms from terminologies with user created concepts.

UMLS data is not included, but can be downloaded for free (see Intallation below). Contrary to PyMedTermino1,
PyMedTermino2 do not require a connection to an external UMLS database: it imports UMLS data in its own local
database, automatically.

If you use PyMedTermino in scientific works, **please cite the following article**:

   **Lamy JB**, Venot A, Duclos C.
   `PyMedTermino: an open-source generic API for advanced terminology services. <http://ebooks.iospress.nl/volumearticle/39485>`_
   **Studies in health technology and informatics 2015**;210:924-928


Installation
************

#. Install Python 3.7 and Owlready2 (if not already done).
   **PyMedTermino2 requires Python >= 3.7 for importing UMLS** (However, after importing the data in the quadstore, it can be used with Python 3.6 if you really need to).

#. After registration with NLM, download UMLS data (Warning: some restriction may apply depending on country; see UMLS licence and its SNOMED CT appendix):

   - https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html

     PyMedTermino2 suports both the "Full UMLS Release Files" and the "UMLS Metathesaurus Files", but the latter
     is recommended since it is faster to uncompress.
     E.g. download “umls-2019AA-metathesaurus.zip”. Do not unzip it!

#. Import UMLS data in Python as follows:

>>> from owlready2 import *
>>> from owlready2.pymedtermino2 import *
>>> from owlready2.pymedtermino2.umls import *
>>> default_world.set_backend(filename = "pym.sqlite3")
>>> import_umls("umls-2019AA-metathesaurus.zip", terminologies = ["ICD10", "SNOMEDCT_US", "CUI"])
>>> default_world.save()

were:
 - "pym.sqlite3" is the quadstore file in which the data are stored.
 - ["ICD10", "SNOMEDCT_US", "CUI"] are the terminologies imported (valid codes are UMLS code, plus "CUI" for CUI).
   If the 'terminologies' parameter is missing, all terminologies are imported.

To import also suppressed/deprecated concept, add the following parameter: remove_suppressed = "".

The importation can take several minutes or hours, depending on the number of terminologies imported.

4. Import French ICD10 (optional):

>>> from owlready2.pymedtermino2.icd10_french import *
>>> import_icd10_french()
>>> default_world.save()

   
SNOMED CT
*********

Loading
-------

To load SNOMED CT in Python:

>>> from owlready2 import *
>>> default_world.set_backend(filename = "pym.sqlite3")
>>> PYM = get_ontology("http://PYM/").load()
>>> SNOMEDCT_US = PYM["SNOMEDCT_US"]

Here, 'PYM' is the abbreviation for PyMedTermino. PYM can be indiced with a terminology code, to obtain
the corresponding terminology object (here, SNOMEDCT_US).


Concepts
--------

The SNOMEDCT_US object represents the SNOMED CT terminology. A SNOMED CT concept can be obtained from its
code (in the following example, 302509004, which is the code for the heart concept) by indexing this
object with curly brackets:

>>> concept = SNOMEDCT_US[302509004]
>>> concept
SNOMEDCT_US["302509004"] # Entire heart

The has_concept() method can be used to verify if a code corresponds to a concept or not:

>>> SNOMEDCT_US.has_concept("invalid_code")
False

Each concept has a code, available as the name of the entity, and a preferred term, available as the label RDF annotation:

>>> concept.name
'302509004'
>>> concept.label
['Entire heart']
>>> concept.label.first()
'Entire heart'

SNOMED CT also proposes synonym terms, available via the 'synonyms' annotation :

>>> concept.synonyms
['Entire heart (body structure)']

The 'terminology' attribute contains the terminology of the concept:

>>> concept.terminology
PYM["SNOMEDCT_US"] # US Edition of SNOMED CT


Full-text search
----------------

The search() method allows full-text search in SNOMED CT terms (including synonyms):

>>> SNOMEDCT_US.search("Cardiac structure")
[SNOMEDCT_US["24964005"] # Cardiac conducting system structure
, SNOMEDCT_US["10746000"] # Cardiac septum structure
...]

Full-text search uses the FTS engine of SQLite, it is thus possible to use its functionalities.
For example, for searching for all words beginning by a given prefix:

>>> SNOMEDCT_US.search("osteo*")
[SNOMEDCT_US["66467005"] # Osteochondromatosis
, SNOMEDCT_US["40970001"] # Chronic osteomyelitis
...]

Is-a relations: parent and child concepts
-----------------------------------------

The “parents” and “children” attributes return the list of parent and child concepts (i.e. the concepts
with is-a relations):

>>> concept.parents
[SNOMEDCT_US["116004006"] # Entire hollow viscus
, SNOMEDCT_US["187639008"] # Entire thoracic viscus
, SNOMEDCT_US["80891009"] # Heart structure
]
>>> concept.children
[SNOMEDCT_US["195591003"] # Entire transplanted heart
]

The ancestor_concepts() and descendant_concepts() methods return all the ancestor concepts
(parents, parents of parents, and so on) and the descendant concepts (children, children of children, and so on) :

>>> concept.ancestor_concepts()
[SNOMEDCT_US["302509004"] # Entire heart
, SNOMEDCT_US["116004006"] # Entire hollow viscus
, SNOMEDCT_US["118760003"] # Entire viscus
...]
>>> concept.descendant_concepts()
[SNOMEDCT_US["302509004"] # Entire heart
, SNOMEDCT_US["195591003"] # Entire transplanted heart
]

Both methods remove dupplicates automatically. They also include the starting concept in the results.
If you do not want it, use the 'include_self' parameter:

>>> concept.descendant_concepts(include_self = False)
[SNOMEDCT_US["195591003"] # Entire transplanted heart
]

PyMedTermino2 concepts are OWL and Python classes. As a consequence, you can use the Python issubclass() function
to test whether a concept is a descendant of another:

>>> issubclass(concept, SNOMEDCT_US["272625005"])
True


Part-of relations
-----------------

“part_of” and “has_part” attributes provide access to subparts or superpart of the concept:

>>> concept.part_of
[SNOMEDCT_US["362010009"] # Entire heart AND pericardium
]
>>> concept.has_part
[SNOMEDCT_US["244258000"] # Entire marginal branch of right coronary artery
, SNOMEDCT_US["261405004"] # Entire atrium
, SNOMEDCT_US["244378006"] # Lateral atrioventricular leaflet
...]


Other relations
---------------

The “get_class_properties” method returns the set of relations available for a given concept. Is-a relations
are never included in this list, and are handled with the “parents” and “children” attributes previously
seen, however part-of relations are included.

>>> concept = SNOMEDCT_US["3424008"]
>>> concept
SNOMEDCT_US["3424008"] # Tachycardia
>>> concept.get_class_properties()
{PYM.mapped_to, PYM.case_significance_id, PYM.unifieds, PYM.terminology, rdf-schema.label, PYM.subset_member, PYM.definition_status_id, PYM.synonyms, PYM.has_interpretation, PYM.active, PYM.interprets, PYM.effective_time, PYM.ctv3id, PYM.groups, PYM.has_finding_site, PYM.type_id}

Each relation corresponds to an attribute in the concept. The name of the attribute is the part after the '.',
e.g. for 'PYM.interprets' the name is 'interprets'.
The attribute's value is a list with the corresponding values:

>>> concept.has_finding_site
[SNOMEDCT_US["24964005"] # Cardiac conducting system structure
]
>>> concept.interprets
[SNOMEDCT_US["364075005"] # Heart rate
]


Relation groups
---------------

In SNOMED CT, relations can be grouped together. The “groups” attribute returns the list of groups. It is
then possible to access to the group's relation.

>>> concept = SNOMEDCT_US["186675001"]
>>> concept
SNOMEDCT_US["186675001"] # Viral pharyngoconjunctivitis
>>> concept.groups
[<Group 453170_0> # mapped_to=Viral conjunctivitis, unspecified
, <Group 453170_3> # has_causative_agent=Virus ; has_associated_morphology=Inflammation ; has_finding_site=Pharyngeal structure ; has_pathological_process=Infectious process
, <Group 453170_4> # has_causative_agent=Virus ; has_associated_morphology=Inflammation ; has_finding_site=Conjunctival structure ; has_pathological_process=Infectious process
>>> concept.groups[2].get_class_properties()
{PYM.has_causative_agent, PYM.has_associated_morphology, PYM.has_finding_site, PYM.has_pathological_process}
>>> concept.groups[2].has_finding_site
[SNOMEDCT_US["29445007"] # Conjunctival structure
]
>>> concept.groups[2].has_associated_morphology
[SNOMEDCT_US["23583003"] # Inflammation
]


Iterating over SNOMED CT
------------------------

To obtain the terminology's first level concepts (i.e. the root concepts), use the children attribute of the terminology:

>>> SNOMEDCT_US.children
[SNOMEDCT_US["138875005"] # SNOMED CT Concept
]

The descendant_concepts() method returns all concepts in SNOMED CT.

>>> for concept in SNOMEDCT_US.descendant_concepts(): [...]



ICD10
*****

Loading modules
---------------

To load SNOMED CT in Python:

>>> from owlready2 import *
>>> default_world.set_backend(filename = "pym.sqlite3")
>>> PYM = get_ontology("http://PYM/").load()
>>> ICD10 = PYM["ICD10"]

Or, for the French version (if you imported it during installation):

>>> CIM10 = PYM["CIM10"]

CIM10 can be used as ICD10.


Concepts
--------

The ICD10 object allows to access to ICD10 concepts. This object behaves similarly to the SNOMED CT
terminology previously described (see `SNOMED CT`_).

>>> ICD10["E10"]
ICD10["E10"] # Insulin-dependent diabetes mellitus
>>> ICD10["E10"].parents
[ICD10["E10-E14.9"] # Diabetes mellitus
]
>>> ICD10["E10"].ancestor_concepts()
[ICD10["E10"] # Insulin-dependent diabetes mellitus
, ICD10["E10-E14.9"] # Diabetes mellitus
, ICD10["E00-E90.9"] # Endocrine, nutritional and metabolic diseases
]

ICD10 being monoaxial, the parents list always includes at most one parent.


UMLS
****

Loading modules
---------------

>>> from owlready2 import *
>>> default_world.set_backend(filename = "pym.sqlite3")
>>> PYM = get_ontology("http://PYM/").load()
>>> CUI = PYM["CUI"]

UMLS concepts (CUI)
-------------------

In UMLS, CUI correspond to concepts: a given concept gathers equivalent terms or codes from various
terminologies.

CUI can be accessed with the UMLS_CUI terminology:

>>> concept = CUI["C0085580"]
>>> concept
CUI["C0085580"] # Essential hypertension
>>> concept.name
'C0085580'
>>> concept.label
['Essential hypertension']
>>> concept.synonyms
['Essential (primary) hypertension', 'Idiopathic hypertension', 'Primary hypertension', 'Systemic primary arterial hypertension', 'Essential hypertension (disorder)']

Relations of CUI are handled in the same way than for SNOMED CT (see above), for example:

>>> concept.get_class_properties()
{PYM.originals, PYM.terminology, rdf-schema.label, PYM.synonyms}


Relation with source terminologies
----------------------------------

The originals attribute of a CUI concept contains the corresponding concepts in UMLS sources terminologies:

>>> concept.originals
[SNOMEDCT_US["59621000"] # Essential hypertension
, CIM10["I10"] # Hypertension essentielle (primitive)
, ICD10["I10"] # Essential (primary) hypertension
]

The inverse attribute is unifieds. For concepts in the source terminologies, it contains the corresponding CUI
(some concepts may be associated with several CUI):

>>> ICD10["I10"].unifieds
[CUI["C0085580"] # Essential hypertension
]


Mapping between terminologies
-----------------------------

PyMedTermino uses the '>>' operator for mapping from a terminology to another.
For example, you can map a SNOMED CT concept to UMLS as follows:

>>> SNOMEDCT_US[186675001]
SNOMEDCT_US["186675001"] # Viral pharyngoconjunctivitis
>>> SNOMEDCT_US[186675001] >> CUI
Concepts([
  CUI["C0542430"] # Viral pharyngoconjunctivitis
])

Or you can map a UMLS concept to ICD10:

>>> CUI["C0542430"] >> ICD10
Concepts([
  ICD10["B30.2"] # Viral pharyngoconjunctivitis
])

Finally, you can map directly from a terminology in UMLS to another terminology in UMLS,
for example from SNOMED CT to ICD10:

>>> SNOMEDCT_US[186675001] >> ICD10
Concepts([
  ICD10["B30.9"] # Viral conjunctivitis, unspecified
])

The direct mapping considers 'mapped_to' relations available first, and default to mapping using CUI.



Set of concepts
***************

The Concepts class implements a set of concepts.

>>> concepts = PYM.Concepts([ ICD10["E10"], ICD10["E11"], ICD10["E12"] ])
>>> concepts
Concepts([
  ICD10["E10"] # Insulin-dependent diabetes mellitus
, ICD10["E12"] # Malnutrition-related diabetes mellitus
, ICD10["E11"] # Non-insulin-dependent diabetes mellitus
])

Concepts class inherits from Python's set and supports all its methods (such as add(), remove(), etc).

Concepts can be used to map several concepts simultaneously, using the '>>' operator, for example:

>>> PYM.Concepts([ ICD10["E10"], ICD10["E11"], ICD10["E12"] ]) >> SNOMEDCT_US
Concepts([
  SNOMEDCT_US["44054006"] # Type 2 diabetes mellitus
, SNOMEDCT_US["46635009"] # Type 1 diabetes mellitus
, SNOMEDCT_US["75524006"] # Malnutrition related diabetes mellitus
])

In addition, the Concepts class also provides advanced terminology-oriented methods:

* keep_most_generic() keeps only the most generic concepts in the set (i.e. it removes all concepts that are a descendant of another concept in the set)
* keep_most_specific() keeps only the most specific concepts in the set (i.e. it removes all concepts that are an ancestor of another concept in the set)
* lowest_common_ancestors() computes the lower common ancestors
* find(c) search the set for a concept that is a descendant of c (including c itself)
* extract(c) search the set for all concepts that are descendant of c (including c itself)
* subtract(c) return a new set with all concepts in the set, except those that are descendant of c (including c itself)
* subtract_update(c) remove from the set for all concepts that are descendant of c (including c itself)
* all_subsets() computes all subsets included in the set.
* imply(other) returns True if all concepts in the 'other' set are descendants of (at least) one of the concepts in the set
* is_semantic_subset(other) returns True if all concepts in this set are descendants of (at least) one of the concept in the 'other' set
* is_semantic_superset(other) returns True if all concepts in this set are ancestors of (at least) one of the concept in the 'other' set
* is_semantic_disjoint(other) returns True if all concepts in this set are semantically disjoint from all concepts in the 'other' set
* semantic_intersection(other) returns the intersection of the set with 'other', considering is-a relations between the concepts in the sets
* remove_entire_families(only_family_with_more_than_one_child = True) replaces concepts in the set by their parents, whenever all the children of the parent are present
