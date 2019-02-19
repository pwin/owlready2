/* Copyright 2008, 2009, 2010 by the Oxford University Computing Laboratory

   This file is part of HermiT.

   HermiT is free software: you can redistribute it and/or modify
   it under the terms of the GNU Lesser General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   HermiT is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU Lesser General Public License for more details.

   You should have received a copy of the GNU Lesser General Public License
   along with HermiT.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.semanticweb.HermiT;

import org.semanticweb.HermiT.Configuration.BlockingStrategyType;
import org.semanticweb.HermiT.blocking.*;
import org.semanticweb.HermiT.debugger.Debugger;
import org.semanticweb.HermiT.existentials.CreationOrderStrategy;
import org.semanticweb.HermiT.existentials.ExistentialExpansionStrategy;
import org.semanticweb.HermiT.existentials.IndividualReuseStrategy;
import org.semanticweb.HermiT.hierarchy.*;
import org.semanticweb.HermiT.model.*;
import org.semanticweb.HermiT.monitor.TableauMonitor;
import org.semanticweb.HermiT.monitor.TableauMonitorFork;
import org.semanticweb.HermiT.monitor.Timer;
import org.semanticweb.HermiT.monitor.TimerWithPause;
import org.semanticweb.HermiT.structural.*;
import org.semanticweb.HermiT.tableau.InterruptFlag;
import org.semanticweb.HermiT.tableau.ReasoningTaskDescription;
import org.semanticweb.HermiT.tableau.Tableau;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.reasoner.*;
import org.semanticweb.owlapi.reasoner.impl.*;
import org.semanticweb.owlapi.util.Version;
import org.semanticweb.owlapi.vocab.PrefixOWLOntologyFormat;

import java.io.PrintWriter;
import java.util.*;

/**
 * Answers queries about the logical implications of a particular knowledge base. A Reasoner is associated with a single knowledge base, which is "loaded" when the reasoner is constructed. By default a full classification of all atomic terms in the knowledge base is also performed at this time (which can take quite a while for large or complex ontologies), but this behavior can be disabled as a part of the Reasoner configuration. Internal details of the loading and reasoning algorithms can be configured in the Reasoner constructor and do not change over the lifetime of the Reasoner object---internal data structures and caches are optimized for a particular configuration. By default, HermiT will use the set of options which provide optimal performance.
 */
public class Reasoner implements OWLReasoner {
    protected final OntologyChangeListener m_ontologyChangeListener;
    protected final Configuration m_configuration;
    protected final OWLOntology m_rootOntology;
    protected final List<OWLOntologyChange> m_pendingChanges;
    protected final Collection<DescriptionGraph> m_descriptionGraphs;
    protected final InterruptFlag m_interruptFlag;
    protected ObjectPropertyInclusionManager m_objectPropertyInclusionManager;
    protected DLOntology m_dlOntology;
    protected Prefixes m_prefixes;
    protected Tableau m_tableau;
    protected Boolean m_isConsistent;
    protected Hierarchy<AtomicConcept> m_atomicConceptHierarchy;
    protected Hierarchy<Role> m_objectRoleHierarchy;
    protected Hierarchy<AtomicRole> m_dataRoleHierarchy;
    protected Map<Role, Set<HierarchyNode<AtomicConcept>>> m_directObjectRoleDomains;
    protected Map<Role, Set<HierarchyNode<AtomicConcept>>> m_directObjectRoleRanges;
    protected Map<AtomicRole, Set<HierarchyNode<AtomicConcept>>> m_directDataRoleDomains;
    protected Map<HierarchyNode<AtomicConcept>, Set<HierarchyNode<AtomicConcept>>> m_directDisjointClasses;
    protected InstanceManager m_instanceManager;

    /**
     * Creates a new reasoner object with standard parameters for blocking, expansion strategy etc. Then the given manager is used to find all required imports for the given ontology and the ontology with the imports is loaded into the reasoner and the data factory of the manager is used to create fresh concepts during the preprocessing phase if necessary.
     *
     * @param rootOntology - the ontology that should be loaded by the reasoner
     */
    public Reasoner(OWLOntology rootOntology) {
        this(new Configuration(), rootOntology, (Set<DescriptionGraph>) null);
    }

    /**
     * Creates a new reasoner object with the parameters for blocking, expansion strategy etc as specified in the given configuration object. A default configuration can be obtained by just passing new Configuration(). Then the given manager is used to find all required imports for the given ontology and the ontology with the imports is loaded into the reasoner and the data factory of the manager is used to create fresh concepts during the preprocessing phase if necessary.
     *
     * @param configuration - a configuration in which parameters can be defined such as the blocking strategy to be used etc
     * @param rootOntology  - the ontology that should be loaded by the reasoner
     */
    public Reasoner(Configuration configuration, OWLOntology rootOntology) {
        this(configuration, rootOntology, (Set<DescriptionGraph>) null);
    }

    /**
     * Creates a new reasoner object loaded with the given ontology and the given description graphs. When creating the reasoner, the given configuration determines the parameters for blocking, expansion strategy etc. A default configuration can be obtained by just passing new Configuration(). Then the given manager is used to find all required imports for the given ontology and the ontology with the imports and the description graphs are loaded into the reasoner. The data factory of the manager is used to create fresh concepts during the preprocessing phase if necessary.
     *
     * @param configuration     - a configuration in which parameters can be defined such as the blocking strategy to be used etc
     * @param rootOntology      - the ontology that should be loaded by the reasoner
     * @param descriptionGraphs - a set of description graphs
     */
    public Reasoner(Configuration configuration, OWLOntology rootOntology, Collection<DescriptionGraph> descriptionGraphs) {
        m_ontologyChangeListener = new OntologyChangeListener();
        m_configuration = configuration;
        m_rootOntology = rootOntology;
        m_pendingChanges = new ArrayList<OWLOntologyChange>();
        m_rootOntology.getOWLOntologyManager().addOntologyChangeListener(m_ontologyChangeListener);
        if (descriptionGraphs == null)
            m_descriptionGraphs = Collections.emptySet();
        else
            m_descriptionGraphs = descriptionGraphs;
        m_interruptFlag = new InterruptFlag(configuration.individualTaskTimeout);
        m_directDisjointClasses = new HashMap<HierarchyNode<AtomicConcept>, Set<HierarchyNode<AtomicConcept>>>();
        loadOntology();
    }

    // Life-cycle management methods

    protected void loadOntology() {
        clearState();
        // Convert OWLOntology into DLOntology
        OWLClausification clausifier = new OWLClausification(m_configuration);
        Object[] result = clausifier.preprocessAndClausify(m_rootOntology, m_descriptionGraphs);
        m_objectPropertyInclusionManager = (ObjectPropertyInclusionManager) result[0];
        m_dlOntology = (DLOntology) result[1];
        
        //System.out.println(m_dlOntology.getDLClauses());
        
        // Load the DLOntology
        createPrefixes();
        m_tableau = createTableau(m_interruptFlag, m_configuration, m_dlOntology, null, m_prefixes);
        m_instanceManager = null;
    }

    protected void createPrefixes() {
        m_prefixes = new Prefixes();
        m_prefixes.declareSemanticWebPrefixes();
        Set<String> individualIRIs = new HashSet<String>();
        Set<String> anonIndividualIRIs = new HashSet<String>();
        for (Individual individual : m_dlOntology.getAllIndividuals())
            if (individual.isAnonymous())
                addIRI(individual.getIRI(), anonIndividualIRIs);
            else
                addIRI(individual.getIRI(), individualIRIs);
        m_prefixes.declareInternalPrefixes(individualIRIs, anonIndividualIRIs);
        m_prefixes.declareDefaultPrefix(m_dlOntology.getOntologyIRI() + "#");
        // declare prefixes as used in the ontology if possible
        OWLOntologyFormat format = m_rootOntology.getOWLOntologyManager().getOntologyFormat(m_rootOntology);
        if (format instanceof PrefixOWLOntologyFormat) {
            PrefixOWLOntologyFormat prefixFormat = (PrefixOWLOntologyFormat) format;
            for (String prefixName : prefixFormat.getPrefixName2PrefixMap().keySet()) {
                String prefix = prefixFormat.getPrefixName2PrefixMap().get(prefixName);
                if (m_prefixes.getPrefixName(prefix) == null)
                    try {
                        m_prefixes.declarePrefix(prefixName, prefix);
                    } catch (IllegalArgumentException e) {
                        // ignore
                    }
            }
        }
    }

    protected void addIRI(String uri, Set<String> prefixIRIs) {
        if (!Prefixes.isInternalIRI(uri)) {
            int lastHash = uri.lastIndexOf('#');
            if (lastHash != -1) {
                String prefixIRI = uri.substring(0, lastHash + 1);
                prefixIRIs.add(prefixIRI);
            }
        }
    }

    protected void finalize() {
        dispose();
    }

    public void dispose() {
        m_rootOntology.getOWLOntologyManager().removeOntologyChangeListener(m_ontologyChangeListener);
        clearState();
        m_interruptFlag.dispose();
    }

    protected void clearState() {
        m_pendingChanges.clear();
        m_dlOntology = null;
        m_prefixes = null;
        m_tableau = null;
        m_isConsistent = null;
        m_atomicConceptHierarchy = null;
        m_objectRoleHierarchy = null;
        m_dataRoleHierarchy = null;
        m_directObjectRoleDomains = new HashMap<Role, Set<HierarchyNode<AtomicConcept>>>();
        m_directObjectRoleRanges = new HashMap<Role, Set<HierarchyNode<AtomicConcept>>>();
        m_directDataRoleDomains = new HashMap<AtomicRole, Set<HierarchyNode<AtomicConcept>>>();
        m_directDisjointClasses = new HashMap<HierarchyNode<AtomicConcept>, Set<HierarchyNode<AtomicConcept>>>();
        m_instanceManager = null;
    }

    public void interrupt() {
        m_interruptFlag.interrupt();
    }

    public OWLDataFactory getDataFactory() {
        return m_rootOntology.getOWLOntologyManager().getOWLDataFactory();
    }

    // Accessor methods of the OWL API

    public String getReasonerName() {
        return getClass().getPackage().getImplementationTitle();
    }

    public Version getReasonerVersion() {
        String versionString = Reasoner.class.getPackage().getImplementationVersion();
        String[] splitted;
        int filled = 0;
        int version[] = new int[4];
        if (versionString != null) {
            splitted = versionString.split("\\.");
            while (filled < splitted.length) {
                version[filled] = Integer.parseInt(splitted[filled]);
                filled++;
            }
        }
        while (filled < version.length) {
            version[filled] = 0;
            filled++;
        }
        return new Version(version[0], version[1], version[2], version[3]);
    }

    public OWLOntology getRootOntology() {
        return m_rootOntology;
    }

    public long getTimeOut() {
        return m_configuration.individualTaskTimeout;
    }

    public IndividualNodeSetPolicy getIndividualNodeSetPolicy() {
        return m_configuration.getIndividualNodeSetPolicy();
    }

    public FreshEntityPolicy getFreshEntityPolicy() {
        return m_configuration.getFreshEntityPolicy();
    }

    // HermiT's accessor methods

    public Prefixes getPrefixes() {
        return m_prefixes;
    }

    public DLOntology getDLOntology() {
        return m_dlOntology;
    }

    public Configuration getConfiguration() {
        return m_configuration.clone();
    }

    // Ontology change management methods

    protected class OntologyChangeListener implements OWLOntologyChangeListener {
        public void ontologiesChanged(List<? extends OWLOntologyChange> changes) throws OWLException {
            for (OWLOntologyChange change : changes)
                if (!(change instanceof RemoveOntologyAnnotation || change instanceof AddOntologyAnnotation))
                    m_pendingChanges.add(change);
        }
    }

    public BufferingMode getBufferingMode() {
        return m_configuration.bufferChanges ? BufferingMode.BUFFERING : BufferingMode.NON_BUFFERING;
    }

    public Set<OWLAxiom> getPendingAxiomAdditions() {
        Set<OWLAxiom> added = new HashSet<OWLAxiom>();
        for (OWLOntologyChange change : m_pendingChanges)
            if (change instanceof AddAxiom)
                added.add(change.getAxiom());
        return added;
    }

    public Set<OWLAxiom> getPendingAxiomRemovals() {
        Set<OWLAxiom> removed = new HashSet<OWLAxiom>();
        for (OWLOntologyChange change : m_pendingChanges)
            if (change instanceof RemoveAxiom)
                removed.add(change.getAxiom());
        return removed;
    }

    public List<OWLOntologyChange> getPendingChanges() {
        return m_pendingChanges;
    }

    public void flush() {
        if (!m_pendingChanges.isEmpty()) {
            // check if we can only reload the ABox
            if (canProcessPendingChangesIncrementally()) {
                Set<OWLOntology> rootOntologyImportsClosure = m_rootOntology.getImportsClosure();
                Set<Atom> positiveFacts = m_dlOntology.getPositiveFacts();
                Set<Atom> negativeFacts = m_dlOntology.getNegativeFacts();
                Set<Individual> allIndividuals = new HashSet<Individual>();
                Set<AtomicConcept> allAtomicConcepts = m_dlOntology.getAllAtomicConcepts();
                Set<AtomicRole> allAtomicObjectRoles = m_dlOntology.getAllAtomicObjectRoles();
                Set<AtomicRole> allAtomicDataRoles = m_dlOntology.getAllAtomicDataRoles();
                ReducedABoxOnlyClausification aboxFactClausifier = new ReducedABoxOnlyClausification(m_configuration, getDataFactory(), allAtomicConcepts, allAtomicObjectRoles, allAtomicDataRoles);
                for (OWLOntologyChange change : m_pendingChanges) {
                    if (rootOntologyImportsClosure.contains(change.getOntology())) {
                        OWLAxiom axiom = change.getAxiom();
                        if (axiom.isLogicalAxiom()) {
                            aboxFactClausifier.clausify((OWLIndividualAxiom) axiom);
                            if (change instanceof AddAxiom) {
                                positiveFacts.addAll(aboxFactClausifier.getPositiveFacts());
                                negativeFacts.addAll(aboxFactClausifier.getNegativeFacts());
                            } else {
                                positiveFacts.removeAll(aboxFactClausifier.getPositiveFacts());
                                negativeFacts.removeAll(aboxFactClausifier.getNegativeFacts());
                            }
                        }
                    }
                }
                for (Atom atom : positiveFacts)
                    atom.getIndividuals(allIndividuals);
                for (Atom atom : negativeFacts)
                    atom.getIndividuals(allIndividuals);
                m_dlOntology = new DLOntology(m_dlOntology.getOntologyIRI(), m_dlOntology.getDLClauses(), positiveFacts, negativeFacts, allAtomicConcepts, allAtomicObjectRoles, m_dlOntology.getAllComplexObjectRoles(), allAtomicDataRoles, m_dlOntology.getAllUnknownDatatypeRestrictions(), m_dlOntology.getDefinedDatatypeIRIs(), allIndividuals, m_dlOntology.hasInverseRoles(), m_dlOntology.hasAtMostRestrictions(), m_dlOntology.hasNominals(), m_dlOntology.hasDatatypes());
                m_tableau = new Tableau(m_interruptFlag, m_tableau.getTableauMonitor(), m_tableau.getExistentialsExpansionStrategy(), m_configuration.useDisjunctionLearning, m_dlOntology, null, m_configuration.parameters);
                m_instanceManager = null;
                m_isConsistent = null;
            } else
                loadOntology();
            m_pendingChanges.clear();
        }
    }

    public boolean canProcessPendingChangesIncrementally() {
        Set<OWLOntology> rootOntologyImportsClosure = m_rootOntology.getImportsClosure();
        for (OWLOntologyChange change : m_pendingChanges) {
            if (rootOntologyImportsClosure.contains(change.getOntology())) {
                if (m_dlOntology.hasNominals() || !m_dlOntology.getAllDescriptionGraphs().isEmpty())
                    return false;
                if (!change.isAxiomChange())
                    return false;
                OWLAxiom axiom = change.getAxiom();
                if (axiom.isLogicalAxiom()) {
                    if (axiom instanceof OWLClassAssertionAxiom) {
                        // we can handle everything that results in positive or negative facts
                        // (C a) with C a named class, HasSelf, HasValue, negated named class, negated HasSelf, negatedHasValue
                        // all used names must already exist in the loaded ontology
                        OWLClassAssertionAxiom classAssertion = (OWLClassAssertionAxiom) axiom;
                        OWLIndividual individual = classAssertion.getIndividual();
                        if (!isDefined(individual))
                            return false;
                        OWLClassExpression classExpression = classAssertion.getClassExpression();
                        if (classExpression instanceof OWLClass) {
                            if (!(isDefined((OWLClass) classExpression) || Prefixes.isInternalIRI(((OWLClass) classExpression).getIRI().toString())))
                                return false;
                        } else if (classExpression instanceof OWLObjectHasSelf) {
                            OWLObjectProperty namedOP = ((OWLObjectHasSelf) classExpression).getProperty().getNamedProperty();
                            if (!(isDefined(namedOP) || Prefixes.isInternalIRI(namedOP.getIRI().toString())))
                                return false;
                        } else if (classExpression instanceof OWLObjectHasValue) {
                            OWLObjectHasValue hasValue = (OWLObjectHasValue) classExpression;
                            OWLObjectProperty namedOP = hasValue.getProperty().getNamedProperty();
                            OWLIndividual filler = hasValue.getValue();
                            if (!(isDefined(namedOP) || Prefixes.isInternalIRI(namedOP.getIRI().toString())) || !isDefined(filler))
                                return false;
                        } else if (classExpression instanceof OWLObjectComplementOf) {
                            OWLClassExpression negated = ((OWLObjectComplementOf) classExpression).getOperand();
                            if (negated instanceof OWLClass) {
                                OWLClass cls = (OWLClass) negated;
                                if (!(isDefined(cls) || Prefixes.isInternalIRI(cls.getIRI().toString())))
                                    return false;
                            } else if (negated instanceof OWLObjectHasSelf) {
                                OWLObjectHasSelf hasSelf = (OWLObjectHasSelf) negated;
                                OWLObjectProperty namedOP = hasSelf.getProperty().getNamedProperty();
                                if (!(isDefined(namedOP) || Prefixes.isInternalIRI(namedOP.getIRI().toString())))
                                    return false;
                            } else if (negated instanceof OWLObjectHasValue) {
                                OWLObjectHasValue hasSelf = (OWLObjectHasValue) negated;
                                OWLObjectProperty namedOP = hasSelf.getProperty().getNamedProperty();
                                OWLIndividual filler = hasSelf.getValue();
                                if (!(isDefined(namedOP) || Prefixes.isInternalIRI(namedOP.getIRI().toString())) || !isDefined(filler))
                                    return false;
                            } else {
                                return false;
                            }
                        } else
                            return false;
                    } else if (!(axiom instanceof OWLIndividualAxiom)) {
                        return false;
                    }
                } else if (axiom instanceof OWLDeclarationAxiom) {
                    OWLEntity entity = ((OWLDeclarationAxiom) axiom).getEntity();
                    if (entity.isOWLClass() && !(isDefined((OWLClass) entity) || Prefixes.isInternalIRI(((OWLClass) entity).getIRI().toString())))
                        return false;
                    else if (entity.isOWLObjectProperty() && !(isDefined((OWLObjectProperty) entity) || Prefixes.isInternalIRI(((OWLObjectProperty) entity).getIRI().toString())))
                        return false;
                    else if (entity.isOWLDataProperty() && !(isDefined((OWLDataProperty) entity) || Prefixes.isInternalIRI(((OWLDataProperty) entity).getIRI().toString())))
                        return false;
                }
            }
        }
        return true;
    }

    // General inferences

    public boolean isDefined(OWLClass owlClass) {
        AtomicConcept atomicConcept = AtomicConcept.create(owlClass.getIRI().toString());
        return
                m_dlOntology.containsAtomicConcept(atomicConcept) ||
                        AtomicConcept.THING.equals(atomicConcept) ||
                        AtomicConcept.NOTHING.equals(atomicConcept);
    }

    public boolean isDefined(OWLIndividual owlIndividual) {
        Individual individual;
        if (owlIndividual.isAnonymous())
            individual = Individual.createAnonymous(owlIndividual.asOWLAnonymousIndividual().getID().toString());
        else
            individual = Individual.create(owlIndividual.asOWLNamedIndividual().getIRI().toString());
        return m_dlOntology.containsIndividual(individual);
    }

    public boolean isDefined(OWLObjectProperty owlObjectProperty) {
        AtomicRole atomicRole = AtomicRole.create(owlObjectProperty.getIRI().toString());
        return
                m_dlOntology.containsObjectRole(atomicRole) ||
                        AtomicRole.TOP_OBJECT_ROLE.equals(owlObjectProperty) ||
                        AtomicRole.BOTTOM_OBJECT_ROLE.equals(owlObjectProperty);
    }

    public boolean isDefined(OWLDataProperty owlDataProperty) {
        AtomicRole atomicRole = AtomicRole.create(owlDataProperty.getIRI().toString());
        return
                m_dlOntology.containsDataRole(atomicRole) ||
                        AtomicRole.TOP_DATA_ROLE.equals(atomicRole) ||
                        AtomicRole.BOTTOM_DATA_ROLE.equals(atomicRole);
    }

    public Set<InferenceType> getPrecomputableInferenceTypes() {
        Set<InferenceType> supportedInferenceTypes = new HashSet<InferenceType>();
        supportedInferenceTypes.add(InferenceType.CLASS_HIERARCHY);
        supportedInferenceTypes.add(InferenceType.OBJECT_PROPERTY_HIERARCHY);
        supportedInferenceTypes.add(InferenceType.DATA_PROPERTY_HIERARCHY);
        supportedInferenceTypes.add(InferenceType.CLASS_ASSERTIONS);
        supportedInferenceTypes.add(InferenceType.OBJECT_PROPERTY_ASSERTIONS);
        // supportedInferenceTypes.add(InferenceType.DATA_PROPERTY_ASSERTIONS);
        supportedInferenceTypes.add(InferenceType.SAME_INDIVIDUAL);
        // supportedInferenceTypes.add(InferenceType.DISJOINT_CLASSES);
        return supportedInferenceTypes;
    }

    public boolean isPrecomputed(InferenceType inferenceType) {
        switch (inferenceType) {
            case CLASS_HIERARCHY:
                return m_atomicConceptHierarchy != null;
            case OBJECT_PROPERTY_HIERARCHY:
                return m_objectRoleHierarchy != null;
            case DATA_PROPERTY_HIERARCHY:
                return m_dataRoleHierarchy != null;
            case CLASS_ASSERTIONS:
                return m_instanceManager != null && m_instanceManager.realizationCompleted();
            case OBJECT_PROPERTY_ASSERTIONS:
                return m_instanceManager != null && m_instanceManager.objectPropertyRealizationCompleted();
            // case DATA_PROPERTY_ASSERTIONS:
            // return m_dataRoleHierarchy!=null; // used to find sub-propeties
            case SAME_INDIVIDUAL:
                return m_instanceManager != null && m_instanceManager.sameAsIndividualsComputed();
            // case DIFFERENT_INDIVIDUALS:
            // return false;
            // case DISJOINT_CLASSES:
            // return m_atomicConceptHierarchy!=null && m_directDisjointClasses.keySet().size()==m_atomicConceptHierarchy.getAllElements().size()-2;
            default:
                break;
        }
        return false;
    }

    public void precomputeInferences(InferenceType... inferenceTypes) throws ReasonerInterruptedException, TimeOutException, InconsistentOntologyException {
        checkPreConditions();
        boolean doAll = m_configuration.prepareReasonerInferences == null;
        // doAll is only false when used via Protege, in that case the Protege preferences apply
        Set<InferenceType> requiredInferences = new HashSet<InferenceType>(Arrays.asList(inferenceTypes));
        if (requiredInferences.contains(InferenceType.CLASS_HIERARCHY))
            if (doAll || m_configuration.prepareReasonerInferences.classClassificationRequired)
                classifyClasses();
        if (requiredInferences.contains(InferenceType.OBJECT_PROPERTY_HIERARCHY))
            if (doAll || m_configuration.prepareReasonerInferences.objectPropertyClassificationRequired)
                classifyObjectProperties();
        if (requiredInferences.contains(InferenceType.DATA_PROPERTY_HIERARCHY))
            if (doAll || m_configuration.prepareReasonerInferences.dataPropertyClassificationRequired)
                classifyDataProperties();
        if (requiredInferences.contains(InferenceType.CLASS_ASSERTIONS))
            if (doAll || m_configuration.prepareReasonerInferences.realisationRequired) {
                realise();
                if (m_configuration.individualNodeSetPolicy == IndividualNodeSetPolicy.BY_SAME_AS || (m_configuration.prepareReasonerInferences != null && m_configuration.prepareReasonerInferences.sameAs))
                    precomputeSameAsEquivalenceClasses();
            }
        if (requiredInferences.contains(InferenceType.OBJECT_PROPERTY_ASSERTIONS))
            if (doAll || m_configuration.prepareReasonerInferences.objectPropertyRealisationRequired)
                realiseObjectProperties();
        // if (requiredInferences.contains(InferenceType.DATA_PROPERTY_ASSERTIONS))
        // if (doAll || m_configuration.prepareReasonerInferences.dataPropertyRealisationRequired)
        // classifyDataProperties(); // used to enriched stated instances
        if (requiredInferences.contains(InferenceType.SAME_INDIVIDUAL))
            if (doAll || m_configuration.prepareReasonerInferences.sameAs)
                precomputeSameAsEquivalenceClasses();
        // the tasks is not being supported by HermiT because it would be very slow
        // we silently ignore the request as the documentation of the method recommends
        // if (requiredInferences.contains(InferenceType.DIFFERENT_INDIVIDUALS))
        // throw new UnsupportedOperationException("Error: HermiT cannot precompute different individuals. "+System.getProperty("line.separator")+"That is a very expensive task because all pairs of individuals have to be tested despite the fact that such a test will most likely fail. ");
        // if (requiredInferences.contains(InferenceType.DISJOINT_CLASSES))
        // precomputeDisjointClasses();
    }

    public void initialisePropertiesInstanceManager() {
        if (m_instanceManager == null || !m_instanceManager.arePropertiesInitialised()) {
            if (m_configuration.reasonerProgressMonitor != null)
                m_configuration.reasonerProgressMonitor.reasonerTaskStarted("Initializing property instance data structures");
            if (m_instanceManager == null)
                m_instanceManager = new InstanceManager(m_interruptFlag, this, m_atomicConceptHierarchy, m_objectRoleHierarchy);
            boolean isConsistent = true;
            if (m_isConsistent != null && !m_isConsistent)
                m_instanceManager.setInconsistent();
            else {
                int noAxioms = m_dlOntology.getDLClauses().size();
                int noComplexRoles = m_dlOntology.getAllComplexObjectRoles().size();
                if (m_dlOntology.hasInverseRoles())
                    noComplexRoles = noComplexRoles / 2;
                int noIndividuals = m_dlOntology.getAllIndividuals().size();
                int chunks = (((2 * noComplexRoles * noIndividuals) / InstanceManager.thresholdForAdditionalAxioms)) + 1;
                int stepsAdditionalAxioms = noComplexRoles * noIndividuals;
                int stepsRewritingAdditionalAxioms = (5 * noComplexRoles * noIndividuals) / chunks;
                int stepsTableauExpansion = (stepsAdditionalAxioms / chunks) + noAxioms + noIndividuals;
                int stepsInitialiseKnownPossible = noIndividuals + noComplexRoles * noIndividuals;
                int steps = stepsAdditionalAxioms + (chunks * stepsRewritingAdditionalAxioms) + (chunks * stepsTableauExpansion) + stepsInitialiseKnownPossible;
                int startIndividualIndex = 0;
                int completedSteps = 0;
                OWLAxiom[] additionalAxioms = m_instanceManager.getAxiomsForReadingOffCompexProperties(getDataFactory(), m_configuration.reasonerProgressMonitor, completedSteps, steps);
                completedSteps += stepsAdditionalAxioms / chunks;
                boolean moreWork = true;
                while (moreWork) {
                    Tableau tableau = getTableau(additionalAxioms);
                    completedSteps += stepsRewritingAdditionalAxioms;
                    if (m_configuration.reasonerProgressMonitor != null)
                        m_configuration.reasonerProgressMonitor.reasonerTaskProgressChanged(completedSteps, steps);
                    isConsistent = tableau.isSatisfiable(true, true, null, null, null, null, m_instanceManager.getNodesForIndividuals(), new ReasoningTaskDescription(false, "Initial consistency check plus reading-off known and possible class and property instances (individual " + startIndividualIndex + " to " + m_instanceManager.getCurrentIndividualIndex() + ")."));
                    completedSteps += stepsTableauExpansion;
                    if (m_configuration.reasonerProgressMonitor != null)
                        m_configuration.reasonerProgressMonitor.reasonerTaskProgressChanged(completedSteps, steps);
                    if (!isConsistent) {
                        m_instanceManager.setInconsistent();
                        break;
                    } else
                        completedSteps = m_instanceManager.initializeKnowAndPossiblePropertyInstances(tableau, m_configuration.reasonerProgressMonitor, startIndividualIndex, completedSteps, steps);
                    tableau.clearAdditionalDLOntology();
                    startIndividualIndex = m_instanceManager.getCurrentIndividualIndex();
                    additionalAxioms = m_instanceManager.getAxiomsForReadingOffCompexProperties(getDataFactory(), m_configuration.reasonerProgressMonitor, completedSteps, steps);
                    completedSteps += stepsAdditionalAxioms / chunks;
                    moreWork = additionalAxioms.length > 0;
                }
                if (m_isConsistent == null)
                    m_isConsistent = isConsistent;
            }
            if (m_configuration.reasonerProgressMonitor != null)
                m_configuration.reasonerProgressMonitor.reasonerTaskStopped();
        }
    }

    protected void initialiseClassInstanceManager() {
        if (m_instanceManager == null || !m_instanceManager.areClassesInitialised()) {
            if (m_configuration.reasonerProgressMonitor != null)
                m_configuration.reasonerProgressMonitor.reasonerTaskStarted("Initializing class instance data structures");
            if (m_instanceManager == null)
                m_instanceManager = new InstanceManager(m_interruptFlag, this, m_atomicConceptHierarchy, m_objectRoleHierarchy);
            boolean isConsistent = true;
            if (m_isConsistent != null && !m_isConsistent)
                m_instanceManager.setInconsistent();
            else {
                int noAxioms = m_dlOntology.getDLClauses().size();
                int noIndividuals = m_dlOntology.getAllIndividuals().size();
                int stepsTableauExpansion = noAxioms + noIndividuals;
                int stepsInitialiseKnownPossible = noIndividuals;
                int steps = stepsTableauExpansion + stepsInitialiseKnownPossible;
                int completedSteps = 0;
                Tableau tableau = getTableau();
                isConsistent = tableau.isSatisfiable(true, true, null, null, null, null, m_instanceManager.getNodesForIndividuals(), new ReasoningTaskDescription(false, "Initial tableau for reading-off known and possible class instances."));
                completedSteps += stepsTableauExpansion;
                if (m_configuration.reasonerProgressMonitor != null)
                    m_configuration.reasonerProgressMonitor.reasonerTaskProgressChanged(completedSteps, steps);
                if (!isConsistent)
                    m_instanceManager.setInconsistent();
                else
                    m_instanceManager.initializeKnowAndPossibleClassInstances(tableau, m_configuration.reasonerProgressMonitor, completedSteps, steps);
                if (m_isConsistent == null)
                    m_isConsistent = isConsistent;
                tableau.clearAdditionalDLOntology();
            }
            if (m_configuration.reasonerProgressMonitor != null)
                m_configuration.reasonerProgressMonitor.reasonerTaskStopped();
        }
    }

    public boolean isConsistent() {
        flushChangesIfRequired();
        if (m_isConsistent == null)
            m_isConsistent = getTableau().isSatisfiable(true, true, null, null, null, null, null, ReasoningTaskDescription.isABoxSatisfiable());
        return m_isConsistent;
    }

    public boolean isEntailmentCheckingSupported(AxiomType<?> axiomType) {
        return true;
    }

    public boolean isEntailed(OWLAxiom axiom) {
        checkPreConditions(axiom);
        if (!isConsistent())
            return true;
        EntailmentChecker checker = new EntailmentChecker(this, getDataFactory());
        return checker.entails(axiom);
    }

    public boolean isEntailed(Set<? extends OWLAxiom> axioms) {
        checkPreConditions(axioms.toArray(new OWLObject[0]));
        if (!m_isConsistent)
            return true;
        EntailmentChecker checker = new EntailmentChecker(this, getDataFactory());
        return checker.entails(axioms);
    }

    // Concept inferences

    /**
     * @deprecated As of release 1.3, replaced by {@link #precomputeInferences(InferenceType... inferenceTypes)} with inference type CLASS_HIERARCHY
     */
    @Deprecated
    public void classify() {
        classifyClasses();
    }

    public void classifyClasses() {
        checkPreConditions();
        if (m_atomicConceptHierarchy == null) {
            Set<AtomicConcept> relevantAtomicConcepts = new HashSet<AtomicConcept>();
            relevantAtomicConcepts.add(AtomicConcept.THING);
            relevantAtomicConcepts.add(AtomicConcept.NOTHING);
            for (AtomicConcept atomicConcept : m_dlOntology.getAllAtomicConcepts())
                if (!Prefixes.isInternalIRI(atomicConcept.getIRI()))
                    relevantAtomicConcepts.add(atomicConcept);
            if (!m_isConsistent)
                m_atomicConceptHierarchy = Hierarchy.emptyHierarchy(relevantAtomicConcepts, AtomicConcept.THING, AtomicConcept.NOTHING);
            else {
                try {
                    final int numRelevantConcepts = relevantAtomicConcepts.size();
                    if (m_configuration.reasonerProgressMonitor != null)
                        m_configuration.reasonerProgressMonitor.reasonerTaskStarted("Building the class hierarchy...");
                    ClassificationProgressMonitor progressMonitor = new ClassificationProgressMonitor() {
                        protected int m_processedConcepts = 0;

                        public void elementClassified(AtomicConcept element) {
                            m_processedConcepts++;
                            if (m_configuration.reasonerProgressMonitor != null)
                                m_configuration.reasonerProgressMonitor.reasonerTaskProgressChanged(m_processedConcepts, numRelevantConcepts);
                        }
                    };
                    m_atomicConceptHierarchy = classifyAtomicConcepts(getTableau(), progressMonitor, AtomicConcept.THING, AtomicConcept.NOTHING, relevantAtomicConcepts, m_configuration.forceQuasiOrderClassification);
                    if (m_instanceManager != null)
                        m_instanceManager.setToClassifiedConceptHierarchy(m_atomicConceptHierarchy);
                } finally {
                    if (m_configuration.reasonerProgressMonitor != null)
                        m_configuration.reasonerProgressMonitor.reasonerTaskStopped();
                }
            }
        }
    }

    public Node<OWLClass> getTopClassNode() {
        classifyClasses();
        return atomicConceptHierarchyNodeToNode(m_atomicConceptHierarchy.getTopNode());
    }

    public Node<OWLClass> getBottomClassNode() {
        classifyClasses();
        return atomicConceptHierarchyNodeToNode(m_atomicConceptHierarchy.getBottomNode());
    }

    public boolean isSatisfiable(OWLClassExpression classExpression) {
        checkPreConditions(classExpression);
        if (!isConsistent())
            return false;
        if (classExpression instanceof OWLClass && m_atomicConceptHierarchy != null) {
            AtomicConcept concept = H((OWLClass) classExpression);
            HierarchyNode<AtomicConcept> node = m_atomicConceptHierarchy.getNodeForElement(concept);
            return node != m_atomicConceptHierarchy.getBottomNode();
        } else {
            OWLDataFactory factory = getDataFactory();
            OWLIndividual freshIndividual = factory.getOWLAnonymousIndividual("fresh-individual");
            OWLClassAssertionAxiom assertClassExpression = factory.getOWLClassAssertionAxiom(classExpression, freshIndividual);
            Tableau tableau = getTableau(assertClassExpression);
            return tableau.isSatisfiable(true, null, null, null, null, null, ReasoningTaskDescription.isConceptSatisfiable(classExpression));
        }
    }

    protected boolean isSubClassOf(OWLClassExpression subClassExpression, OWLClassExpression superClassExpression) {
        checkPreConditions(subClassExpression, superClassExpression);
        if (!isConsistent() || subClassExpression.isOWLNothing() || superClassExpression.isOWLThing())
            return true;
        if (subClassExpression instanceof OWLClass && superClassExpression instanceof OWLClass) {
            AtomicConcept subconcept = H((OWLClass) subClassExpression);
            AtomicConcept superconcept = H((OWLClass) superClassExpression);
            if (m_atomicConceptHierarchy != null && !containsFreshEntities(subClassExpression, superClassExpression)) {
                HierarchyNode<AtomicConcept> subconceptNode = m_atomicConceptHierarchy.getNodeForElement(subconcept);
                return subconceptNode.isEquivalentElement(superconcept) || subconceptNode.isAncestorElement(superconcept);
            } else {
                Tableau tableau = getTableau();
                Individual freshIndividual = Individual.createAnonymous("fresh-individual");
                Atom subconceptAssertion = Atom.create(subconcept, freshIndividual);
                Atom superconceptAssertion = Atom.create(superconcept, freshIndividual);
                return !tableau.isSatisfiable(true, Collections.singleton(subconceptAssertion), Collections.singleton(superconceptAssertion), null, null, null, ReasoningTaskDescription.isConceptSubsumedBy(subconcept, superconcept));
            }
        } else {
            OWLDataFactory factory = getDataFactory();
            OWLIndividual freshIndividual = factory.getOWLAnonymousIndividual("fresh-individual");
            OWLClassAssertionAxiom assertSubClassExpression = factory.getOWLClassAssertionAxiom(subClassExpression, freshIndividual);
            OWLClassAssertionAxiom assertNotSuperClassExpression = factory.getOWLClassAssertionAxiom(superClassExpression.getObjectComplementOf(), freshIndividual);
            Tableau tableau = getTableau(assertSubClassExpression, assertNotSuperClassExpression);
            boolean result = tableau.isSatisfiable(true, null, null, null, null, null, ReasoningTaskDescription.isConceptSubsumedBy(subClassExpression, superClassExpression));
            tableau.clearAdditionalDLOntology();
            return !result;
        }
    }

    public Node<OWLClass> getEquivalentClasses(OWLClassExpression classExpression) {
        HierarchyNode<AtomicConcept> node = getHierarchyNode(classExpression);
        return atomicConceptHierarchyNodeToNode(node);
    }

    public NodeSet<OWLClass> getSuperClasses(OWLClassExpression classExpression, boolean direct) {
        HierarchyNode<AtomicConcept> node = getHierarchyNode(classExpression);
        Set<HierarchyNode<AtomicConcept>> result;
        if (direct)
            result = node.getParentNodes();
        else {
            result = new HashSet<HierarchyNode<AtomicConcept>>(node.getAncestorNodes());
            result.remove(node);
        }
        return atomicConceptHierarchyNodesToNodeSet(result);
    }

    public NodeSet<OWLClass> getSubClasses(OWLClassExpression classExpression, boolean direct) {
        HierarchyNode<AtomicConcept> node = getHierarchyNode(classExpression);
        Set<HierarchyNode<AtomicConcept>> result;
        if (direct)
            result = node.getChildNodes();
        else {
            result = new HashSet<HierarchyNode<AtomicConcept>>(node.getDescendantNodes());
            result.remove(node);
        }
        return atomicConceptHierarchyNodesToNodeSet(result);
    }

    public Node<OWLClass> getUnsatisfiableClasses() {
        classifyClasses();
        HierarchyNode<AtomicConcept> node = m_atomicConceptHierarchy.getBottomNode();
        return atomicConceptHierarchyNodeToNode(node);
    }

    public NodeSet<OWLClass> getDisjointClasses(OWLClassExpression classExpression) {
        checkPreConditions(classExpression);
        classifyClasses();
        if (classExpression.isOWLNothing() || !m_isConsistent) {
            HierarchyNode<AtomicConcept> node = m_atomicConceptHierarchy.getBottomNode();
            return atomicConceptHierarchyNodesToNodeSet(node.getAncestorNodes());
        } else if (classExpression.isOWLThing()) {
            HierarchyNode<AtomicConcept> node = m_atomicConceptHierarchy.getBottomNode();
            return atomicConceptHierarchyNodesToNodeSet(Collections.singleton(node));
        } else if (classExpression instanceof OWLClass) {
            HierarchyNode<AtomicConcept> node = getHierarchyNode(classExpression);
            if (node == null || node == m_atomicConceptHierarchy.getTopNode()) {
                // fresh concept
                return new OWLClassNodeSet(getDataFactory().getOWLNothing());
            } else if (node == m_atomicConceptHierarchy.getBottomNode())
                return atomicConceptHierarchyNodesToNodeSet(node.getAncestorNodes());
            else {
                Set<HierarchyNode<AtomicConcept>> directDisjoints = getDisjointConceptNodes(node);
                Set<HierarchyNode<AtomicConcept>> result = new HashSet<HierarchyNode<AtomicConcept>>();
                for (HierarchyNode<AtomicConcept> directDisjoint : directDisjoints) {
                    result.addAll(directDisjoint.getDescendantNodes());
                }
                return atomicConceptHierarchyNodesToNodeSet(result);
            }
        } else {
            Node<OWLClass> equivalentToComplement = getEquivalentClasses(classExpression.getObjectComplementOf());
            NodeSet<OWLClass> subsDisjoint = getSubClasses(classExpression.getObjectComplementOf(), false);
            Set<Node<OWLClass>> result = new HashSet<Node<OWLClass>>();
            if (equivalentToComplement.getSize() > 0)
                result.add(equivalentToComplement);
            result.addAll(subsDisjoint.getNodes());
            return new OWLClassNodeSet(result);
        }
    }

    protected Set<HierarchyNode<AtomicConcept>> getDisjointConceptNodes(HierarchyNode<AtomicConcept> node) {
        if (m_directDisjointClasses.containsKey(node))
            return m_directDisjointClasses.get(node);
        else {
            Set<HierarchyNode<AtomicConcept>> result = new HashSet<HierarchyNode<AtomicConcept>>();
            OWLDataFactory factory = getDataFactory();
            OWLClassExpression negated = factory.getOWLObjectComplementOf(factory.getOWLClass(IRI.create(node.getRepresentative().getIRI())));
            HierarchyNode<AtomicConcept> equivalentToComplement = getHierarchyNode(negated);
            for (AtomicConcept equiv : equivalentToComplement.getEquivalentElements()) {
                if (!Prefixes.isInternalIRI(equiv.getIRI())) {
                    HierarchyNode<AtomicConcept> rootDisjoint = m_atomicConceptHierarchy.getNodeForElement(equiv);
                    result = Collections.singleton(rootDisjoint);
                    m_directDisjointClasses.put(node, result);
                    return result;
                }
            }
            result = equivalentToComplement.getChildNodes();
            m_directDisjointClasses.put(node, result);
            return result;
        }
    }

    public void precomputeDisjointClasses() {
        checkPreConditions();
        if (!m_isConsistent)
            return;
        if (m_atomicConceptHierarchy == null || m_directDisjointClasses.keySet().size() < m_atomicConceptHierarchy.getAllNodesSet().size() - 2) {
            classifyClasses();
            Set<HierarchyNode<AtomicConcept>> nodes = new HashSet<HierarchyNode<AtomicConcept>>(m_atomicConceptHierarchy.getAllNodes());
            nodes.remove(m_atomicConceptHierarchy.getTopNode());
            nodes.remove(m_atomicConceptHierarchy.getBottomNode());
            nodes.removeAll(m_directDisjointClasses.keySet());
            int steps = nodes.size();
            int step = 0;
            if (m_configuration.reasonerProgressMonitor != null)
                m_configuration.reasonerProgressMonitor.reasonerTaskStarted("Compute disjoint classes");
            for (HierarchyNode<AtomicConcept> node : nodes) {
                getDisjointConceptNodes(node);
                if (m_configuration.reasonerProgressMonitor != null)
                    m_configuration.reasonerProgressMonitor.reasonerTaskProgressChanged(++step, steps);
            }
            if (m_configuration.reasonerProgressMonitor != null)
                m_configuration.reasonerProgressMonitor.reasonerTaskStopped();
        }
    }

    protected HierarchyNode<AtomicConcept> getHierarchyNode(OWLClassExpression classExpression) {
        checkPreConditions(classExpression);
        classifyClasses();
        if (!isConsistent())
            return m_atomicConceptHierarchy.getBottomNode();
        else if (classExpression instanceof OWLClass) {
            AtomicConcept atomicConcept = H((OWLClass) classExpression);
            HierarchyNode<AtomicConcept> node = m_atomicConceptHierarchy.getNodeForElement(atomicConcept);
            if (node == null)
                node = new HierarchyNode<AtomicConcept>(atomicConcept, Collections.singleton(atomicConcept), Collections.singleton(m_atomicConceptHierarchy.getTopNode()), Collections.singleton(m_atomicConceptHierarchy.getBottomNode()));
            return node;
        } else {
            OWLDataFactory factory = getDataFactory();
            OWLClass queryConcept = factory.getOWLClass(IRI.create("internal:query-concept"));
            OWLAxiom classDefinitionAxiom = factory.getOWLEquivalentClassesAxiom(queryConcept, classExpression);
            final Tableau tableau = getTableau(classDefinitionAxiom);
            HierarchySearch.Relation<AtomicConcept> hierarchyRelation = new HierarchySearch.Relation<AtomicConcept>() {
                public boolean doesSubsume(AtomicConcept parent, AtomicConcept child) {
                    Individual freshIndividual = Individual.createAnonymous("fresh-individual");
                    return !tableau.isSatisfiable(true, Collections.singleton(Atom.create(child, freshIndividual)), null, null, Collections.singleton(Atom.create(parent, freshIndividual)), null, ReasoningTaskDescription.isConceptSubsumedBy(child, parent));
                }
            };
            HierarchyNode<AtomicConcept> extendedHierarchy = HierarchySearch.findPosition(hierarchyRelation, AtomicConcept.create("internal:query-concept"), m_atomicConceptHierarchy.getTopNode(), m_atomicConceptHierarchy.getBottomNode());
            tableau.clearAdditionalDLOntology();
            return extendedHierarchy;
        }
    }

    // Object property inferences

    public void classifyObjectProperties() {
        checkPreConditions();
        if (m_objectRoleHierarchy == null) {
            Set<Role> relevantObjectRoles = new HashSet<Role>();
            for (AtomicRole atomicRole : m_dlOntology.getAllAtomicObjectRoles()) {
                if (atomicRole != AtomicRole.TOP_OBJECT_ROLE && atomicRole != AtomicRole.BOTTOM_OBJECT_ROLE) {
                    relevantObjectRoles.add(atomicRole);
                    if (m_dlOntology.hasInverseRoles())
                        relevantObjectRoles.add(atomicRole.getInverse());
                }
            }
            if (!m_isConsistent) {
                relevantObjectRoles.add(AtomicRole.TOP_OBJECT_ROLE);
                relevantObjectRoles.add(AtomicRole.BOTTOM_OBJECT_ROLE);
                m_objectRoleHierarchy = Hierarchy.emptyHierarchy(relevantObjectRoles, AtomicRole.TOP_OBJECT_ROLE, AtomicRole.BOTTOM_OBJECT_ROLE);
            } else {
                Map<Role, AtomicConcept> conceptsForRoles = new HashMap<Role, AtomicConcept>();
                final Map<AtomicConcept, Role> rolesForConcepts = new HashMap<AtomicConcept, Role>();
                // Create the additional axioms for classification
                List<OWLAxiom> additionalAxioms = new ArrayList<OWLAxiom>();
                OWLDataFactory factory = getDataFactory();
                OWLClass freshConcept = factory.getOWLClass(IRI.create("internal:fresh-concept"));
                for (Role objectRole : relevantObjectRoles) {
                    AtomicConcept conceptForRole;
                    OWLObjectPropertyExpression objectPropertyExpression;
                    if (objectRole instanceof AtomicRole) {
                        conceptForRole = AtomicConcept.create("internal:prop#" + ((AtomicRole) objectRole).getIRI());
                        objectPropertyExpression = factory.getOWLObjectProperty(IRI.create(((AtomicRole) objectRole).getIRI()));
                    } else {
                        conceptForRole = AtomicConcept.create("internal:prop#inv#" + ((InverseRole) objectRole).getInverseOf().getIRI());
                        objectPropertyExpression = factory.getOWLObjectInverseOf(factory.getOWLObjectProperty(IRI.create(((InverseRole) objectRole).getInverseOf().getIRI())));
                    }
                    OWLAxiom axiom;
                    OWLClass classForRole = factory.getOWLClass(IRI.create(conceptForRole.getIRI()));
                    axiom = factory.getOWLEquivalentClassesAxiom(classForRole, factory.getOWLObjectSomeValuesFrom(objectPropertyExpression, freshConcept));
                    additionalAxioms.add(axiom);
                    conceptsForRoles.put(objectRole, conceptForRole);
                    rolesForConcepts.put(conceptForRole, objectRole);
                }
                // handle top & bottom case
                conceptsForRoles.put(AtomicRole.TOP_OBJECT_ROLE, AtomicConcept.THING);
                rolesForConcepts.put(AtomicConcept.THING, AtomicRole.TOP_OBJECT_ROLE);
                conceptsForRoles.put(AtomicRole.BOTTOM_OBJECT_ROLE, AtomicConcept.NOTHING);
                rolesForConcepts.put(AtomicConcept.NOTHING, AtomicRole.BOTTOM_OBJECT_ROLE);
                OWLIndividual freshIndividual = factory.getOWLAnonymousIndividual();
                OWLAxiom axiom = factory.getOWLClassAssertionAxiom(freshConcept, freshIndividual);
                additionalAxioms.add(axiom);
                OWLAxiom[] additionalAxiomsArray = new OWLAxiom[additionalAxioms.size()];
                additionalAxioms.toArray(additionalAxiomsArray);
                // Run the actual classification task
                Tableau tableau = getTableau(additionalAxiomsArray);
                try {
                    final int numberOfRoles = relevantObjectRoles.size();
                    if (m_configuration.reasonerProgressMonitor != null)
                        m_configuration.reasonerProgressMonitor.reasonerTaskStarted("Classifying object properties...");
                    ClassificationProgressMonitor progressMonitor = new ClassificationProgressMonitor() {
                        protected int m_processedRoles = 0;

                        public void elementClassified(AtomicConcept element) {
                            m_processedRoles++;
                            if (m_configuration.reasonerProgressMonitor != null)
                                m_configuration.reasonerProgressMonitor.reasonerTaskProgressChanged(m_processedRoles, numberOfRoles);
                        }
                    };
                    Hierarchy<AtomicConcept> atomicConceptHierarchyForRoles = classifyAtomicConceptsForRoles(tableau, progressMonitor, conceptsForRoles.get(AtomicRole.TOP_OBJECT_ROLE), conceptsForRoles.get(AtomicRole.BOTTOM_OBJECT_ROLE), rolesForConcepts.keySet(), m_dlOntology.hasInverseRoles(), conceptsForRoles, rolesForConcepts, m_configuration.forceQuasiOrderClassification);
                    Hierarchy.Transformer<AtomicConcept, Role> transformer = new Hierarchy.Transformer<AtomicConcept, Role>() {
                        public Role transform(AtomicConcept atomicConcept) {
                            return rolesForConcepts.get(atomicConcept);
                        }

                        public Role determineRepresentative(AtomicConcept oldRepresentative, Set<Role> newEquivalentElements) {
                            return transform(oldRepresentative);
                        }
                    };
                    m_objectRoleHierarchy = atomicConceptHierarchyForRoles.transform(transformer, null);
                    if (m_instanceManager != null)
                        m_instanceManager.setToClassifiedRoleHierarchy(m_objectRoleHierarchy);
                } finally {
                    tableau.clearAdditionalDLOntology();
                    if (m_configuration.reasonerProgressMonitor != null)
                        m_configuration.reasonerProgressMonitor.reasonerTaskStopped();
                }
            }
        }
    }

    public Node<OWLObjectPropertyExpression> getTopObjectPropertyNode() {
        classifyObjectProperties();
        return objectPropertyHierarchyNodeToNode(m_objectRoleHierarchy.getTopNode());
    }

    public Node<OWLObjectPropertyExpression> getBottomObjectPropertyNode() {
        classifyObjectProperties();
        return objectPropertyHierarchyNodeToNode(m_objectRoleHierarchy.getBottomNode());
    }

    protected boolean isSubObjectPropertyExpressionOf(OWLObjectPropertyExpression subObjectPropertyExpression, OWLObjectPropertyExpression superObjectPropertyExpression) {
        checkPreConditions(subObjectPropertyExpression, superObjectPropertyExpression);
        if (!m_isConsistent || subObjectPropertyExpression.getNamedProperty().isOWLBottomObjectProperty() || superObjectPropertyExpression.getNamedProperty().isOWLTopObjectProperty())
            return true;
        Role subrole = H(subObjectPropertyExpression);
        Role superrole = H(superObjectPropertyExpression);
        if (m_objectRoleHierarchy != null && !containsFreshEntities(subObjectPropertyExpression, superObjectPropertyExpression)) {
            HierarchyNode<Role> subroleNode = m_objectRoleHierarchy.getNodeForElement(subrole);
            return subroleNode.isEquivalentElement(superrole) || subroleNode.isAncestorElement(superrole);
        } else {
            OWLDataFactory factory = getDataFactory();
            OWLClass pseudoNominal = factory.getOWLClass(IRI.create("internal:pseudo-nominal"));
            OWLClassExpression allSuperNotPseudoNominal = factory.getOWLObjectAllValuesFrom(superObjectPropertyExpression, pseudoNominal.getObjectComplementOf());
            OWLIndividual freshIndividualA = factory.getOWLAnonymousIndividual("fresh-individual-A");
            OWLIndividual freshIndividualB = factory.getOWLAnonymousIndividual("fresh-individual-B");
            OWLAxiom subObjectPropertyAssertion = factory.getOWLObjectPropertyAssertionAxiom(subObjectPropertyExpression, freshIndividualA, freshIndividualB);
            OWLAxiom pseudoNominalAssertion = factory.getOWLClassAssertionAxiom(pseudoNominal, freshIndividualB);
            OWLAxiom allSuperNotPseudoNominalAssertion = factory.getOWLClassAssertionAxiom(allSuperNotPseudoNominal, freshIndividualA);
            Tableau tableau = getTableau(subObjectPropertyAssertion, pseudoNominalAssertion, allSuperNotPseudoNominalAssertion);
            boolean result = tableau.isSatisfiable(true, null, null, null, null, null, ReasoningTaskDescription.isRoleSubsumedBy(subrole, superrole, true));
            tableau.clearAdditionalDLOntology();
            return !result;
        }
    }

    protected boolean isSubObjectPropertyExpressionOf(List<OWLObjectPropertyExpression> subPropertyChain, OWLObjectPropertyExpression superObjectPropertyExpression) {
        OWLObject[] objects = new OWLObject[subPropertyChain.size() + 1];
        for (int i = 0; i < subPropertyChain.size(); i++)
            objects[i] = subPropertyChain.get(i);
        objects[subPropertyChain.size()] = superObjectPropertyExpression;
        checkPreConditions(objects);
        if (!m_isConsistent || superObjectPropertyExpression.getNamedProperty().isOWLTopObjectProperty())
            return true;
        else {
            OWLDataFactory factory = getDataFactory();
            OWLClass pseudoNominal = factory.getOWLClass(IRI.create("internal:pseudo-nominal"));
            OWLClassExpression allSuperNotPseudoNominal = factory.getOWLObjectAllValuesFrom(superObjectPropertyExpression, pseudoNominal.getObjectComplementOf());
            OWLAxiom[] additionalAxioms = new OWLAxiom[subPropertyChain.size() + 2];
            int axiomIndex = 0;
            for (OWLObjectPropertyExpression subObjectPropertyExpression : subPropertyChain) {
                OWLIndividual first = factory.getOWLAnonymousIndividual("fresh-individual-" + axiomIndex);
                OWLIndividual second = factory.getOWLAnonymousIndividual("fresh-individual-" + (axiomIndex + 1));
                additionalAxioms[axiomIndex++] = factory.getOWLObjectPropertyAssertionAxiom(subObjectPropertyExpression, first, second);
            }
            OWLIndividual freshIndividual0 = factory.getOWLAnonymousIndividual("fresh-individual-0");
            OWLIndividual freshIndividualN = factory.getOWLAnonymousIndividual("fresh-individual-" + subPropertyChain.size());
            additionalAxioms[axiomIndex++] = factory.getOWLClassAssertionAxiom(pseudoNominal, freshIndividualN);
            additionalAxioms[axiomIndex++] = factory.getOWLClassAssertionAxiom(allSuperNotPseudoNominal, freshIndividual0);
            Tableau tableau = getTableau(additionalAxioms);
            return !tableau.isSatisfiable(true, null, null, null, null, null, new ReasoningTaskDescription(true, "subproperty chain subsumption"));
        }
    }

    public NodeSet<OWLObjectPropertyExpression> getSuperObjectProperties(OWLObjectPropertyExpression propertyExpression, boolean direct) {
        HierarchyNode<Role> node = getHierarchyNode(propertyExpression);
        Set<HierarchyNode<Role>> result = new HashSet<HierarchyNode<Role>>();
        if (direct)
            for (HierarchyNode<Role> n : node.getParentNodes())
                result.add(n);
        else {
            result = node.getAncestorNodes();
            result.remove(node);
        }
        return objectPropertyHierarchyNodesToNodeSet(result);
    }

    public NodeSet<OWLObjectPropertyExpression> getSubObjectProperties(OWLObjectPropertyExpression propertyExpression, boolean direct) {
        HierarchyNode<Role> node = getHierarchyNode(propertyExpression);
        Set<HierarchyNode<Role>> result = new HashSet<HierarchyNode<Role>>();
        if (direct)
            for (HierarchyNode<Role> n : node.getChildNodes())
                result.add(n);
        else {
            result = node.getDescendantNodes();
            result.remove(node);
        }
        return objectPropertyHierarchyNodesToNodeSet(result);
    }

    public Node<OWLObjectPropertyExpression> getEquivalentObjectProperties(OWLObjectPropertyExpression propertyExpression) {
        return objectPropertyHierarchyNodeToNode(getHierarchyNode(propertyExpression));
    }

    public NodeSet<OWLClass> getObjectPropertyDomains(OWLObjectPropertyExpression propertyExpression, boolean direct) {
        checkPreConditions(propertyExpression);
        classifyClasses();
        if (!isConsistent())
            return new OWLClassNodeSet(getBottomClassNode());
        final Role role = H(propertyExpression);
        Set<HierarchyNode<AtomicConcept>> nodes = m_directObjectRoleDomains.get(role);
        if (nodes == null) {
            final Individual freshIndividualA = Individual.createAnonymous("fresh-individual-A");
            final Individual freshIndividualB = Individual.createAnonymous("fresh-individual-B");
            final Set<Atom> roleAssertion = Collections.singleton(role.getRoleAssertion(freshIndividualA, freshIndividualB));
            final Tableau tableau = getTableau();
            HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>> searchPredicate = new HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>>() {
                public Set<HierarchyNode<AtomicConcept>> getSuccessorElements(HierarchyNode<AtomicConcept> u) {
                    return u.getChildNodes();
                }

                public Set<HierarchyNode<AtomicConcept>> getPredecessorElements(HierarchyNode<AtomicConcept> u) {
                    return u.getParentNodes();
                }

                public boolean trueOf(HierarchyNode<AtomicConcept> u) {
                    AtomicConcept potentialDomainConcept = u.getRepresentative();
                    return !tableau.isSatisfiable(false, roleAssertion, Collections.singleton(Atom.create(potentialDomainConcept, freshIndividualA)), null, null, null, ReasoningTaskDescription.isDomainOf(potentialDomainConcept, role));
                }
            };
            nodes = HierarchySearch.search(searchPredicate, Collections.singleton(m_atomicConceptHierarchy.getTopNode()), null);
            m_directObjectRoleDomains.put(role, nodes);
        }
        if (!direct)
            nodes = HierarchyNode.getAncestorNodes(nodes);
        return atomicConceptHierarchyNodesToNodeSet(nodes);
    }

    public NodeSet<OWLClass> getObjectPropertyRanges(OWLObjectPropertyExpression propertyExpression, boolean direct) {
        checkPreConditions(propertyExpression);
        classifyClasses();
        if (!isConsistent())
            return new OWLClassNodeSet(getBottomClassNode());
        final Role role = H(propertyExpression);
        Set<HierarchyNode<AtomicConcept>> nodes = m_directObjectRoleRanges.get(role);
        if (nodes == null) {
            final Individual freshIndividualA = Individual.createAnonymous("fresh-individual-A");
            final Individual freshIndividualB = Individual.createAnonymous("fresh-individual-B");
            final Set<Atom> roleAssertion = Collections.singleton(role.getRoleAssertion(freshIndividualA, freshIndividualB));
            final Tableau tableau = getTableau();
            HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>> searchPredicate = new HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>>() {
                public Set<HierarchyNode<AtomicConcept>> getSuccessorElements(HierarchyNode<AtomicConcept> u) {
                    return u.getChildNodes();
                }

                public Set<HierarchyNode<AtomicConcept>> getPredecessorElements(HierarchyNode<AtomicConcept> u) {
                    return u.getParentNodes();
                }

                public boolean trueOf(HierarchyNode<AtomicConcept> u) {
                    AtomicConcept potentialRangeConcept = u.getRepresentative();
                    return !tableau.isSatisfiable(false, roleAssertion, Collections.singleton(Atom.create(potentialRangeConcept, freshIndividualB)), null, null, null, ReasoningTaskDescription.isRangeOf(potentialRangeConcept, role));
                }
            };
            nodes = HierarchySearch.search(searchPredicate, Collections.singleton(m_atomicConceptHierarchy.getTopNode()), null);
            m_directObjectRoleRanges.put(role, nodes);
        }
        if (!direct)
            nodes = HierarchyNode.getAncestorNodes(nodes);
        return atomicConceptHierarchyNodesToNodeSet(nodes);
    }

    public Node<OWLObjectPropertyExpression> getInverseObjectProperties(OWLObjectPropertyExpression propertyExpression) {
        return getEquivalentObjectProperties(propertyExpression.getSimplified().getInverseProperty());
    }

    public NodeSet<OWLObjectPropertyExpression> getDisjointObjectProperties(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent)
            return new OWLObjectPropertyNodeSet();
        classifyObjectProperties();
        Set<HierarchyNode<Role>> result = new HashSet<HierarchyNode<Role>>();
        if (propertyExpression.getNamedProperty().isOWLTopObjectProperty()) {
            result.add(m_objectRoleHierarchy.getBottomNode());
            return objectPropertyHierarchyNodesToNodeSet(result);
        } else if (propertyExpression.isOWLBottomObjectProperty()) {
            HierarchyNode<Role> node = m_objectRoleHierarchy.getTopNode();
            result.add(node);
            result.addAll(node.getDescendantNodes());
            return objectPropertyHierarchyNodesToNodeSet(result);
        }
        Role role = H(propertyExpression);
        Individual freshIndividualA = Individual.createAnonymous("fresh-individual-A");
        Individual freshIndividualB = Individual.createAnonymous("fresh-individual-B");
        Atom roleAssertion = role.getRoleAssertion(freshIndividualA, freshIndividualB);
        Tableau tableau = getTableau();
        Set<HierarchyNode<Role>> nodesToTest = new HashSet<HierarchyNode<Role>>();
        nodesToTest.addAll(m_objectRoleHierarchy.getTopNode().getChildNodes());
        while (!nodesToTest.isEmpty()) {
            HierarchyNode<Role> nodeToTest = nodesToTest.iterator().next();
            nodesToTest.remove(nodeToTest);
            Role roleToTest = nodeToTest.getRepresentative();
            Atom roleToTestAssertion = roleToTest.getRoleAssertion(freshIndividualA, freshIndividualB);
            Set<Atom> perTestAtoms = new HashSet<Atom>(2);
            perTestAtoms.add(roleAssertion);
            perTestAtoms.add(roleToTestAssertion);
            if (!tableau.isSatisfiable(false, perTestAtoms, null, null, null, null, new ReasoningTaskDescription(true, "disjointness of {0} and {1}", role, roleToTest)))
                // disjoint
                result.addAll(nodeToTest.getDescendantNodes());
            else
                // maybe some children are disjoint
                nodesToTest.addAll(nodeToTest.getChildNodes());
        }
        if (result.isEmpty())
            result.add(m_objectRoleHierarchy.getBottomNode());
        return objectPropertyHierarchyNodesToNodeSet(result);
    }

    protected boolean isDisjointObjectProperty(OWLObjectPropertyExpression propertyExpression1, OWLObjectPropertyExpression propertyExpression2) {
        checkPreConditions(propertyExpression1, propertyExpression2);
        if (!m_isConsistent)
            return true;
        Role role1 = H(propertyExpression1);
        Role role2 = H(propertyExpression2);
        Individual freshIndividualA = Individual.createAnonymous("fresh-individual-A");
        Individual freshIndividualB = Individual.createAnonymous("fresh-individual-B");
        Atom roleAssertion1 = role1.getRoleAssertion(freshIndividualA, freshIndividualB);
        Atom roleAssertion2 = role2.getRoleAssertion(freshIndividualA, freshIndividualB);
        Set<Atom> perTestAtoms = new HashSet<Atom>(2);
        perTestAtoms.add(roleAssertion1);
        perTestAtoms.add(roleAssertion2);
        return !getTableau().isSatisfiable(false, perTestAtoms, null, null, null, null, new ReasoningTaskDescription(true, "disjointness of {0} and {1}", role1, role2));
    }

    protected boolean isFunctional(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent)
            return true;
        Role role = H(propertyExpression);
        Individual freshIndividual = Individual.createAnonymous("fresh-individual");
        Individual freshIndividualA = Individual.createAnonymous("fresh-individual-A");
        Individual freshIndividualB = Individual.createAnonymous("fresh-individual-B");
        Set<Atom> assertions = new HashSet<Atom>();
        assertions.add(role.getRoleAssertion(freshIndividual, freshIndividualA));
        assertions.add(role.getRoleAssertion(freshIndividual, freshIndividualB));
        assertions.add(Atom.create(Inequality.INSTANCE, freshIndividualA, freshIndividualB));
        return !getTableau().isSatisfiable(false, assertions, null, null, null, null, new ReasoningTaskDescription(true, "functionality of {0}", role));
    }

    protected boolean isInverseFunctional(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent)
            return true;
        Role role = H(propertyExpression);
        Individual freshIndividual = Individual.createAnonymous("fresh-individual");
        Individual freshIndividualA = Individual.createAnonymous("fresh-individual-A");
        Individual freshIndividualB = Individual.createAnonymous("fresh-individual-B");
        Set<Atom> assertions = new HashSet<Atom>();
        assertions.add(role.getRoleAssertion(freshIndividualA, freshIndividual));
        assertions.add(role.getRoleAssertion(freshIndividualB, freshIndividual));
        assertions.add(Atom.create(Inequality.INSTANCE, freshIndividualA, freshIndividualB));
        return !getTableau().isSatisfiable(false, assertions, null, null, null, null, new ReasoningTaskDescription(true, "inverse-functionality of {0}", role));
    }

    protected boolean isIrreflexive(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent)
            return true;
        Role role = H(propertyExpression);
        Individual freshIndividual = Individual.createAnonymous("fresh-individual");
        return !getTableau().isSatisfiable(false, Collections.singleton(role.getRoleAssertion(freshIndividual, freshIndividual)), null, null, null, null, new ReasoningTaskDescription(true, "irreflexivity of {0}", role));
    }

    protected boolean isReflexive(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent)
            return true;
        OWLDataFactory factory = getDataFactory();
        OWLClass pseudoNominal = factory.getOWLClass(IRI.create("internal:pseudo-nominal"));
        OWLClassExpression allNotPseudoNominal = factory.getOWLObjectAllValuesFrom(propertyExpression, pseudoNominal.getObjectComplementOf());
        OWLIndividual freshIndividual = factory.getOWLAnonymousIndividual("fresh-individual");
        OWLAxiom pseudoNominalAssertion = factory.getOWLClassAssertionAxiom(pseudoNominal, freshIndividual);
        OWLAxiom allNotPseudoNominalAssertion = factory.getOWLClassAssertionAxiom(allNotPseudoNominal, freshIndividual);
        Tableau tableau = getTableau(pseudoNominalAssertion, allNotPseudoNominalAssertion);
        boolean result = tableau.isSatisfiable(true, null, null, null, null, null, new ReasoningTaskDescription(true, "symmetry of {0}", H(propertyExpression)));
        tableau.clearAdditionalDLOntology();
        return !result;
    }

    protected boolean isAsymmetric(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent)
            return true;
        OWLDataFactory factory = getDataFactory();
        OWLIndividual freshIndividualA = factory.getOWLAnonymousIndividual("fresh-individual-A");
        OWLIndividual freshIndividualB = factory.getOWLAnonymousIndividual("fresh-individual-B");
        OWLAxiom assertion1 = factory.getOWLObjectPropertyAssertionAxiom(propertyExpression, freshIndividualA, freshIndividualB);
        OWLAxiom assertion2 = factory.getOWLObjectPropertyAssertionAxiom(propertyExpression.getInverseProperty(), freshIndividualA, freshIndividualB);
        Tableau tableau = getTableau(assertion1, assertion2);
        boolean result = tableau.isSatisfiable(true, null, null, null, null, null, new ReasoningTaskDescription(true, "asymmetry of {0}", H(propertyExpression)));
        tableau.clearAdditionalDLOntology();
        return !result;
    }

    protected boolean isSymmetric(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent || propertyExpression.getNamedProperty().isOWLTopObjectProperty())
            return true;
        OWLDataFactory factory = getDataFactory();
        OWLClass pseudoNominal = factory.getOWLClass(IRI.create("internal:pseudo-nominal"));
        OWLClassExpression allNotPseudoNominal = factory.getOWLObjectAllValuesFrom(propertyExpression, pseudoNominal.getObjectComplementOf());
        OWLIndividual freshIndividualA = factory.getOWLAnonymousIndividual("fresh-individual-A");
        OWLIndividual freshIndividualB = factory.getOWLAnonymousIndividual("fresh-individual-B");
        OWLAxiom assertion1 = factory.getOWLObjectPropertyAssertionAxiom(propertyExpression, freshIndividualA, freshIndividualB);
        OWLAxiom assertion2 = factory.getOWLClassAssertionAxiom(allNotPseudoNominal, freshIndividualB);
        OWLAxiom assertion3 = factory.getOWLClassAssertionAxiom(pseudoNominal, freshIndividualA);
        Tableau tableau = getTableau(assertion1, assertion2, assertion3);
        boolean result = tableau.isSatisfiable(true, null, null, null, null, null, new ReasoningTaskDescription(true, "symmetry of {0}", propertyExpression));
        tableau.clearAdditionalDLOntology();
        return !result;
    }

    protected boolean isTransitive(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (!m_isConsistent)
            return true;
        OWLDataFactory factory = getDataFactory();
        OWLClass pseudoNominal = factory.getOWLClass(IRI.create("internal:pseudo-nominal"));
        OWLClassExpression allNotPseudoNominal = factory.getOWLObjectAllValuesFrom(propertyExpression, pseudoNominal.getObjectComplementOf());
        OWLIndividual freshIndividualA = factory.getOWLAnonymousIndividual("fresh-individual-A");
        OWLIndividual freshIndividualB = factory.getOWLAnonymousIndividual("fresh-individual-B");
        OWLIndividual freshIndividualC = factory.getOWLAnonymousIndividual("fresh-individual-C");
        OWLAxiom assertion1 = factory.getOWLObjectPropertyAssertionAxiom(propertyExpression, freshIndividualA, freshIndividualB);
        OWLAxiom assertion2 = factory.getOWLObjectPropertyAssertionAxiom(propertyExpression, freshIndividualB, freshIndividualC);
        OWLAxiom assertion3 = factory.getOWLClassAssertionAxiom(allNotPseudoNominal, freshIndividualA);
        OWLAxiom assertion4 = factory.getOWLClassAssertionAxiom(pseudoNominal, freshIndividualC);
        Tableau tableau = getTableau(assertion1, assertion2, assertion3, assertion4);
        boolean result = tableau.isSatisfiable(true, null, null, null, null, null, new ReasoningTaskDescription(true, "transitivity of {0}", H(propertyExpression)));
        tableau.clearAdditionalDLOntology();
        return !result;
    }

    protected HierarchyNode<Role> getHierarchyNode(OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        classifyObjectProperties();
        if (!m_isConsistent)
            return m_objectRoleHierarchy.getBottomNode();
        else {
            Role role = H(propertyExpression);
            HierarchyNode<Role> node = m_objectRoleHierarchy.getNodeForElement(role);
            if (node == null)
                node = new HierarchyNode<Role>(role, Collections.singleton(role), Collections.singleton(m_objectRoleHierarchy.getTopNode()), Collections.singleton(m_objectRoleHierarchy.getBottomNode()));
            return node;
        }
    }

    // Data property inferences

    public void classifyDataProperties() {
        checkPreConditions();
        if (m_dataRoleHierarchy == null) {
            Set<AtomicRole> relevantDataRoles = new HashSet<AtomicRole>();
            relevantDataRoles.add(AtomicRole.TOP_DATA_ROLE);
            relevantDataRoles.add(AtomicRole.BOTTOM_DATA_ROLE);
            relevantDataRoles.addAll(m_dlOntology.getAllAtomicDataRoles());
            if (!m_isConsistent)
                m_dataRoleHierarchy = Hierarchy.emptyHierarchy(relevantDataRoles, AtomicRole.TOP_DATA_ROLE, AtomicRole.BOTTOM_DATA_ROLE);
            else {
                if (m_dlOntology.hasDatatypes()) {
                    Map<AtomicRole, AtomicConcept> conceptsForRoles = new HashMap<AtomicRole, AtomicConcept>();
                    final Map<AtomicConcept, AtomicRole> rolesForConcepts = new HashMap<AtomicConcept, AtomicRole>();
                    // Create the additional axioms for classification
                    List<OWLAxiom> additionalAxioms = new ArrayList<OWLAxiom>();
                    OWLDataFactory factory = getDataFactory();
                    OWLDatatype unknownDatatypeA = factory.getOWLDatatype(IRI.create("internal:unknown-datatype#A"));
                    for (AtomicRole dataRole : relevantDataRoles) {
                        AtomicConcept conceptForRole;
                        if (AtomicRole.TOP_DATA_ROLE.equals(dataRole))
                            conceptForRole = AtomicConcept.THING;
                        else if (AtomicRole.BOTTOM_DATA_ROLE.equals(dataRole))
                            conceptForRole = AtomicConcept.NOTHING;
                        else {
                            conceptForRole = AtomicConcept.create("internal:prop#" + dataRole.getIRI());
                            OWLClass classForRole = factory.getOWLClass(IRI.create(conceptForRole.getIRI()));
                            OWLDataProperty dataProperty = factory.getOWLDataProperty(IRI.create(dataRole.getIRI()));
                            OWLAxiom axiom = factory.getOWLEquivalentClassesAxiom(classForRole, factory.getOWLDataSomeValuesFrom(dataProperty, unknownDatatypeA));
                            additionalAxioms.add(axiom);
                        }
                        conceptsForRoles.put(dataRole, conceptForRole);
                        rolesForConcepts.put(conceptForRole, dataRole);
                    }
                    OWLAxiom[] additionalAxiomsArray = new OWLAxiom[additionalAxioms.size()];
                    additionalAxioms.toArray(additionalAxiomsArray);
                    // Run the actual classification task
                    Tableau tableau = getTableau(additionalAxiomsArray);
                    try {
                        final int numberOfRoles = relevantDataRoles.size();
                        if (m_configuration.reasonerProgressMonitor != null)
                            m_configuration.reasonerProgressMonitor.reasonerTaskStarted("Classifying data properties...");
                        ClassificationProgressMonitor progressMonitor = new ClassificationProgressMonitor() {
                            protected int m_processedRoles = 0;

                            public void elementClassified(AtomicConcept element) {
                                m_processedRoles++;
                                if (m_configuration.reasonerProgressMonitor != null)
                                    m_configuration.reasonerProgressMonitor.reasonerTaskProgressChanged(m_processedRoles, numberOfRoles);
                            }
                        };
                        Hierarchy<AtomicConcept> atomicConceptHierarchyForRoles = classifyAtomicConcepts(tableau, progressMonitor, conceptsForRoles.get(AtomicRole.TOP_DATA_ROLE), conceptsForRoles.get(AtomicRole.BOTTOM_DATA_ROLE), rolesForConcepts.keySet(), m_configuration.forceQuasiOrderClassification);
                        Hierarchy.Transformer<AtomicConcept, AtomicRole> transformer = new Hierarchy.Transformer<AtomicConcept, AtomicRole>() {
                            public AtomicRole transform(AtomicConcept atomicConcept) {
                                return rolesForConcepts.get(atomicConcept);
                            }

                            public AtomicRole determineRepresentative(AtomicConcept oldRepresentative, Set<AtomicRole> newEquivalentElements) {
                                return transform(oldRepresentative);
                            }
                        };
                        m_dataRoleHierarchy = atomicConceptHierarchyForRoles.transform(transformer, null);
                    } finally {
                        tableau.clearAdditionalDLOntology();
                        if (m_configuration.reasonerProgressMonitor != null)
                            m_configuration.reasonerProgressMonitor.reasonerTaskStopped();
                    }
                } else
                    m_dataRoleHierarchy = Hierarchy.trivialHierarchy(AtomicRole.TOP_DATA_ROLE, AtomicRole.BOTTOM_DATA_ROLE);
            }
        }
    }

    public Node<OWLDataProperty> getTopDataPropertyNode() {
        classifyDataProperties();
        return dataPropertyHierarchyNodeToNode(m_dataRoleHierarchy.getTopNode());
    }

    public Node<OWLDataProperty> getBottomDataPropertyNode() {
        classifyDataProperties();
        return dataPropertyHierarchyNodeToNode(m_dataRoleHierarchy.getBottomNode());
    }

    protected boolean isSubDataPropertyOf(OWLDataProperty subDataProperty, OWLDataProperty superDataProperty) {
        checkPreConditions(subDataProperty, superDataProperty);
        if (!m_isConsistent || subDataProperty.isOWLBottomDataProperty() || superDataProperty.isOWLTopDataProperty())
            return true;
        AtomicRole subrole = H(subDataProperty);
        AtomicRole superrole = H(superDataProperty);
        if (m_dataRoleHierarchy != null && !containsFreshEntities(subDataProperty, superDataProperty)) {
            HierarchyNode<AtomicRole> subroleNode = m_dataRoleHierarchy.getNodeForElement(subrole);
            return subroleNode.isEquivalentElement(superrole) || subroleNode.isAncestorElement(superrole);
        } else {
            OWLDataFactory factory = getDataFactory();
            OWLIndividual individual = factory.getOWLAnonymousIndividual("fresh-individual");
            OWLLiteral freshConstant = factory.getOWLLiteral("internal:fresh-constant", factory.getOWLDatatype(IRI.create("internal:anonymous-constants")));
            OWLDataProperty negatedSuperDataProperty = factory.getOWLDataProperty(IRI.create("internal:negated-superproperty"));
            OWLAxiom subpropertyAssertion = factory.getOWLDataPropertyAssertionAxiom(subDataProperty, individual, freshConstant);
            OWLAxiom negatedSuperpropertyAssertion = factory.getOWLDataPropertyAssertionAxiom(negatedSuperDataProperty, individual, freshConstant);
            OWLAxiom superpropertyAxiomatization = factory.getOWLDisjointDataPropertiesAxiom(superDataProperty, negatedSuperDataProperty);
            Tableau tableau = getTableau(subpropertyAssertion, negatedSuperpropertyAssertion, superpropertyAxiomatization);
            boolean result = tableau.isSatisfiable(true, null, null, null, null, null, ReasoningTaskDescription.isRoleSubsumedBy(subrole, superrole, false));
            tableau.clearAdditionalDLOntology();
            return !result;
        }
    }

    public NodeSet<OWLDataProperty> getSuperDataProperties(OWLDataProperty property, boolean direct) {
        HierarchyNode<AtomicRole> node = getHierarchyNode(property);
        Set<HierarchyNode<AtomicRole>> result;
        if (direct)
            result = node.getParentNodes();
        else {
            result = new HashSet<HierarchyNode<AtomicRole>>(node.getAncestorNodes());
            result.remove(node);
        }
        return dataPropertyHierarchyNodesToNodeSet(result);
    }

    public NodeSet<OWLDataProperty> getSubDataProperties(OWLDataProperty property, boolean direct) {
        HierarchyNode<AtomicRole> node = getHierarchyNode(property);
        Set<HierarchyNode<AtomicRole>> result;
        if (direct)
            result = node.getChildNodes();
        else {
            result = new HashSet<HierarchyNode<AtomicRole>>(node.getDescendantNodes());
            result.remove(node);
        }
        return dataPropertyHierarchyNodesToNodeSet(result);
    }

    public Node<OWLDataProperty> getEquivalentDataProperties(OWLDataProperty property) {
        return dataPropertyHierarchyNodeToNode(getHierarchyNode(property));
    }

    public NodeSet<OWLClass> getDataPropertyDomains(OWLDataProperty property, boolean direct) {
        checkPreConditions(property);
        classifyClasses();
        if (!m_isConsistent)
            return new OWLClassNodeSet(getBottomClassNode());
        final AtomicRole atomicRole = H(property);
        Set<HierarchyNode<AtomicConcept>> nodes = m_directDataRoleDomains.get(atomicRole);
        if (nodes == null) {
            final Individual freshIndividual = Individual.createAnonymous("fresh-individual");
            final Constant freshConstant = Constant.createAnonymous("fresh-constant");
            final Set<Atom> roleAssertion = Collections.singleton(atomicRole.getRoleAssertion(freshIndividual, freshConstant));
            final Tableau tableau = getTableau();
            HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>> searchPredicate = new HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>>() {
                public Set<HierarchyNode<AtomicConcept>> getSuccessorElements(HierarchyNode<AtomicConcept> u) {
                    return u.getChildNodes();
                }

                public Set<HierarchyNode<AtomicConcept>> getPredecessorElements(HierarchyNode<AtomicConcept> u) {
                    return u.getParentNodes();
                }

                public boolean trueOf(HierarchyNode<AtomicConcept> u) {
                    AtomicConcept potentialDomainConcept = u.getRepresentative();
                    return !tableau.isSatisfiable(false, roleAssertion, Collections.singleton(Atom.create(potentialDomainConcept, freshIndividual)), null, null, null, ReasoningTaskDescription.isDomainOf(potentialDomainConcept, atomicRole));
                }
            };
            nodes = HierarchySearch.search(searchPredicate, Collections.singleton(m_atomicConceptHierarchy.getTopNode()), null);
            m_directDataRoleDomains.put(atomicRole, nodes);
        }
        if (!direct)
            nodes = HierarchyNode.getAncestorNodes(nodes);
        return atomicConceptHierarchyNodesToNodeSet(nodes);
    }

    public NodeSet<OWLDataProperty> getDisjointDataProperties(OWLDataPropertyExpression propertyExpression) {
        checkPreConditions(propertyExpression);
        if (m_dlOntology.hasDatatypes()) {
            classifyDataProperties();
            if (!m_isConsistent)
                return new OWLDataPropertyNodeSet();
            Set<HierarchyNode<AtomicRole>> result = new HashSet<HierarchyNode<AtomicRole>>();
            if (propertyExpression.isOWLTopDataProperty()) {
                result.add(m_dataRoleHierarchy.getBottomNode());
                return dataPropertyHierarchyNodesToNodeSet(result);
            } else if (propertyExpression.isOWLBottomDataProperty()) {
                HierarchyNode<AtomicRole> node = m_dataRoleHierarchy.getTopNode();
                result.add(node);
                result.addAll(node.getDescendantNodes());
                return dataPropertyHierarchyNodesToNodeSet(result);
            }
            AtomicRole atomicRole = H(propertyExpression.asOWLDataProperty());
            Individual freshIndividual = Individual.create("fresh-individual");
            Constant freshConstant = Constant.createAnonymous("fresh-constant");
            Atom atomicRoleAssertion = atomicRole.getRoleAssertion(freshIndividual, freshConstant);
            Tableau tableau = getTableau();
            Set<HierarchyNode<AtomicRole>> nodesToTest = new HashSet<HierarchyNode<AtomicRole>>();
            nodesToTest.addAll(m_dataRoleHierarchy.getTopNode().getChildNodes());
            while (!nodesToTest.isEmpty()) {
                HierarchyNode<AtomicRole> nodeToTest = nodesToTest.iterator().next();
                nodesToTest.remove(nodeToTest);
                AtomicRole atomicRoleToTest = nodeToTest.getRepresentative();
                Atom atomicRoleToTestAssertion = atomicRoleToTest.getRoleAssertion(freshIndividual, freshConstant);
                Set<Atom> perTestAtoms = new HashSet<Atom>(2);
                perTestAtoms.add(atomicRoleAssertion);
                perTestAtoms.add(atomicRoleToTestAssertion);
                if (!tableau.isSatisfiable(false, perTestAtoms, null, null, null, null, new ReasoningTaskDescription(true, "disjointness of {0} and {1}", atomicRole, atomicRoleToTest)))
                    // disjoint
                    result.addAll(nodeToTest.getDescendantNodes());
                else
                    // maybe some children are disjoint
                    nodesToTest.addAll(nodeToTest.getChildNodes());
            }
            if (result.isEmpty())
                result.add(m_dataRoleHierarchy.getBottomNode());
            return dataPropertyHierarchyNodesToNodeSet(result);
        } else {
            OWLDataFactory factory = getDataFactory();
            if (propertyExpression.isOWLTopDataProperty() && isConsistent())
                return new OWLDataPropertyNodeSet(new OWLDataPropertyNode(factory.getOWLBottomDataProperty()));
            else if (propertyExpression.isOWLBottomDataProperty() && isConsistent())
                return new OWLDataPropertyNodeSet(new OWLDataPropertyNode(factory.getOWLTopDataProperty()));
            else
                return new OWLDataPropertyNodeSet();
        }
    }

    protected boolean isFunctional(OWLDataProperty property) {
        checkPreConditions(property);
        if (!m_isConsistent)
            return true;
        AtomicRole atomicRole = H(property);
        Individual freshIndividual = Individual.createAnonymous("fresh-individual");
        Constant freshConstantA = Constant.createAnonymous("fresh-constant-A");
        Constant freshConstantB = Constant.createAnonymous("fresh-constant-B");
        Set<Atom> assertions = new HashSet<Atom>();
        assertions.add(atomicRole.getRoleAssertion(freshIndividual, freshConstantA));
        assertions.add(atomicRole.getRoleAssertion(freshIndividual, freshConstantB));
        assertions.add(Atom.create(Inequality.INSTANCE, freshConstantA, freshConstantB));
        return !getTableau().isSatisfiable(false, assertions, null, null, null, null, new ReasoningTaskDescription(true, "functionality of {0}", atomicRole));
    }

    protected HierarchyNode<AtomicRole> getHierarchyNode(OWLDataProperty property) {
        checkPreConditions(property);
        classifyDataProperties();
        if (!m_isConsistent)
            return m_dataRoleHierarchy.getBottomNode();
        else {
            AtomicRole atomicRole = H(property);
            HierarchyNode<AtomicRole> node = m_dataRoleHierarchy.getNodeForElement(atomicRole);
            if (node == null)
                node = new HierarchyNode<AtomicRole>(atomicRole, Collections.singleton(atomicRole), Collections.singleton(m_dataRoleHierarchy.getTopNode()), Collections.singleton(m_dataRoleHierarchy.getBottomNode()));
            return node;
        }
    }

    // Individual inferences

    protected void realise() {
        checkPreConditions();
        if (m_dlOntology.getAllIndividuals().size() > 0) {
            classifyClasses();
            initialiseClassInstanceManager();
            m_instanceManager.realize(m_configuration.reasonerProgressMonitor);
        }
    }

    public void realiseObjectProperties() {
        checkPreConditions();
        if (m_dlOntology.getAllIndividuals().size() > 0) {
            classifyObjectProperties();
            initialisePropertiesInstanceManager();
            m_instanceManager.realizeObjectRoles(m_configuration.reasonerProgressMonitor);
        }
    }

    public void precomputeSameAsEquivalenceClasses() {
        checkPreConditions();
        if (m_dlOntology.getAllIndividuals().size() > 0) {
            initialiseClassInstanceManager();
            m_instanceManager.computeSameAsEquivalenceClasses(m_configuration.reasonerProgressMonitor);
        }
    }

    public NodeSet<OWLClass> getTypes(OWLNamedIndividual namedIndividual, boolean direct) {
        checkPreConditions(namedIndividual);
        Set<HierarchyNode<AtomicConcept>> result;
        if (!isDefined(namedIndividual)) {
            classifyClasses();
            result = new HashSet<HierarchyNode<AtomicConcept>>();
            result.add(m_atomicConceptHierarchy.getTopNode());
        } else {
            if (direct)
                classifyClasses();
            initialiseClassInstanceManager();
            if (direct)
                m_instanceManager.setToClassifiedConceptHierarchy(m_atomicConceptHierarchy);
            result = m_instanceManager.getTypes(H(namedIndividual), direct);
        }
        return atomicConceptHierarchyNodesToNodeSet(result);
    }

    public boolean hasType(OWLNamedIndividual namedIndividual, OWLClassExpression type, boolean direct) {
        checkPreConditions(namedIndividual, type);
        if (!m_isConsistent)
            return true;
        if (!isDefined(namedIndividual))
            return getEquivalentClasses(type).contains(m_rootOntology.getOWLOntologyManager().getOWLDataFactory().getOWLThing());
        else {
            if (type instanceof OWLClass) {
                if (direct)
                    classifyClasses();
                initialiseClassInstanceManager();
                if (direct)
                    m_instanceManager.setToClassifiedConceptHierarchy(m_atomicConceptHierarchy);
                return m_instanceManager.hasType(H(namedIndividual), H((OWLClass) type), direct);
            } else {
                OWLDataFactory factory = getDataFactory();
                OWLAxiom negatedAssertionAxiom = factory.getOWLClassAssertionAxiom(type.getObjectComplementOf(), namedIndividual);
                Tableau tableau = getTableau(negatedAssertionAxiom);
                boolean result = tableau.isSatisfiable(true, true, null, null, null, null, null, ReasoningTaskDescription.isInstanceOf(namedIndividual, type));
                tableau.clearAdditionalDLOntology();
                return !result;
            }
        }
    }

    public NodeSet<OWLNamedIndividual> getInstances(OWLClassExpression classExpression, boolean direct) {
        if (m_dlOntology.getAllIndividuals().size() > 0) {
            checkPreConditions(classExpression);
            if (!m_isConsistent) {
                Node<OWLNamedIndividual> node = new OWLNamedIndividualNode(getAllNamedIndividuals());
                return new OWLNamedIndividualNodeSet(Collections.singleton(node));
            }
            if (direct || !(classExpression instanceof OWLClass))
                classifyClasses();
            initialiseClassInstanceManager();
            Set<Individual> result = new HashSet<Individual>();
            if (classExpression instanceof OWLClass)
                result = m_instanceManager.getInstances(H((OWLClass) classExpression), direct);
            else {
                HierarchyNode<AtomicConcept> hierarchyNode = getHierarchyNode(classExpression); //defines internal:query-concept as equivalent to the queried (complex) concepts and inserts internal:query-concept into the class hierarchy
                result = m_instanceManager.getInstances(hierarchyNode, direct); // gets instances of classes that are direct subclasses of internal:query-concept
                OWLDataFactory factory = getDataFactory();
                OWLClass queryClass = factory.getOWLClass(IRI.create("internal:query-concept"));
                OWLAxiom queryClassDefinition = factory.getOWLSubClassOfAxiom(queryClass, classExpression.getObjectComplementOf());
                AtomicConcept queryConcept = AtomicConcept.create("internal:query-concept");
                Set<HierarchyNode<AtomicConcept>> visitedNodes = new HashSet<HierarchyNode<AtomicConcept>>(hierarchyNode.getChildNodes());
                List<HierarchyNode<AtomicConcept>> toVisit = new ArrayList<HierarchyNode<AtomicConcept>>(hierarchyNode.getParentNodes()); //look for (direct) sibling nodes
                while (!toVisit.isEmpty()) {
                    HierarchyNode<AtomicConcept> node = toVisit.remove(toVisit.size() - 1);
                    if (visitedNodes.add(node)) {
                        Set<Individual> realizationForNodeConcept = m_instanceManager.getInstances(node, true);
                        if (realizationForNodeConcept != null) {
                            Tableau tableau = getTableau(queryClassDefinition);
                            for (Individual individual : realizationForNodeConcept)
                                if (isResultRelevantIndividual(individual))
                                    if (!tableau.isSatisfiable(true, true, Collections.singleton(Atom.create(queryConcept, individual)), null, null, null, null, ReasoningTaskDescription.isInstanceOf(individual, classExpression)))
                                        result.add(individual);
                            tableau.clearAdditionalDLOntology();
                        }
                        toVisit.addAll(node.getChildNodes());
                    }
                }
            }
            return sortBySameAsIfNecessary(result);
        } else
            return new OWLNamedIndividualNodeSet(new HashSet<Node<OWLNamedIndividual>>());
    }

    public boolean isSameIndividual(OWLNamedIndividual namedIndividual1, OWLNamedIndividual namedIndividual2) {
        checkPreConditions(namedIndividual1, namedIndividual2);
        if (!m_isConsistent)
            return true;
        if (m_dlOntology.getAllIndividuals().size() == 0)
            return false;
        else {
            initialiseClassInstanceManager();
            m_instanceManager.computeSameAsEquivalenceClasses(m_configuration.reasonerProgressMonitor);
            return m_instanceManager.isSameIndividual(H(namedIndividual1), H(namedIndividual2));
        }
    }

    public Node<OWLNamedIndividual> getSameIndividuals(OWLNamedIndividual namedIndividual) {
        checkPreConditions(namedIndividual);
        if (!m_isConsistent)
            return new OWLNamedIndividualNode(getAllNamedIndividuals());
        if (m_dlOntology.getAllIndividuals().size() == 0 || !m_dlOntology.containsIndividual(H(namedIndividual)))
            return new OWLNamedIndividualNode(namedIndividual);
        else {
            initialiseClassInstanceManager();
            Set<Individual> sameIndividuals = m_instanceManager.getSameAsIndividuals(H(namedIndividual));
            OWLDataFactory factory = getDataFactory();
            Set<OWLNamedIndividual> result = new HashSet<OWLNamedIndividual>();
            for (Individual individual : sameIndividuals)
                result.add(factory.getOWLNamedIndividual(IRI.create(individual.getIRI())));
            return new OWLNamedIndividualNode(result);
        }
    }

    public NodeSet<OWLNamedIndividual> getDifferentIndividuals(OWLNamedIndividual namedIndividual) {
        checkPreConditions(namedIndividual);
        if (!m_isConsistent) {
            Node<OWLNamedIndividual> node = new OWLNamedIndividualNode(getAllNamedIndividuals());
            return new OWLNamedIndividualNodeSet(Collections.singleton(node));
        }
        Individual individual = H(namedIndividual);
        Tableau tableau = getTableau();
        Set<Individual> result = new HashSet<Individual>();
        for (Individual potentiallyDifferentIndividual : m_dlOntology.getAllIndividuals())
            if (isResultRelevantIndividual(potentiallyDifferentIndividual) && !individual.equals(potentiallyDifferentIndividual))
                if (!tableau.isSatisfiable(true, true, Collections.singleton(Atom.create(Equality.INSTANCE, individual, potentiallyDifferentIndividual)), null, null, null, null, new ReasoningTaskDescription(true, "is {0} different from {1}", individual, potentiallyDifferentIndividual)))
                    result.add(potentiallyDifferentIndividual);
        return sortBySameAsIfNecessary(result);
    }

    public NodeSet<OWLNamedIndividual> getObjectPropertyValues(OWLNamedIndividual namedIndividual, OWLObjectPropertyExpression propertyExpression) {
        checkPreConditions(namedIndividual, propertyExpression);
        if (!m_isConsistent) {
            Node<OWLNamedIndividual> node = new OWLNamedIndividualNode(getAllNamedIndividuals());
            return new OWLNamedIndividualNodeSet(Collections.singleton(node));
        }
        AtomicRole role = H(propertyExpression.getNamedProperty());
        if (!m_dlOntology.containsObjectRole(role))
            return new OWLNamedIndividualNodeSet();
        initialisePropertiesInstanceManager();
        Individual individual = H(namedIndividual);
        Set<Individual> result;
        if (propertyExpression.getSimplified().isAnonymous()) {
            // inverse role
            result = m_instanceManager.getObjectPropertySubjects(role, individual);
        } else {
            // named role
            result = m_instanceManager.getObjectPropertyValues(role, individual);
        }
        return sortBySameAsIfNecessary(result);
    }

    public Map<OWLNamedIndividual, Set<OWLNamedIndividual>> getObjectPropertyInstances(OWLObjectProperty property) {
        checkPreConditions(property);
        Map<OWLNamedIndividual, Set<OWLNamedIndividual>> result = new HashMap<OWLNamedIndividual, Set<OWLNamedIndividual>>();
        if (!m_isConsistent) {
            Set<OWLNamedIndividual> all = getAllNamedIndividuals();
            for (OWLNamedIndividual ind : all)
                result.put(ind, all);
            return result;
        }
        initialisePropertiesInstanceManager();
        AtomicRole role = H(property);
        Map<Individual, Set<Individual>> relations = m_instanceManager.getObjectPropertyInstances(role);
        OWLDataFactory factory = getDataFactory();
        for (Individual individual : relations.keySet()) {
            Set<OWLNamedIndividual> successors = new HashSet<OWLNamedIndividual>();
            result.put(factory.getOWLNamedIndividual(IRI.create(individual.getIRI())), successors);
            for (Individual successorIndividual : relations.get(individual))
                successors.add(factory.getOWLNamedIndividual(IRI.create(successorIndividual.getIRI())));
        }
        return result;
    }

    public boolean hasObjectPropertyRelationship(OWLNamedIndividual subject, OWLObjectPropertyExpression propertyExpression, OWLNamedIndividual object) {
        checkPreConditions(subject, propertyExpression, object);
        if (!m_isConsistent)
            return true;
        initialisePropertiesInstanceManager();
        OWLObjectProperty property = propertyExpression.getNamedProperty();
        if (propertyExpression.getSimplified().isAnonymous()) {
            OWLNamedIndividual tmp = subject;
            subject = object;
            object = tmp;
        }
        AtomicRole role = H(property);
        Individual subj = H(subject);
        Individual obj = H(object);
        return m_instanceManager.hasObjectRoleRelationship(role, subj, obj);
    }

    public Set<OWLLiteral> getDataPropertyValues(OWLNamedIndividual namedIndividual, OWLDataProperty property) {
        checkPreConditions(namedIndividual, property);
        Set<OWLLiteral> result = new HashSet<OWLLiteral>();
        if (m_dlOntology.hasDatatypes()) {
            OWLDataFactory factory = getDataFactory();
            Set<OWLDataProperty> relevantDataProperties = getSubDataProperties(property, false).getFlattened();
            relevantDataProperties.add(property);
            Set<OWLNamedIndividual> relevantIndividuals = getSameIndividuals(namedIndividual).getEntities();
            for (OWLDataProperty dataProperty : relevantDataProperties) {
                if (!dataProperty.isBottomEntity()) {
                    AtomicRole atomicRole = H(dataProperty);
                    Map<Individual, Set<Constant>> dataPropertyAssertions = m_dlOntology.getDataPropertyAssertions().get(atomicRole);
                    if (dataPropertyAssertions != null) {
                        for (OWLNamedIndividual ind : relevantIndividuals) {
                            Individual individual = H(ind);
                            if (dataPropertyAssertions.containsKey(individual)) {
                                for (Constant constant : dataPropertyAssertions.get(individual)) {
                                    String lexicalForm = constant.getLexicalForm();
                                    String datatypeURI = constant.getDatatypeURI();
                                    OWLLiteral literal;
                                    if ((Prefixes.s_semanticWebPrefixes.get("rdf:") + "PlainLiteral").equals(datatypeURI)) {
                                        int atPosition = lexicalForm.lastIndexOf('@');
                                        literal = factory.getOWLLiteral(lexicalForm.substring(0, atPosition), lexicalForm.substring(atPosition + 1));
                                    } else
                                        literal = factory.getOWLLiteral(lexicalForm, factory.getOWLDatatype(IRI.create(datatypeURI)));
                                    result.add(literal);
                                }
                            }
                        }
                    }
                }
            }
        }
        return result;
    }

    public boolean hasDataPropertyRelationship(OWLNamedIndividual subject, OWLDataProperty property, OWLLiteral object) {
        checkPreConditions(subject, property);
        if (!m_isConsistent)
            return true;
        OWLDataFactory factory = getDataFactory();
        OWLAxiom notAssertion = factory.getOWLNegativeDataPropertyAssertionAxiom(property, subject, object);
        Tableau tableau = getTableau(notAssertion);
        boolean result = tableau.isSatisfiable(true, true, null, null, null, null, null, new ReasoningTaskDescription(true, "is {0} connected to {1} via {2}", H(subject), object, H(property)));
        tableau.clearAdditionalDLOntology();
        return !result;
    }

    protected Set<HierarchyNode<AtomicConcept>> getDirectSuperConceptNodes(final Individual individual) {
        HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>> predicate = new HierarchySearch.SearchPredicate<HierarchyNode<AtomicConcept>>() {
            public Set<HierarchyNode<AtomicConcept>> getSuccessorElements(HierarchyNode<AtomicConcept> u) {
                return u.getChildNodes();
            }

            public Set<HierarchyNode<AtomicConcept>> getPredecessorElements(HierarchyNode<AtomicConcept> u) {
                return u.getParentNodes();
            }

            public boolean trueOf(HierarchyNode<AtomicConcept> u) {
                AtomicConcept atomicConcept = u.getRepresentative();
                if (AtomicConcept.THING.equals(atomicConcept))
                    return true;
                else
                    return !getTableau().isSatisfiable(true, true, null, Collections.singleton(Atom.create(atomicConcept, individual)), null, null, null, ReasoningTaskDescription.isInstanceOf(atomicConcept, individual));
            }
        };
        return HierarchySearch.search(predicate, Collections.singleton(m_atomicConceptHierarchy.getTopNode()), null);
    }

    protected NodeSet<OWLNamedIndividual> sortBySameAsIfNecessary(Set<Individual> individuals) {
        OWLDataFactory factory = getDataFactory();
        Set<Node<OWLNamedIndividual>> result = new HashSet<Node<OWLNamedIndividual>>();
        if (m_configuration.individualNodeSetPolicy == IndividualNodeSetPolicy.BY_SAME_AS) {
            // group the individuals by same as equivalence classes
            while (!individuals.isEmpty()) {
                initialiseClassInstanceManager();
                Individual individual = individuals.iterator().next();
                Set<Individual> sameIndividuals = m_instanceManager.getSameAsIndividuals(individual);
                Set<OWLNamedIndividual> sameNamedIndividuals = new HashSet<OWLNamedIndividual>();
                for (Individual sameIndividual : sameIndividuals)
                    sameNamedIndividuals.add(factory.getOWLNamedIndividual(IRI.create(sameIndividual.getIRI())));
                individuals.removeAll(sameIndividuals);
                result.add(new OWLNamedIndividualNode(sameNamedIndividuals));
            }
        } else {
            for (Individual individual : individuals)
                result.add(new OWLNamedIndividualNode(factory.getOWLNamedIndividual(IRI.create(individual.getIRI()))));
        }
        return new OWLNamedIndividualNodeSet(result);
    }

    protected Set<OWLNamedIndividual> getAllNamedIndividuals() {
        Set<OWLNamedIndividual> result = new HashSet<OWLNamedIndividual>();
        OWLDataFactory factory = getDataFactory();
        for (Individual individual : m_dlOntology.getAllIndividuals())
            if (isResultRelevantIndividual(individual))
                result.add(factory.getOWLNamedIndividual(IRI.create(individual.getIRI())));
        return result;
    }

    protected static boolean isResultRelevantIndividual(Individual individual) {
        return !individual.isAnonymous() && !Prefixes.isInternalIRI(individual.getIRI());
    }

    // Various creation methods

    public Tableau getTableau() {
        m_tableau.clearAdditionalDLOntology();
        return m_tableau;
    }

    /**
     * A mostly internal method. Can be used to retrieve a tableau for axioms in the given ontology manager plus an additional set of axioms.
     *
     * @param additionalAxioms - a list of additional axioms that should be included in the tableau
     * @return a tableau containing rules for the normalised axioms, this tableau is not permanent in the reasoner, i.e., it does not overwrite the originally created tableau
     * @throws IllegalArgumentException - if the axioms lead to non-admissible clauses, some configuration parameters are incompatible or other such errors
     */
    public Tableau getTableau(OWLAxiom... additionalAxioms) throws IllegalArgumentException {
        if (additionalAxioms == null || additionalAxioms.length == 0)
            return getTableau();
        else {
            DLOntology deltaDLOntology = createDeltaDLOntology(m_configuration, m_dlOntology, additionalAxioms);
            if (m_tableau.supportsAdditionalDLOntology(deltaDLOntology)) {
                m_tableau.setAdditionalDLOntology(deltaDLOntology);
                return m_tableau;
            } else
                return createTableau(m_interruptFlag, m_configuration, m_dlOntology, deltaDLOntology, m_prefixes);
        }
    }

    protected static Tableau createTableau(InterruptFlag interruptFlag, Configuration configuration, DLOntology permanentDLOntology, DLOntology additionalDLOntology, Prefixes prefixes) throws IllegalArgumentException {
        boolean hasInverseRoles = (permanentDLOntology.hasInverseRoles() || (additionalDLOntology != null && additionalDLOntology.hasInverseRoles()));
        boolean hasNominals = (permanentDLOntology.hasNominals() || (additionalDLOntology != null && additionalDLOntology.hasNominals()));

        TableauMonitor wellKnownTableauMonitor = null;
        switch (configuration.tableauMonitorType) {
            case NONE:
                wellKnownTableauMonitor = null;
                break;
            case TIMING:
                wellKnownTableauMonitor = new Timer();
                break;
            case TIMING_WITH_PAUSE:
                wellKnownTableauMonitor = new TimerWithPause();
                break;
            case DEBUGGER_HISTORY_ON:
                wellKnownTableauMonitor = new Debugger(prefixes, true);
                break;
            case DEBUGGER_NO_HISTORY:
                wellKnownTableauMonitor = new Debugger(prefixes, false);
                break;
            default:
                throw new IllegalArgumentException("Unknown monitor type");
        }

        TableauMonitor tableauMonitor = null;
        if (configuration.monitor == null)
            tableauMonitor = wellKnownTableauMonitor;
        else if (wellKnownTableauMonitor == null)
            tableauMonitor = configuration.monitor;
        else
            tableauMonitor = new TableauMonitorFork(wellKnownTableauMonitor, configuration.monitor);

        DirectBlockingChecker directBlockingChecker = null;
        switch (configuration.directBlockingType) {
            case OPTIMAL:
                if (configuration.blockingStrategyType == BlockingStrategyType.SIMPLE_CORE || configuration.blockingStrategyType == BlockingStrategyType.COMPLEX_CORE)
                    directBlockingChecker = new ValidatedSingleDirectBlockingChecker(hasInverseRoles);
                else if (hasInverseRoles)
                    directBlockingChecker = new PairWiseDirectBlockingChecker();
                else
                    directBlockingChecker = new SingleDirectBlockingChecker();
                break;
            case SINGLE:
                if (configuration.blockingStrategyType == BlockingStrategyType.SIMPLE_CORE || configuration.blockingStrategyType == BlockingStrategyType.COMPLEX_CORE)
                    directBlockingChecker = new ValidatedSingleDirectBlockingChecker(hasInverseRoles);
                else
                    directBlockingChecker = new SingleDirectBlockingChecker();
                break;
            case PAIR_WISE:
                if (configuration.blockingStrategyType == BlockingStrategyType.SIMPLE_CORE || configuration.blockingStrategyType == BlockingStrategyType.COMPLEX_CORE)
                    directBlockingChecker = new ValidatedPairwiseDirectBlockingChecker(hasInverseRoles);
                else
                    directBlockingChecker = new PairWiseDirectBlockingChecker();
                break;
            default:
                throw new IllegalArgumentException("Unknown direct blocking type.");
        }

        BlockingSignatureCache blockingSignatureCache = null;
        if (!hasNominals && !(configuration.blockingStrategyType == BlockingStrategyType.SIMPLE_CORE || configuration.blockingStrategyType == BlockingStrategyType.COMPLEX_CORE)) {
            switch (configuration.blockingSignatureCacheType) {
                case CACHED:
                    blockingSignatureCache = new BlockingSignatureCache(directBlockingChecker);
                    break;
                case NOT_CACHED:
                    blockingSignatureCache = null;
                    break;
                default:
                    throw new IllegalArgumentException("Unknown blocking cache type.");
            }
        }

        BlockingStrategy blockingStrategy = null;
        switch (configuration.blockingStrategyType) {
            case ANCESTOR:
                blockingStrategy = new AncestorBlocking(directBlockingChecker, blockingSignatureCache);
                break;
            case ANYWHERE:
                blockingStrategy = new AnywhereBlocking(directBlockingChecker, blockingSignatureCache);
                break;
            case SIMPLE_CORE:
                blockingStrategy = new AnywhereValidatedBlocking(directBlockingChecker, hasInverseRoles, true);
                break;
            case COMPLEX_CORE:
                blockingStrategy = new AnywhereValidatedBlocking(directBlockingChecker, hasInverseRoles, false);
                break;
            case OPTIMAL:
                blockingStrategy = new AnywhereBlocking(directBlockingChecker, blockingSignatureCache);
                break;
            default:
                throw new IllegalArgumentException("Unknown blocking strategy type.");
        }

        ExistentialExpansionStrategy existentialsExpansionStrategy = null;
        switch (configuration.existentialStrategyType) {
            case CREATION_ORDER:
                existentialsExpansionStrategy = new CreationOrderStrategy(blockingStrategy);
                break;
            case EL:
                existentialsExpansionStrategy = new IndividualReuseStrategy(blockingStrategy, true);
                break;
            case INDIVIDUAL_REUSE:
                existentialsExpansionStrategy = new IndividualReuseStrategy(blockingStrategy, false);
                break;
            default:
                throw new IllegalArgumentException("Unknown expansion strategy type.");
        }

        return new Tableau(interruptFlag, tableauMonitor, existentialsExpansionStrategy, configuration.useDisjunctionLearning, permanentDLOntology, additionalDLOntology, configuration.parameters);
    }

    protected Hierarchy<AtomicConcept> classifyAtomicConcepts(Tableau tableau, ClassificationProgressMonitor progressMonitor, AtomicConcept topElement, AtomicConcept bottomElement, Set<AtomicConcept> elements, boolean forceQuasiOrder) {
        if (tableau.isDeterministic() && !forceQuasiOrder)
            return new DeterministicClassification(tableau, progressMonitor, topElement, bottomElement, elements).classify();
        else
            return new QuasiOrderClassification(tableau, progressMonitor, topElement, bottomElement, elements).classify();
    }

    protected Hierarchy<AtomicConcept> classifyAtomicConceptsForRoles(Tableau tableau, ClassificationProgressMonitor progressMonitor, AtomicConcept topElement, AtomicConcept bottomElement, Set<AtomicConcept> elements, boolean hasInverses, Map<Role, AtomicConcept> conceptsForRoles, Map<AtomicConcept, Role> rolesForConcepts, boolean forceQuasiOrder) {
        if (tableau.isDeterministic() && !forceQuasiOrder)
            return new DeterministicClassification(tableau, progressMonitor, topElement, bottomElement, elements).classify();
        else
            return new QuasiOrderClassificationForRoles(tableau, progressMonitor, topElement, bottomElement, elements, hasInverses, conceptsForRoles, rolesForConcepts).classify();
    }

    protected DLOntology createDeltaDLOntology(Configuration configuration, DLOntology originalDLOntology, OWLAxiom... additionalAxioms) throws IllegalArgumentException {
        Set<OWLAxiom> additionalAxiomsSet = new HashSet<OWLAxiom>();
        for (OWLAxiom axiom : additionalAxioms) {
            if (isUnsupportedExtensionAxiom(axiom))
                throw new IllegalArgumentException("Internal error: unsupported extension axiom type.");
            additionalAxiomsSet.add(axiom);
        }
        OWLDataFactory dataFactory = getDataFactory();
        OWLAxioms axioms = new OWLAxioms();
        axioms.m_definedDatatypesIRIs.addAll(originalDLOntology.getDefinedDatatypeIRIs());
        OWLNormalization normalization = new OWLNormalization(dataFactory, axioms, originalDLOntology.getAllAtomicConcepts().size());
        normalization.processAxioms(additionalAxiomsSet);
        BuiltInPropertyManager builtInPropertyManager = new BuiltInPropertyManager(dataFactory);
        builtInPropertyManager.axiomatizeBuiltInPropertiesAsNeeded(axioms, originalDLOntology.getAllAtomicObjectRoles().contains(AtomicRole.TOP_OBJECT_ROLE), originalDLOntology.getAllAtomicObjectRoles().contains(AtomicRole.BOTTOM_OBJECT_ROLE), originalDLOntology.getAllAtomicObjectRoles().contains(AtomicRole.TOP_DATA_ROLE), originalDLOntology.getAllAtomicObjectRoles().contains(AtomicRole.BOTTOM_DATA_ROLE));

        int currentReplacementIndex = m_objectPropertyInclusionManager.rewriteNegativeObjectPropertyAssertions(dataFactory, axioms, originalDLOntology.getAllAtomicConcepts().size());
        m_objectPropertyInclusionManager.rewriteAxioms(dataFactory, axioms, currentReplacementIndex);
        OWLAxiomsExpressivity axiomsExpressivity = new OWLAxiomsExpressivity(axioms);
        axiomsExpressivity.m_hasAtMostRestrictions |= originalDLOntology.hasAtMostRestrictions();
        axiomsExpressivity.m_hasInverseRoles |= originalDLOntology.hasInverseRoles();
        axiomsExpressivity.m_hasNominals |= originalDLOntology.hasNominals();
        axiomsExpressivity.m_hasDatatypes |= originalDLOntology.hasDatatypes();
        OWLClausification clausifier = new OWLClausification(configuration);
        Set<DescriptionGraph> descriptionGraphs = Collections.emptySet();
        return clausifier.clausify(dataFactory, "uri:urn:internal-kb", axioms, axiomsExpressivity, descriptionGraphs);
    }

    protected static boolean isUnsupportedExtensionAxiom(OWLAxiom axiom) {
        return
                axiom instanceof OWLSubObjectPropertyOfAxiom ||
                        axiom instanceof OWLTransitiveObjectPropertyAxiom ||
                        axiom instanceof OWLSubPropertyChainOfAxiom ||
                        axiom instanceof OWLFunctionalObjectPropertyAxiom ||
                        axiom instanceof OWLInverseFunctionalObjectPropertyAxiom ||
                        axiom instanceof SWRLRule;
    }

    // Hierarchy printing

    /**
     * Writes out the hierarchies quickly
     *
     * @param out              - the printwriter that is used to output the hierarchies
     * @param classes          - if true, the class hierarchy is printed
     * @param objectProperties - if true, the object property hierarchy is printed
     * @param dataProperties   - if true, the data property hierarchy is printed
     */
  public void dumpHierarchies(PrintWriter out, boolean classes, boolean objectProperties, boolean dataProperties, boolean propertyValues) {
        HierarchyDumperFSS printer = new HierarchyDumperFSS(out);
        if (classes) {
            classifyClasses();
            printer.printAtomicConceptHierarchy(m_atomicConceptHierarchy);
        }
        if (objectProperties) {
            classifyObjectProperties();
            printer.printObjectPropertyHierarchy(m_objectRoleHierarchy);
        }
        if (dataProperties) {
            classifyDataProperties();
            printer.printDataPropertyHierarchy(m_dataRoleHierarchy);
        }
        
        // CHANGED BY W. ZIMMER and JIBA
        //  print also inferred object properties to console/file
        if (propertyValues && (m_instanceManager != null)) {
            printer.printInferredProperties(m_instanceManager.getCurrentRoleHierarchy());
        }
    }

    /**
     * Prints the hierarchies into a functional style syntax ontology all nicely sorted alphabetically.
     *
     * @param out              - the printwriter that is used to output the hierarchies
     * @param classes          - if true, the class hierarchy is printed
     * @param objectProperties - if true, the object property hierarchy is printed
     * @param dataProperties   - if true, the data property hierarchy is printed
     */
    public void printHierarchies(PrintWriter out, boolean classes, boolean objectProperties, boolean dataProperties) {
        HierarchyPrinterFSS printer = new HierarchyPrinterFSS(out, m_dlOntology.getOntologyIRI() + "#");
        if (classes) {
            classifyClasses();
            printer.loadAtomicConceptPrefixIRIs(m_atomicConceptHierarchy.getAllElements());
        }
        if (objectProperties) {
            classifyObjectProperties();
            printer.loadAtomicRolePrefixIRIs(m_dlOntology.getAllAtomicObjectRoles());
        }
        if (dataProperties) {
            classifyDataProperties();
            printer.loadAtomicRolePrefixIRIs(m_dlOntology.getAllAtomicDataRoles());
        }
        printer.startPrinting();
        boolean atLF = true;
        if (classes && !m_atomicConceptHierarchy.isEmpty()) {
            printer.printAtomicConceptHierarchy(m_atomicConceptHierarchy);
            atLF = false;
        }
        if (objectProperties && !m_objectRoleHierarchy.isEmpty()) {
            if (!atLF)
                out.println();
            printer.printRoleHierarchy(m_objectRoleHierarchy, true);
            atLF = false;
        }
        if (dataProperties && !m_dataRoleHierarchy.isEmpty()) {
            if (!atLF)
                out.println();
            printer.printRoleHierarchy(m_dataRoleHierarchy, false);
            atLF = false;
        }
        printer.endPrinting();
    }

    // Various utility methods

    protected void checkPreConditions(OWLObject... objects) {
        flushChangesIfRequired();
        if (objects != null && objects.length > 0)
            throwFreshEntityExceptionIfNecessary(objects);
        throwInconsistentOntologyExceptionIfNecessary();
    }

    protected void flushChangesIfRequired() {
        if (!m_configuration.bufferChanges && !m_pendingChanges.isEmpty())
            flush();
    }

    protected void throwInconsistentOntologyExceptionIfNecessary() {
        if (!isConsistent() && m_configuration.throwInconsistentOntologyException)
            throw new InconsistentOntologyException();
    }

    protected void throwFreshEntityExceptionIfNecessary(OWLObject... objects) {
        if (m_configuration.freshEntityPolicy == FreshEntityPolicy.DISALLOW) {
            Set<OWLEntity> undeclaredEntities = new HashSet<OWLEntity>();
            for (OWLObject object : objects) {
                if (!(object instanceof OWLEntity) || !((OWLEntity) object).isBuiltIn()) {
                    for (OWLDataProperty dp : object.getDataPropertiesInSignature())
                        if (!isDefined(dp) && !Prefixes.isInternalIRI(dp.getIRI().toString()))
                            undeclaredEntities.add(dp);
                    for (OWLObjectProperty op : object.getObjectPropertiesInSignature())
                        if (!isDefined(op) && !Prefixes.isInternalIRI(op.getIRI().toString()))
                            undeclaredEntities.add(op);
                    for (OWLNamedIndividual individual : object.getIndividualsInSignature())
                        if (!isDefined(individual) && !Prefixes.isInternalIRI(individual.getIRI().toString()))
                            undeclaredEntities.add(individual);
                    for (OWLClass owlClass : object.getClassesInSignature())
                        if (!isDefined(owlClass) && !Prefixes.isInternalIRI(owlClass.getIRI().toString()))
                            undeclaredEntities.add(owlClass);
                }
            }
            if (!undeclaredEntities.isEmpty())
                throw new FreshEntitiesException(undeclaredEntities);
        }
    }

    protected boolean containsFreshEntities(OWLObject... objects) {
        for (OWLObject object : objects) {
            if (!(object instanceof OWLEntity) || !((OWLEntity) object).isBuiltIn()) {
                for (OWLDataProperty dp : object.getDataPropertiesInSignature())
                    if (!isDefined(dp) && !Prefixes.isInternalIRI(dp.getIRI().toString()))
                        return true;
                for (OWLObjectProperty op : object.getObjectPropertiesInSignature())
                    if (!isDefined(op) && !Prefixes.isInternalIRI(op.getIRI().toString()))
                        return true;
                for (OWLNamedIndividual individual : object.getIndividualsInSignature())
                    if (!isDefined(individual) && !Prefixes.isInternalIRI(individual.getIRI().toString()))
                        return true;
                for (OWLClass owlClass : object.getClassesInSignature())
                    if (!isDefined(owlClass) && !Prefixes.isInternalIRI(owlClass.getIRI().toString()))
                        return true;
            }
        }
        return false;
    }

    // Methods for conversion from OWL API to HermiT's API

    protected static AtomicConcept H(OWLClass owlClass) {
        return AtomicConcept.create(owlClass.getIRI().toString());
    }

    protected static AtomicRole H(OWLObjectProperty objectProperty) {
        return AtomicRole.create(objectProperty.getIRI().toString());
    }

    protected static Role H(OWLObjectPropertyExpression objectPropertyExpression) {
        objectPropertyExpression = objectPropertyExpression.getSimplified();
        if (objectPropertyExpression instanceof OWLObjectProperty)
            return H((OWLObjectProperty) objectPropertyExpression);
        else
            return H(objectPropertyExpression.getNamedProperty()).getInverse();
    }

    protected static AtomicRole H(OWLDataProperty dataProperty) {
        return AtomicRole.create(dataProperty.getIRI().toString());
    }

    protected static Role H(OWLDataPropertyExpression dataPropertyExpression) {
        return H((OWLDataProperty) dataPropertyExpression);
    }

    protected static Individual H(OWLNamedIndividual namedIndividual) {
        return Individual.create(namedIndividual.getIRI().toString());
    }

    protected static Individual H(OWLAnonymousIndividual anonymousIndividual) {
        return Individual.createAnonymous(anonymousIndividual.getID().toString());
    }

    protected static Individual H(OWLIndividual individual) {
        if (individual.isAnonymous())
            return H((OWLAnonymousIndividual) individual);
        else
            return H((OWLNamedIndividual) individual);
    }

    // Extended methods for conversion from HermiT's API to OWL API

    protected Node<OWLClass> atomicConceptHierarchyNodeToNode(HierarchyNode<AtomicConcept> hierarchyNode) {
        Set<OWLClass> result = new HashSet<OWLClass>();
        OWLDataFactory factory = getDataFactory();
        for (AtomicConcept concept : hierarchyNode.getEquivalentElements())
            if (!Prefixes.isInternalIRI(concept.getIRI()))
                result.add(factory.getOWLClass(IRI.create(concept.getIRI())));
        return new OWLClassNode(result);
    }

    protected NodeSet<OWLClass> atomicConceptHierarchyNodesToNodeSet(Collection<HierarchyNode<AtomicConcept>> hierarchyNodes) {
        Set<Node<OWLClass>> result = new HashSet<Node<OWLClass>>();
        for (HierarchyNode<AtomicConcept> hierarchyNode : hierarchyNodes) {
            Node<OWLClass> node = atomicConceptHierarchyNodeToNode(hierarchyNode);
            if (node.getSize() != 0)
                result.add(node);
        }
        return new OWLClassNodeSet(result);
    }

    protected Node<OWLObjectPropertyExpression> objectPropertyHierarchyNodeToNode(HierarchyNode<Role> hierarchyNode) {
        Set<OWLObjectPropertyExpression> result = new HashSet<OWLObjectPropertyExpression>();
        OWLDataFactory factory = getDataFactory();
        for (Role role : hierarchyNode.getEquivalentElements()) {
            if (role instanceof AtomicRole)
                result.add(factory.getOWLObjectProperty(IRI.create(((AtomicRole) role).getIRI())));
            else {
                OWLObjectPropertyExpression ope = factory.getOWLObjectProperty(IRI.create(((InverseRole) role).getInverseOf().getIRI()));
                result.add(factory.getOWLObjectInverseOf(ope));
            }
        }
        return new OWLObjectPropertyNode(result);
    }

    protected NodeSet<OWLObjectPropertyExpression> objectPropertyHierarchyNodesToNodeSet(Collection<HierarchyNode<Role>> hierarchyNodes) {
        Set<Node<OWLObjectPropertyExpression>> result = new HashSet<Node<OWLObjectPropertyExpression>>();
        for (HierarchyNode<Role> hierarchyNode : hierarchyNodes) {
            result.add(objectPropertyHierarchyNodeToNode(hierarchyNode));
        }
        return new OWLObjectPropertyNodeSet(result);
    }

    protected Node<OWLDataProperty> dataPropertyHierarchyNodeToNode(HierarchyNode<AtomicRole> hierarchyNode) {
        Set<OWLDataProperty> result = new HashSet<OWLDataProperty>();
        OWLDataFactory factory = getDataFactory();
        for (AtomicRole atomicRole : hierarchyNode.getEquivalentElements())
            result.add(factory.getOWLDataProperty(IRI.create(atomicRole.getIRI())));
        return new OWLDataPropertyNode(result);
    }

    protected NodeSet<OWLDataProperty> dataPropertyHierarchyNodesToNodeSet(Collection<HierarchyNode<AtomicRole>> hierarchyNodes) {
        Set<Node<OWLDataProperty>> result = new HashSet<Node<OWLDataProperty>>();
        for (HierarchyNode<AtomicRole> hierarchyNode : hierarchyNodes)
            result.add(dataPropertyHierarchyNodeToNode(hierarchyNode));
        return new OWLDataPropertyNodeSet(result);
    }

    // The factory for OWL API reasoners

    public static class ReasonerFactory implements OWLReasonerFactory {
        public String getReasonerName() {
            return getClass().getPackage().getImplementationTitle();
        }

        public OWLReasoner createReasoner(OWLOntology ontology) {
            return createReasoner(ontology, null);
        }

        public OWLReasoner createReasoner(OWLOntology ontology, OWLReasonerConfiguration config) {
            return createHermiTOWLReasoner(getProtegeConfiguration(config), ontology);
        }

        public OWLReasoner createNonBufferingReasoner(OWLOntology ontology) {
            return createNonBufferingReasoner(ontology, null);
        }

        public OWLReasoner createNonBufferingReasoner(OWLOntology ontology, OWLReasonerConfiguration owlAPIConfiguration) {
            Configuration configuration = getProtegeConfiguration(owlAPIConfiguration);
            configuration.bufferChanges = false;
            return createHermiTOWLReasoner(configuration, ontology);
        }

        protected Configuration getProtegeConfiguration(OWLReasonerConfiguration owlAPIConfiguration) {
            Configuration configuration;
            if (owlAPIConfiguration != null) {
                if (owlAPIConfiguration instanceof Configuration)
                    configuration = (Configuration) owlAPIConfiguration;
                else {
                    configuration = new Configuration();
                    configuration.freshEntityPolicy = owlAPIConfiguration.getFreshEntityPolicy();
                    configuration.individualNodeSetPolicy = owlAPIConfiguration.getIndividualNodeSetPolicy();
                    configuration.reasonerProgressMonitor = owlAPIConfiguration.getProgressMonitor();
                    configuration.individualTaskTimeout = owlAPIConfiguration.getTimeOut();
                }
            } else {
                configuration = new Configuration();
                configuration.ignoreUnsupportedDatatypes = true;
            }
            return configuration;
        }

        protected OWLReasoner createHermiTOWLReasoner(Configuration configuration, OWLOntology ontology) {
            return new Reasoner(configuration, ontology);
        }
    }
}
