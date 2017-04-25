<?xml version="1.0"?>


<!DOCTYPE rdf:RDF [
    <!ENTITY owl "http://www.w3.org/2002/07/owl#" >
    <!ENTITY xsd "http://www.w3.org/2001/XMLSchema#" >
    <!ENTITY rdfs "http://www.w3.org/2000/01/rdf-schema#" >
    <!ENTITY rdf "http://www.w3.org/1999/02/22-rdf-syntax-ns#" >
    <!ENTITY test_ntriples "http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#" >
]>


<rdf:RDF xmlns="http://www.semanticweb.org/jiba/ontologies/2017/0/test#"
     xml:base="http://www.semanticweb.org/jiba/ontologies/2017/0/test"
     xmlns:test_ntriples="http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <owl:Ontology rdf:about="http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples"/>
    


    <!-- 
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Annotation properties
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     -->

    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#annot -->

    <owl:AnnotationProperty rdf:about="&test_ntriples;annot"/>
    


    <!-- 
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Object Properties
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     -->

    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#has_main_topping -->

    <owl:ObjectProperty rdf:about="&test_ntriples;has_main_topping">
        <rdf:type rdf:resource="&owl;FunctionalProperty"/>
        <rdfs:domain rdf:resource="&test_ntriples;Pizza"/>
        <rdfs:range rdf:resource="&test_ntriples;Topping"/>
    </owl:ObjectProperty>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#has_topping -->

    <owl:ObjectProperty rdf:about="&test_ntriples;has_topping">
        <rdfs:domain rdf:resource="&test_ntriples;Pizza"/>
        <rdfs:range rdf:resource="&test_ntriples;Topping"/>
    </owl:ObjectProperty>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#main_topping_of -->

    <owl:ObjectProperty rdf:about="&test_ntriples;main_topping_of">
        <rdfs:range rdf:resource="&test_ntriples;Pizza"/>
        <rdfs:domain rdf:resource="&test_ntriples;Topping"/>
        <owl:inverseOf rdf:resource="&test_ntriples;has_main_topping"/>
    </owl:ObjectProperty>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#topping_of -->

    <owl:ObjectProperty rdf:about="&test_ntriples;topping_of">
        <rdfs:range rdf:resource="&test_ntriples;Pizza"/>
        <rdfs:domain rdf:resource="&test_ntriples;Topping"/>
        <owl:inverseOf rdf:resource="&test_ntriples;has_topping"/>
    </owl:ObjectProperty>
    


    <!-- 
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Data properties
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     -->

    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#price -->

    <owl:DatatypeProperty rdf:about="&test_ntriples;price">
        <rdf:type rdf:resource="&owl;FunctionalProperty"/>
        <rdfs:domain rdf:resource="&test_ntriples;Pizza"/>
        <rdfs:range rdf:resource="&xsd;float"/>
    </owl:DatatypeProperty>
    


    <!-- 
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Classes
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     -->

    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Cheese -->

    <owl:Class rdf:about="&test_ntriples;Cheese">
        <rdfs:subClassOf rdf:resource="&test_ntriples;Topping"/>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Eggplant -->

    <owl:Class rdf:about="&test_ntriples;Eggplant">
        <rdfs:subClassOf rdf:resource="&test_ntriples;Vegetable"/>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Meat -->

    <owl:Class rdf:about="&test_ntriples;Meat">
        <rdfs:subClassOf rdf:resource="&test_ntriples;Topping"/>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#NonPizza -->

    <owl:Class rdf:about="&test_ntriples;NonPizza">
        <rdfs:subClassOf>
            <owl:Class>
                <owl:complementOf rdf:resource="&test_ntriples;Pizza"/>
            </owl:Class>
        </rdfs:subClassOf>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Olive -->

    <owl:Class rdf:about="&test_ntriples;Olive">
        <rdfs:subClassOf rdf:resource="&test_ntriples;Vegetable"/>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Pizza -->

    <owl:Class rdf:about="&test_ntriples;Pizza">
        <rdfs:comment xml:lang="en">Comment on Pizza</rdfs:comment>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Tomato -->

    <owl:Class rdf:about="&test_ntriples;Tomato">
        <rdfs:subClassOf rdf:resource="&test_ntriples;Vegetable"/>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Topping -->

    <owl:Class rdf:about="&test_ntriples;Topping"/>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#Vegetable -->

    <owl:Class rdf:about="&test_ntriples;Vegetable">
        <rdfs:subClassOf rdf:resource="&test_ntriples;Topping"/>
        <rdfs:subClassOf>
            <owl:Class>
                <owl:unionOf rdf:parseType="Collection">
                    <rdf:Description rdf:about="&test_ntriples;Eggplant"/>
                    <rdf:Description rdf:about="&test_ntriples;Olive"/>
                    <rdf:Description rdf:about="&test_ntriples;Tomato"/>
                </owl:unionOf>
            </owl:Class>
        </rdfs:subClassOf>
    </owl:Class>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#VegetarianPizza -->

    <owl:Class rdf:about="&test_ntriples;VegetarianPizza">
        <rdfs:subClassOf rdf:resource="&test_ntriples;Pizza"/>
        <rdfs:subClassOf>
            <owl:Class>
                <owl:complementOf>
                    <owl:Restriction>
                        <owl:onProperty rdf:resource="&test_ntriples;has_topping"/>
                        <owl:someValuesFrom rdf:resource="&test_ntriples;Meat"/>
                    </owl:Restriction>
                </owl:complementOf>
            </owl:Class>
        </rdfs:subClassOf>
    </owl:Class>
    


    <!-- 
    ///////////////////////////////////////////////////////////////////////////////////////
    //
    // Individuals
    //
    ///////////////////////////////////////////////////////////////////////////////////////
     -->

    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#ma_pizza -->

    <owl:NamedIndividual rdf:about="&test_ntriples;ma_pizza">
        <rdf:type rdf:resource="&test_ntriples;Pizza"/>
        <test_ntriples:price rdf:datatype="&xsd;float">9.9</test_ntriples:price>
        <test_ntriples:annot rdf:datatype="&xsd;string">Test annot</test_ntriples:annot>
        <rdfs:comment xml:lang="en">Comment</rdfs:comment>
        <rdfs:comment xml:lang="fr">Commentaire</rdfs:comment>
        <test_ntriples:has_main_topping rdf:resource="&test_ntriples;ma_tomate"/>
        <test_ntriples:has_topping rdf:resource="&test_ntriples;ma_tomate"/>
        <test_ntriples:has_topping rdf:resource="&test_ntriples;mon_frometon"/>
    </owl:NamedIndividual>
    <owl:Axiom>
        <rdfs:comment xml:lang="en">Comment on a triple</rdfs:comment>
        <rdfs:comment xml:lang="fr">Commentaire sur un triplet</rdfs:comment>
        <owl:annotatedTarget rdf:resource="&test_ntriples;Pizza"/>
        <owl:annotatedSource rdf:resource="&test_ntriples;ma_pizza"/>
        <owl:annotatedProperty rdf:resource="&rdf;type"/>
    </owl:Axiom>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#ma_tomate -->

    <owl:NamedIndividual rdf:about="&test_ntriples;ma_tomate">
        <rdf:type rdf:resource="&test_ntriples;Tomato"/>
    </owl:NamedIndividual>
    


    <!-- http://www.semanticweb.org/jiba/ontologies/2017/0/test_ntriples#mon_frometon -->

    <owl:NamedIndividual rdf:about="&test_ntriples;mon_frometon">
        <rdf:type rdf:resource="&test_ntriples;Cheese"/>
    </owl:NamedIndividual>
</rdf:RDF>



<!-- Generated by the OWL API (version 3.4.2) http://owlapi.sourceforge.net -->

