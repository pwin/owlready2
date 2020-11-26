# -*- coding: utf-8 -*-
import types
from typing import Union, Optional

from owlready2 .disjoint import AllDisjoint
from owlready2.class_construct import LogicalClassConstruct, Or, And, Not, Inverse, \
    Construct, Restriction, OneOf, ConstrainedDatatype, PropertyChain
from owlready2.entity import EntityClass, ThingClass
from owlready2.annotation import AnnotationPropertyClass
from owlready2.prop import PropertyClass, ObjectPropertyClass, DataPropertyClass, ReasoningPropertyClass, \
    SymmetricProperty, AsymmetricProperty, TransitiveProperty, FunctionalProperty, ReflexiveProperty, \
    IrreflexiveProperty
from owlready2.namespace import owl, Ontology
import owlready2.base

_DL_SYNTAX = types.SimpleNamespace(
    SUBCLASS="⊑",
    EQUIVALENT_TO="≡",
    NOT="¬",
    DISJOINT_WITH="⊑" + " " + "¬",
    EXISTS="∃",
    FORALL="∀",
    IN="∈",
    MIN="≥",
    EQUAL="=",
    NOT_EQUAL="≠",
    MAX="≤",
    INVERSE="⁻",
    AND="⊓",
    TOP="⊤",
    BOTTOM="⊥",
    OR="⊔",
    COMP="∘",
    WEDGE="⋀",
    IMPLIES="←",
    COMMA=",",
    SELF="self",
)

_FACETS = {
    "length": "length",
    "min_length": "minLength",
    "max_length": "maxLength",
    "pattern": "pattern",
    "max_inclusive": "\u2264",
    "max_exclusive": "\u003c",
    "min_inclusive": "\u2265",
    "min_exclusive": "\u003e",
    "total_digits": "totalDigits",
    "fraction_digits": "fractionDigits",
}

def dl_render_terminology_str(onto: Ontology, show_disjoint: bool = True, show_domain: bool = True, show_range: bool = True, show_inverse: bool = True, show_characteristics: bool = False) -> str:
    s = []
    if onto.annotation_properties():
        s.extend(['',
                  "##################################",
                  "#  Annotation properties         #",
                  "##################################", ''])
        for prop in onto.annotation_properties():
            s.extend(["######### %s #########" % dl_render_concept_str(prop).center(14),
                      dl_render_prop_str(prop), ''])
    if onto.data_properties():
        s.extend(['',
                  "##################################",
                  "#  Data properties               #",
                  "##################################", ''])
        for prop in onto.data_properties():
            s.extend(["######### %s #########" % dl_render_concept_str(prop).center(14),
                      dl_render_prop_str(prop, show_domain=show_domain, show_range=show_range, show_inverse=show_inverse, show_characteristics=show_characteristics), ''])
    if onto.object_properties():
        s.extend(['',
                  "##################################",
                  "#  Object properties             #",
                  "##################################", ''])
        for prop in onto.object_properties():
            s.extend(["######### %s #########" % dl_render_concept_str(prop).center(14),
                      dl_render_prop_str(prop, show_domain=show_domain, show_range=show_range, show_inverse=show_inverse, show_characteristics=show_characteristics), ''])
    if onto.classes():
        s.extend(['',
                  "##################################",
                  "#  Classes                       #",
                  "##################################", ''])
        for klass in onto.classes():
            s.extend(["######### %s #########" % dl_render_concept_str(klass).center(14),
                dl_render_class_str(klass, show_disjoint=show_disjoint), ''])
    return "\n".join(s)


def dl_render_class_str(klass: ThingClass, show_disjoint: bool = True) -> str:
    s = []
    if klass.equivalent_to:
        s.extend(
            [("%s %s %s" % (dl_render_concept_str(klass), _DL_SYNTAX.EQUIVALENT_TO, dl_render_concept_str(_))) for _ in
             klass.equivalent_to])
    if klass.is_a:
        s.extend([("%s %s %s" % (dl_render_concept_str(klass), _DL_SYNTAX.SUBCLASS, dl_render_concept_str(_))) for _ in
                  klass.is_a])
    if not s:
        s.append("%s %s %s" % (dl_render_concept_str(klass), _DL_SYNTAX.SUBCLASS, _DL_SYNTAX.TOP))
    if show_disjoint:
        for disjoint in klass.disjoints():
            s.append(dl_render_disjoint_str(disjoint, klass))
    return "\n".join(s)

def dl_render_prop_str(prop: PropertyClass, show_domain: bool = True, show_range: bool = True, show_inverse: bool = True, show_characteristics: bool = False) -> str:
    s = []
    if prop.is_a:
        s.extend([("%s %s %s" % (dl_render_concept_str(prop), _DL_SYNTAX.SUBCLASS, dl_render_concept_str(_))) for _ in
              prop.is_a if _.namespace is not owl])
    if prop.domain and show_domain:
        s.extend([("%s %s .%s %s %s" % (_DL_SYNTAX.EXISTS, prop.name, _DL_SYNTAX.TOP, _DL_SYNTAX.SUBCLASS, dl_render_concept_str(_))) for _ in prop.domain])
    if prop.range and show_range:
        s.extend([("%s %s %s %s .%s" % (_DL_SYNTAX.TOP, _DL_SYNTAX.SUBCLASS, _DL_SYNTAX.FORALL, prop.name, dl_render_concept_str(_))) for _ in prop.range])
    if prop.inverse_property and show_inverse:
        s.append("%s %s %s%s" % (prop.name, _DL_SYNTAX.EQUIVALENT_TO, dl_render_concept_str(prop.inverse_property), _DL_SYNTAX.INVERSE))
    if show_characteristics:
        if SymmetricProperty in prop.is_a:
            s.append("%s %s %s%s" % (
                prop.name, _DL_SYNTAX.SUBCLASS, prop.name, _DL_SYNTAX.INVERSE))
        if AsymmetricProperty in prop.is_a:
            s.append("%s %s %s%s%s" % (
                prop.name, _DL_SYNTAX.SUBCLASS, _DL_SYNTAX.NOT, prop.name, _DL_SYNTAX.INVERSE))
        if TransitiveProperty in prop.is_a:
            s.append("%s %s %s" % (dl_render_concept_str(PropertyChain([prop, prop])), _DL_SYNTAX.SUBCLASS, prop.name))
        if FunctionalProperty in prop.is_a:
            s.append("%s %s %s" % (_DL_SYNTAX.TOP, _DL_SYNTAX.SUBCLASS, dl_render_concept_str(prop.max(1))))
        if ReflexiveProperty in prop.is_a:
            s.append("%s %s %s" % (_DL_SYNTAX.TOP, _DL_SYNTAX.SUBCLASS, dl_render_concept_str(prop.has_self())))
        if IrreflexiveProperty in prop.is_a:
            s.append("%s %s %s" % (dl_render_concept_str(prop.has_self()), _DL_SYNTAX.SUBCLASS, _DL_SYNTAX.BOTTOM))

    return "\n".join(s)

def dl_render_disjoint_str(disjoint: AllDisjoint, klass: Optional[ThingClass] = None) -> str:
    if klass is None:
        return "\n".join(dl_render_disjoint_str(disjoint, _) for _ in disjoint.entities)
    if klass in disjoint.entities:
        return "\n".join("%s %s %s" % (dl_render_concept_str(And([klass, _])), _DL_SYNTAX.SUBCLASS, _DL_SYNTAX.BOTTOM)
                         for _ in disjoint.entities if _ is not klass)


def dl_render_concept_str(concept: Union[Construct, EntityClass]) -> str:
    this = dl_render_concept_str
    if concept is None:
        return _DL_SYNTAX.BOTTOM
    if isinstance(concept, ThingClass):
        if concept is owl.Thing:
            return _DL_SYNTAX.TOP
        if concept is owl.Nothing:
            return _DL_SYNTAX.BOTTOM
        return concept.name
    if isinstance(concept, PropertyClass):
        return concept.name
    if isinstance(concept, LogicalClassConstruct):
        s = []
        for x in concept.Classes:
            if isinstance(x, LogicalClassConstruct):
                s.append("(" + this(x) + ")")
            else:
                s.append(this(x))
        if isinstance(concept, Or):
            return (" %s " % _DL_SYNTAX.OR).join(s)
        if isinstance(concept, And):
            return (" %s " % _DL_SYNTAX.AND).join(s)
    if isinstance(concept, Not):
        return "%s %s" % (_DL_SYNTAX.NOT, this(concept.Class))
    if isinstance(concept, Inverse):
        return "%s%s" % (this(concept.property), _DL_SYNTAX.INVERSE)
    if isinstance(concept, Restriction):
        # type map
        # SOME:
        # ONLY:
        # VALUE:
        # HAS_SELF:
        # EXACTLY:
        # MIN:
        # MAX:
        if concept.type == owlready2.base.SOME:
            return "%s %s .%s" % (_DL_SYNTAX.EXISTS, this(concept.property), this(concept.value))
        if concept.type == owlready2.base.ONLY:
            return "%s %s .%s" % (_DL_SYNTAX.FORALL, this(concept.property), this(concept.value))
        if concept.type == owlready2.base.VALUE:
            return "%s %s .{%s}" % (_DL_SYNTAX.EXISTS, this(concept.property), concept.value.name if isinstance(concept.value, owl.Thing) else concept.value)
        if concept.type == owlready2.base.HAS_SELF:
            return "%s %s .%s" % (_DL_SYNTAX.EXISTS, this(concept.property), _DL_SYNTAX.SELF)
        if concept.type == owlready2.base.EXACTLY:
            return "%s %s %s .%s" % (_DL_SYNTAX.EQUAL, concept.cardinality, this(concept.property), this(concept.value))
        if concept.type == owlready2.base.MIN:
            return "%s %s %s .%s" % (_DL_SYNTAX.MIN, concept.cardinality, this(concept.property), this(concept.value))
        if concept.type == owlready2.base.MAX:
            return "%s %s %s .%s" % (_DL_SYNTAX.MAX, concept.cardinality, this(concept.property), this(concept.value))
    if isinstance(concept, OneOf):
        return "{%s}" % (" %s " % _DL_SYNTAX.OR).join("%s" % (_.name if isinstance(_, owl.Thing) else _) for _ in concept.instances)
    if isinstance(concept, ConstrainedDatatype):
        s = []
        for k in _FACETS:
            v = getattr(concept, k, None)
            if not v is None:
                s.append("%s %s" % (_FACETS[k], v))
        return "%s[%s]" % (concept.base_datatype.__name__, (" %s " % _DL_SYNTAX.COMMA).join(s))
    if isinstance(concept, PropertyChain):
        return (" %s " % _DL_SYNTAX.COMP).join(this(_) for _ in concept.properties)
    if concept in owlready2.base._universal_datatype_2_abbrev:
        iri = owlready2.base._universal_abbrev_2_iri.get(owlready2.base._universal_datatype_2_abbrev.get(concept))
        if iri.startswith("http://www.w3.org/2001/XMLSchema#"):
            return "xsd:" + iri[33:]
        hash, slash = iri.rindex('#'), iri.rindex('/')
        return iri[max(hash, slash)+1:]
    if owlready2.rdfs_datatype in [_.storid for _ in concept.is_a]: # rdfs:Datatype
        return concept.name
    raise NotImplemented
