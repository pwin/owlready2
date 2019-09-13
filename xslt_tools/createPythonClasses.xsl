<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
    xmlns:foo="http://whatever"
    version="2.0">
    <xsl:output method="text" omit-xml-declaration="yes" indent="no"/>
    
    <xsl:function name="foo:getURL">
        <xsl:param name="path" />
        <xsl:choose>
            <xsl:when test="contains($path,'#')">
                <xsl:value-of select="substring-before($path,tokenize($path,'#')[last()])" />
            </xsl:when>
            <xsl:when test="contains($path,'/')">
                <xsl:value-of select="substring-before($path,tokenize($path,'/')[last()])" />
            </xsl:when>
            <xsl:otherwise />
        </xsl:choose>
    </xsl:function>
    
    
    <xsl:function name="foo:getClass">
        <xsl:param name="path" />
        <xsl:choose>
            <xsl:when test="contains($path,'#')">
                <xsl:value-of select="tokenize($path,'#')[last()]" />
            </xsl:when>
            <xsl:when test="contains($path,'/')">
                <xsl:value-of select="tokenize($path,'/')[last()]" />
            </xsl:when>
            <xsl:otherwise >
                <xsl:value-of select="$path"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>
    
    
    <xsl:template match="/">

<xsl:text>#!/usr/bin/env python


"""
Comment: </xsl:text><xsl:value-of select="rdf:RDF/owl:Ontology/rdfs:comment[@xml:lang='en']"/>
<xsl:text>
About: </xsl:text><xsl:value-of select="rdf:RDF/owl:Ontology/@rdf:about[@xml:lang='en']"/>
<xsl:text>
Version Info: </xsl:text><xsl:value-of select="rdf:RDF/owl:Ontology/owl:versionInfo[@xml:lang='en']"/>
<xsl:text>
Version IRI: </xsl:text> <xsl:value-of select="rdf:RDF/owl:Ontology/owl:versionIRI/@rdf:resource"/>        
<xsl:text>&#xA;"""&#xA;&#xA;
from owlready2 import *

onto = get_ontology("</xsl:text>
        <xsl:value-of select="/*/namespace::*[name()='']"/><xsl:text>")&#xA;&#xA;</xsl:text>        
        
<xsl:for-each select="//owl:Class[@rdf:about]">
    <xsl:variable name="class"><xsl:value-of select="foo:getClass(@rdf:about)"/></xsl:variable>
    <xsl:variable name="namespace"><xsl:value-of select="foo:getURL(@rdf:about)"/></xsl:variable>
    <xsl:variable name="thing">Thing</xsl:variable>
<xsl:text>&#xA;def Class </xsl:text>
<xsl:value-of select="$class" />
<xsl:text>(</xsl:text>
    <xsl:choose>
        <xsl:when test="./rdfs:subClassOf">
            <xsl:for-each select="./rdfs:subClassOf">
            <xsl:value-of select="foo:getClass(./@rdf:resource)"></xsl:value-of>
            </xsl:for-each>
        </xsl:when>
        <xsl:otherwise>
            <xsl:value-of select="$thing"/>
        </xsl:otherwise>
    </xsl:choose>
    <xsl:text>):</xsl:text>
    <xsl:choose>
        <xsl:when test="string-length(tokenize($namespace,' ')) > 0">
<xsl:text>&#xA;    namespace = onto.get_namespace("</xsl:text><xsl:value-of select="$namespace"></xsl:value-of><xsl:text>")</xsl:text>
        </xsl:when>
    <xsl:otherwise>
<xsl:text>&#xA;    namespace = onto </xsl:text>        
    </xsl:otherwise></xsl:choose>        
    <xsl:if test="rdfs:label[@xml:lang='en']">
        <xsl:text>&#xA;    label = "</xsl:text><xsl:value-of select="rdfs:label[@xml:lang='en']" /><xsl:text>"</xsl:text>
</xsl:if>
    <xsl:if test="rdfs:comment[@xml:lang='en']">
        <xsl:text>&#xA;    comment = """</xsl:text><xsl:value-of select="rdfs:comment[@xml:lang='en']" /><xsl:text>"""</xsl:text>
</xsl:if>
<xsl:text>
    
</xsl:text>
</xsl:for-each>


<xsl:for-each select="//owl:ObjectProperty[@rdf:about]">
    <xsl:variable name="class"><xsl:value-of select="foo:getClass(@rdf:about)"/></xsl:variable>
    <xsl:variable name="namespace"><xsl:value-of select="foo:getURL(@rdf:about)"/></xsl:variable>
    <xsl:variable name="thing">ObjectProperty</xsl:variable>
    <xsl:text>&#xA;def Class </xsl:text>
    <xsl:value-of select="$class" />
    <xsl:text>(</xsl:text>
    <xsl:choose>
        <xsl:when test="./rdfs:subPropertyOf">
            <xsl:for-each select="./rdfs:subPropertyOf">
            <xsl:value-of select="foo:getClass(./@rdf:resource)"></xsl:value-of>
            </xsl:for-each>
        </xsl:when>
        <xsl:otherwise>
            <xsl:value-of select="$thing"/>
        </xsl:otherwise>
    </xsl:choose>
    <xsl:text>):</xsl:text>
    <xsl:choose>
        <xsl:when test="string-length(tokenize($namespace,' ')) > 0">
            <xsl:text>&#xA;    namespace = onto.get_namespace("</xsl:text><xsl:value-of select="$namespace"></xsl:value-of><xsl:text>")</xsl:text>
        </xsl:when>
        <xsl:otherwise>
            <xsl:text>&#xA;    namespace = onto </xsl:text>        
        </xsl:otherwise></xsl:choose>        
    <xsl:if test="rdfs:label[@xml:lang='en']">
        <xsl:text>&#xA;    label = "</xsl:text><xsl:value-of select="rdfs:label[@xml:lang='en']" /><xsl:text>"</xsl:text>
    </xsl:if>
    <xsl:if test="rdfs:comment[@xml:lang='en']">
        <xsl:text>&#xA;    comment = """</xsl:text><xsl:value-of select="rdfs:comment[@xml:lang='en']" /><xsl:text>"""</xsl:text>
    </xsl:if>
    <xsl:text>
    
</xsl:text>
</xsl:for-each>
<xsl:for-each select="//owl:DataProperty[@rdf:about]">
    <xsl:variable name="class"><xsl:value-of select="foo:getClass(@rdf:about)"/></xsl:variable>
    <xsl:variable name="namespace"><xsl:value-of select="foo:getURL(@rdf:about)"/></xsl:variable>
    <xsl:variable name="thing">DataProperty</xsl:variable>
    <xsl:text>&#xA;def Class </xsl:text>
    <xsl:value-of select="$class" />
    <xsl:text>(</xsl:text>
    <xsl:choose>
        <xsl:when test="./rdfs:subPropertyOf">
            <xsl:for-each select="./rdfs:subPropertyOf">
                <xsl:value-of select="foo:getClass(./@rdf:resource)"></xsl:value-of>
            </xsl:for-each>
        </xsl:when>
        <xsl:otherwise>
            <xsl:value-of select="$thing"/>
        </xsl:otherwise>
    </xsl:choose>
    <xsl:text>):</xsl:text>
    <xsl:choose>
        <xsl:when test="string-length(tokenize($namespace,' ')) > 0">
            <xsl:text>&#xA;    namespace = onto.get_namespace("</xsl:text><xsl:value-of select="$namespace"></xsl:value-of><xsl:text>")</xsl:text>
        </xsl:when>
        <xsl:otherwise>
            <xsl:text>&#xA;    namespace = onto </xsl:text>        
        </xsl:otherwise></xsl:choose>        
    <xsl:if test="rdfs:label[@xml:lang='en']">
        <xsl:text>&#xA;    label = "</xsl:text><xsl:value-of select="rdfs:label[@xml:lang='en']" /><xsl:text>"</xsl:text>
    </xsl:if>
    <xsl:if test="rdfs:comment[@xml:lang='en']">
        <xsl:text>&#xA;    comment = """</xsl:text><xsl:value-of select="rdfs:comment[@xml:lang='en']" /><xsl:text>"""</xsl:text>
    </xsl:if>
    <xsl:text>

</xsl:text>
</xsl:for-each>
    


<xsl:for-each select="//owl:AnnotationProperty[@rdf:about]">
    <xsl:variable name="class"><xsl:value-of select="foo:getClass(@rdf:about)"/></xsl:variable>
    <xsl:variable name="namespace"><xsl:value-of select="foo:getURL(@rdf:about)"/></xsl:variable>
    <xsl:variable name="thing">AnnotationProperty</xsl:variable>
    <xsl:text>&#xA;def Class </xsl:text>
    <xsl:value-of select="$class" />
    <xsl:text>(</xsl:text>
    <xsl:choose>
        <xsl:when test="./rdfs:subPropertyOf">
            <xsl:for-each select="./rdfs:subPropertyOf">
                <xsl:value-of select="foo:getClass(./@rdf:resource)"></xsl:value-of>
            </xsl:for-each>
        </xsl:when>
        <xsl:otherwise>
            <xsl:value-of select="$thing"/>
        </xsl:otherwise>
    </xsl:choose>
    <xsl:text>):</xsl:text>
    <xsl:choose>
        <xsl:when test="string-length(tokenize($namespace,' ')) > 0">
            <xsl:text>&#xA;    namespace = onto.get_namespace("</xsl:text><xsl:value-of select="$namespace"></xsl:value-of><xsl:text>")</xsl:text>
        </xsl:when>
        <xsl:otherwise>
            <xsl:text>&#xA;    namespace = onto </xsl:text>        
        </xsl:otherwise></xsl:choose>        
    <xsl:if test="rdfs:label[@xml:lang='en']">
        <xsl:text>&#xA;    label = "</xsl:text><xsl:value-of select="rdfs:label[@xml:lang='en']" /><xsl:text>"</xsl:text>
    </xsl:if>
    <xsl:if test="rdfs:comment[@xml:lang='en']">
        <xsl:text>&#xA;    comment = """</xsl:text><xsl:value-of select="rdfs:comment[@xml:lang='en']" /><xsl:text>"""</xsl:text>
    </xsl:if>
    <xsl:text>

</xsl:text>
</xsl:for-each>
    </xsl:template>
</xsl:stylesheet>