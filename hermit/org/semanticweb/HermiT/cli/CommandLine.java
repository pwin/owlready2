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
package org.semanticweb.HermiT.cli;

import gnu.getopt.Getopt;
import gnu.getopt.LongOpt;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.net.URI;
import java.text.BreakIterator;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.Map;
import java.util.Set;

import org.semanticweb.HermiT.Configuration;
import org.semanticweb.HermiT.EntailmentChecker;
import org.semanticweb.HermiT.Prefixes;
import org.semanticweb.HermiT.Reasoner;
import org.semanticweb.HermiT.model.Individual;
import org.semanticweb.HermiT.monitor.Timer;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.IRI;
import org.semanticweb.owlapi.model.OWLClass;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyCreationException;
import org.semanticweb.owlapi.model.OWLOntologyIRIMapper;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.semanticweb.owlapi.model.OWLNamedIndividual;
import org.semanticweb.owlapi.reasoner.InferenceType;
import org.semanticweb.owlapi.reasoner.Node;
import org.semanticweb.owlapi.reasoner.NodeSet;
import org.semanticweb.owlapi.util.AutoIRIMapper;

public class CommandLine {

    @SuppressWarnings("serial")
    protected static class UsageException extends IllegalArgumentException {
        public UsageException(String inMessage) {
            super(inMessage);
        }
    }


    protected static class StatusOutput {
        protected int level;
        public StatusOutput(int inLevel) {
            level=inLevel;
        }
        static public final int ALWAYS=0;
        static public final int STATUS=1;
        static public final int DETAIL=2;
        static public final int DEBUG=3;
        public void log(int inLevel,String message) {
            if (inLevel<=level)
                System.err.println(message);
        }
    }

    protected interface Action {
        void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes);
    }

    static protected class DumpPrefixesAction implements Action {
        public void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes) {
            output.println("Prefixes:");
            for (Map.Entry<String,String> e : hermit.getPrefixes().getPrefixIRIsByPrefixName().entrySet()) {
                output.println("\t"+e.getKey()+"\t"+e.getValue());
            }
            output.flush();
        }
    }

    static protected class DumpClausesAction implements Action {
        final String file;

        public DumpClausesAction(String fileName) {
            file=fileName;
        }
        public void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes) {
            if (file!=null) {
                if (file.equals("-")) {
                    output=new PrintWriter(System.out);
                }
                else {
                    java.io.FileOutputStream f;
                    try {
                        f=new java.io.FileOutputStream(file);
                    }
                    catch (java.io.FileNotFoundException e) {
                        throw new IllegalArgumentException("unable to open "+file+" for writing");
                    }
                    catch (SecurityException e) {
                        throw new IllegalArgumentException("unable to write to "+file);
                    }
                    output=new PrintWriter(f);
                }
            }
            if (ignoreOntologyPrefixes)
                output.println(hermit.getDLOntology().toString(new Prefixes()));
            else
                output.println(hermit.getDLOntology().toString(hermit.getPrefixes()));
            output.flush();
        }
    }

    static protected class ClassifyAction implements Action {
        final boolean classifyClasses;
        final boolean classifyOPs;
        final boolean classifyDPs;
        final boolean classifyIs;
        final boolean classifyPVs;
        final boolean classifyDs;
        final boolean prettyPrint;
        final String outputLocation;

        public ClassifyAction(boolean classifyClasses, boolean classifyOPs, boolean classifyDPs, boolean classifyIs, boolean classifyPVs, boolean classifyDs, boolean prettyPrint, String outputLocation) {
            this.classifyClasses=classifyClasses;
            this.classifyOPs=classifyOPs;
            this.classifyDPs=classifyDPs;
            this.classifyIs=classifyIs;
            this.classifyPVs=classifyPVs;
            this.classifyDs=classifyDs;
            this.prettyPrint=prettyPrint;
            this.outputLocation=outputLocation;
        }
        public void run(Reasoner hermit, StatusOutput status, PrintWriter output,boolean ignoreOntologyPrefixes) {
            Set<InferenceType> inferences=new HashSet<InferenceType>();
            if (classifyClasses)
                inferences.add(InferenceType.CLASS_HIERARCHY);
            if (classifyOPs)
                inferences.add(InferenceType.OBJECT_PROPERTY_HIERARCHY);
            if (classifyDPs)
                inferences.add(InferenceType.DATA_PROPERTY_HIERARCHY);
            if (classifyIs)
                inferences.add(InferenceType.CLASS_ASSERTIONS);
            if (classifyPVs) {
                inferences.add(InferenceType.OBJECT_PROPERTY_ASSERTIONS);
                inferences.add(InferenceType.DATA_PROPERTY_ASSERTIONS);
            }
            if (classifyDs) {
                inferences.add(InferenceType.SAME_INDIVIDUAL);
                inferences.add(InferenceType.DIFFERENT_INDIVIDUALS);
                inferences.add(InferenceType.DISJOINT_CLASSES);
            }
            status.log(2,"Classifying...");
            hermit.precomputeInferences(inferences.toArray(new InferenceType[0]));
            //hermit.precomputeInferences(InferenceType.CLASS_HIERARCHY, InferenceType.OBJECT_PROPERTY_HIERARCHY, InferenceType.DATA_PROPERTY_HIERARCHY, InferenceType.CLASS_ASSERTIONS,InferenceType.OBJECT_PROPERTY_ASSERTIONS,InferenceType.SAME_INDIVIDUAL,InferenceType.DISJOINT_CLASSES,InferenceType.DATA_PROPERTY_ASSERTIONS,InferenceType.DIFFERENT_INDIVIDUALS);
            
            if (output!=null) {
                if (outputLocation!=null)
                    status.log(2,"Writing results to "+outputLocation);
                else
                    status.log(2,"Writing results...");
                if (prettyPrint)
                    hermit.printHierarchies(output, classifyClasses, classifyOPs, classifyDPs);
                else
                  hermit.dumpHierarchies(output, classifyClasses, classifyOPs, classifyDPs, classifyPVs);
                if (classifyIs) {
                    for(OWLNamedIndividual namedIndividual : hermit.getRootOntology().getIndividualsInSignature()) {
                        for (Node<OWLClass> node : hermit.getTypes(namedIndividual, true)) {
                            for (OWLClass clazz : node.getEntities()) {
                                output.print("Type( <");
                                output.print(namedIndividual.toStringID());
                                output.print("> <");
                                output.print(clazz.toStringID());
                                output.print("> )\n");
                            }
                        }
                    }
                }
                output.flush();
            }
        }
    }

    static protected class SatisfiabilityAction implements Action {
        final String conceptName;
        public SatisfiabilityAction(String c) {
            conceptName=c;
        }
        public void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes) {
            status.log(2,"Checking satisfiability of '"+conceptName+"'");
            Prefixes prefixes=hermit.getPrefixes();
            String conceptUri=prefixes.canBeExpanded(conceptName) ? prefixes.expandAbbreviatedIRI(conceptName) : conceptName;
            if (conceptUri.startsWith("<") && conceptUri.endsWith(">"))
                conceptUri=conceptUri.substring(1,conceptUri.length()-1);
            OWLClass owlClass=OWLManager.createOWLOntologyManager().getOWLDataFactory().getOWLClass(IRI.create(conceptUri));
            if (!hermit.isDefined(owlClass)) {
                status.log(0,"Warning: class '"+conceptUri+"' was not declared in the ontology.");
            }
            boolean result=hermit.isSatisfiable(owlClass);
            output.println(conceptName+(result ? " is satisfiable." : " is not satisfiable."));
            output.flush();
        }
    }

    static protected class SupersAction implements Action {
        final String conceptName;
        final boolean all;

        public SupersAction(String name,boolean getAll) {
            conceptName=name;
            all=getAll;
        }
        public void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes) {
            status.log(2,"Finding supers of '"+conceptName+"'");
            Prefixes prefixes=hermit.getPrefixes();
            String conceptUri=prefixes.canBeExpanded(conceptName) ? prefixes.expandAbbreviatedIRI(conceptName) :conceptName;
            if (conceptUri.startsWith("<") && conceptUri.endsWith(">"))
                conceptUri=conceptUri.substring(1,conceptUri.length()-1);
            OWLClass owlClass=OWLManager.createOWLOntologyManager().getOWLDataFactory().getOWLClass(IRI.create(conceptUri));
            if (!hermit.isDefined(owlClass)) {
                status.log(0,"Warning: class '"+conceptUri+"' was not declared in the ontology.");
            }
            NodeSet<OWLClass> classes;
            if (all) {
                classes=hermit.getSuperClasses(owlClass,false);
                output.println("All super-classes of '"+conceptName+"':");
            }
            else {
                classes=hermit.getSuperClasses(owlClass,false);
                output.println("Direct super-classes of '"+conceptName+"':");
            }
            for (Node<OWLClass> set : classes)
                for (OWLClass classInSet : set)
                    if (ignoreOntologyPrefixes) {
                        String iri=classInSet.getIRI().toString();
                        if (prefixes.canBeExpanded(iri))
                            output.println("\t"+prefixes.expandAbbreviatedIRI(iri));
                        else
                            output.println("\t"+iri);
                    }
                    else
                        output.println("\t"+prefixes.abbreviateIRI(classInSet.getIRI().toString()));
            output.flush();
        }
    }

    static protected class SubsAction implements Action {
        final String conceptName;
        final boolean all;

        public SubsAction(String name,boolean getAll) {
            conceptName=name;
            all=getAll;
        }
        public void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes) {
            status.log(2,"Finding subs of '"+conceptName+"'");
            Prefixes prefixes=hermit.getPrefixes();
            String conceptUri=prefixes.canBeExpanded(conceptName) ? prefixes.expandAbbreviatedIRI(conceptName) : conceptName;
            if (conceptUri.startsWith("<") && conceptUri.endsWith(">"))
                conceptUri=conceptUri.substring(1,conceptUri.length()-1);
            OWLClass owlClass=OWLManager.createOWLOntologyManager().getOWLDataFactory().getOWLClass(IRI.create(conceptUri));
            if (!hermit.isDefined(owlClass)) {
                status.log(0,"Warning: class '"+conceptUri+"' was not declared in the ontology.");
            }
            NodeSet<OWLClass> classes;
            if (all) {
                classes=hermit.getSubClasses(owlClass,false);
                output.println("All sub-classes of '"+conceptName+"':");
            }
            else {
                classes=hermit.getSubClasses(owlClass,true);
                output.println("Direct sub-classes of '"+conceptName+"':");
            }
            for (Node<OWLClass> set : classes)
                for (OWLClass classInSet : set)
                    if (ignoreOntologyPrefixes) {
                        String iri=classInSet.getIRI().toString();
                        if (prefixes.canBeExpanded(iri))
                            output.println("\t"+prefixes.expandAbbreviatedIRI(iri));
                        else
                            output.println("\t"+iri);
                    }
                    else
                        output.println("\t"+prefixes.abbreviateIRI(classInSet.getIRI().toString()));
            output.flush();
        }
    }

    static protected class EquivalentsAction implements Action {
        final String conceptName;

        public EquivalentsAction(String name) {
            conceptName=name;
        }
        public void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes) {
            status.log(2,"Finding equivalents of '"+conceptName+"'");
            Prefixes prefixes=hermit.getPrefixes();
            String conceptUri=prefixes.canBeExpanded(conceptName) ? prefixes.expandAbbreviatedIRI(conceptName) : conceptName;
            if (conceptUri.startsWith("<") && conceptUri.endsWith(">"))
                conceptUri=conceptUri.substring(1,conceptUri.length()-1);
            OWLClass owlClass=OWLManager.createOWLOntologyManager().getOWLDataFactory().getOWLClass(IRI.create(conceptUri));
            if (!hermit.isDefined(owlClass)) {
                status.log(0,"Warning: class '"+conceptName+"' was not declared in the ontology.");
            }
            Node<OWLClass> classes=hermit.getEquivalentClasses(owlClass);
            if (ignoreOntologyPrefixes)
                output.println("Classes equivalent to '"+conceptName+"':");
            else
                output.println("Classes equivalent to '"+prefixes.abbreviateIRI(conceptName)+"':");
            for (OWLClass classInSet : classes)
                if (ignoreOntologyPrefixes) {
                    String iri=classInSet.getIRI().toString();
                    if (prefixes.canBeExpanded(iri))
                        output.println("\t"+prefixes.expandAbbreviatedIRI(iri));
                    else
                        output.println("\t"+iri);
                }
                else
                    output.println("\t"+prefixes.abbreviateIRI(classInSet.getIRI().toString()));
            output.flush();
        }
    }

    static protected class EntailsAction implements Action {

        final IRI conclusionIRI;

        public EntailsAction(Configuration config,IRI conclusionIRI) {
            this.conclusionIRI=conclusionIRI;
        }
        public void run(Reasoner hermit,StatusOutput status,PrintWriter output,boolean ignoreOntologyPrefixes) {
            status.log(2,"Checking whether the loaded ontology entails the conclusion ontology");
            OWLOntologyManager m=OWLManager.createOWLOntologyManager();
            try {
                OWLOntology conclusions = m.loadOntology(conclusionIRI);
                status.log(2,"Conclusion ontology loaded.");
                EntailmentChecker checker=new EntailmentChecker(hermit, m.getOWLDataFactory());
                boolean isEntailed=checker.entails(conclusions.getLogicalAxioms());
                status.log(2,"Conclusion ontology is "+(isEntailed?"":"not ")+"entailed.");
                output.println(isEntailed);
            }
            catch (OWLOntologyCreationException e) {
                e.printStackTrace();
            }
            output.flush();
        }
    }

    protected static final int
        kTime=1000,
        kDumpClauses=1001,
        kDumpRoleBox=1002,
        kDirectBlock=1003,
        kBlockStrategy=1004,
        kBlockCache=1005,
        kExpansion=1006,
        kBase=1007,
        kParser=1008,
        kDefaultPrefix=1009,
        kDumpPrefixes=1010,
        kTaxonomy=1011,
        kIgnoreUnsupportedDatatypes=1012,
        kPremise=1013,
        kConclusion=1014;

    protected static final String versionString;
    static {
        String version=CommandLine.class.getPackage().getImplementationVersion();
        if (version==null)
            version="<no version set>";
        versionString=version;
    }
    protected static final String usageString="Usage: hermit [OPTION]... IRI...";
    protected static final String[] helpHeader={
        "Perform reasoning on each OWL ontology IRI.",
        "Example: java -jar Hermit.jar -dsowl:Thing http://www.co-ode.org/ontologies/pizza/2005/05/16/pizza.owl",
        "    (prints direct subclasses of owl:Thing within the pizza ontology)",
        "Example: java -jar Hermit.jar --premise=http://km.aifb.uni-karlsruhe.de/projects/owltests/index.php/Special:GetOntology/New-Feature-DisjointObjectProperties-002?m=p --conclusion=http://km.aifb.uni-karlsruhe.de/projects/owltests/index.php/Special:GetOntology/New-Feature-DisjointObjectProperties-002?m=c --checkEntailment",
        "    (checks whether the conclusion ontology is entailed by the premise ontology)",
        "",
        "Both relative and absolute ontology IRIs can be used. Relative IRIs",
        "are resolved with respect to the current directory (i.e. local file",
        "names are valid IRIs); this behavior can be changed with the '--base'",
        "option.",
        "",
        "Classes and properties are identified using functional-syntax-style",
        "identifiers: names not containing a colon are resolved against the",
        "ontology's default prefix; otherwise the portion of the name",
        "preceding the colon is treated as a prefix prefix. Use of",
        "prefixes can be controlled using the -p, -N, and --prefix",
        "options. Alternatively, classes and properties can be identified with",
        "full IRIs by enclosing the IRI in <angle brackets>.",
        "",
        "By default, ontologies are simply retrieved and parsed. For more",
        "interesting reasoning, set one of the -c/-k/-s/-S/-e/-U options."
    };
    protected static final String[] footer={
        "HermiT is a product of Oxford University.",
        "Visit <http://hermit-reasoner.org/> for details."
    };
    protected static final String
        kMisc="Miscellaneous",
        kActions="Actions",
        kParsing="Parsing and loading",
        kPrefixes="Prefix name and IRI",
        kAlgorithm="Algorithm settings (expert users only!)",
        kInternals="Internals and debugging (unstable)";

    protected static final Option[] options=new Option[] {
        // meta:
        new Option('h',"help",kMisc,"display this help and exit"),
        new Option('V',"version",kMisc,"display version information and exit"),
        new Option('v',"verbose",kMisc,false,"AMOUNT","increase verbosity by AMOUNT levels (default 1)"),
        new Option('q',"quiet",kMisc,false,"AMOUNT","decrease verbosity by AMOUNT levels (default 1)"),
        new Option('o',"output",kMisc,true,"FILE","write output to FILE"),
        new Option(kPremise,"premise",kMisc,true,"PREMISE","set the premise ontology to PREMISE"),
        new Option(kConclusion,"conclusion",kMisc,true,"CONCLUSION","set the conclusion ontology to CONCLUSION"),

        // actions:
        new Option('l',"load",kActions,"parse and preprocess ontologies (default action)"),
        new Option('c',"classify",kActions,"classify the classes of the ontology, optionally writing taxonomy to a file if -o (--output) is used"),
        new Option('O',"classifyOPs",kActions,"classify the object properties of the ontology, optionally writing taxonomy to a file if -o (--output) is used"),
        new Option('D',"classifyDPs",kActions,"classify the data properties of the ontology, optionally writing taxonomy to a file if -o (--output) is used"),
        new Option('I',"classifyIs",kActions,"classify the instances of the ontology, optionally writing taxonomy to a file if -o (--output) is used"),
        new Option('Y',"classifyPVs",kActions,"classify the asserted property values"),
        new Option('Z',"classifyDs",kActions,"classify the disjoint classes, same as and different individuals"),
        new Option('P',"prettyPrint",kActions,"when writing the classified hierarchy to a file, create a proper ontology and nicely indent the axioms according to their leven in the hierarchy"),
        new Option('k',"consistency",kActions,false,"CLASS","check satisfiability of CLASS (default owl:Thing)"),
        new Option('d',"direct",kActions,"restrict next subs/supers call to only direct sub/superclasses"),
        new Option('s',"subs",kActions,true,"CLASS","output classes subsumed by CLASS (or only direct subs if following --direct)"),
        new Option('S',"supers",kActions,true,"CLASS","output classes subsuming CLASS (or only direct supers if following --direct)"),
        new Option('e',"equivalents",kActions,true,"CLASS","output classes equivalent to CLASS"),
        new Option('U',"unsatisfiable",kActions,"output unsatisfiable classes (equivalent to --equivalents=owl:Nothing)"),
        new Option(kDumpPrefixes,"print-prefixes",kActions,"output prefix names available for use in identifiers"),
        new Option('E',"checkEntailment",kActions,"check whether the premise (option premise) ontology entails the conclusion ontology (option conclusion)"),

        new Option('N',"no-prefixes",kPrefixes,"do not abbreviate or expand identifiers using prefixes defined in input ontology"),
        new Option('p',"prefix",kPrefixes,true,"PN=IRI","use PN as an abbreviation for IRI in identifiers"),
        new Option(kDefaultPrefix,"prefix",kPrefixes,true,"IRI","use IRI as the default identifier prefix"),

        // algorithm tweaks:
        new Option(kDirectBlock,"block-match",kAlgorithm,true,"TYPE","identify blocked nodes with TYPE blocking; supported values are 'single', 'pairwise', and 'optimal' (default 'optimal')"),
        new Option(kBlockStrategy,"block-strategy",kAlgorithm,true,"TYPE","use TYPE as blocking strategy; supported values are 'ancestor', 'anywhere', 'core', and 'optimal' (default 'optimal')"),
        new Option(kBlockCache,"blockersCache",kAlgorithm,"cache blocking nodes for use in later tests; not possible with nominals or core blocking"),
        new Option(kIgnoreUnsupportedDatatypes,"ignoreUnsupportedDatatypes",kAlgorithm,"ignore unsupported datatypes"),
        new Option(kExpansion,"expansion-strategy",kAlgorithm,true,"TYPE","use TYPE as existential expansion strategy; supported values are 'el', 'creation', 'reuse', and 'optimal' (default 'optimal')"),

        // internals:
        new Option(kDumpClauses,"dump-clauses",kInternals,false,"FILE","output DL-clauses to FILE (default stdout)")
    };

    public static void main(String[] argv) {
        try {
            int verbosity=1;
            boolean ignoreOntologyPrefixes=false;
            PrintWriter output=new PrintWriter(System.out);
            String defaultPrefix=null;
            Map<String,String> prefixMappings=new HashMap<String,String>();
            String resultsFileLocation=null;
            boolean classifyClasses=false;
            boolean classifyOPs=false;
            boolean classifyDPs=false;
            boolean classifyIs=false;
            boolean classifyPVs=false;
            boolean classifyDs=false;
            boolean prettyPrint=false;
            Collection<Action> actions=new LinkedList<Action>();
            URI base;
            IRI conclusionIRI=null;
            Configuration config=new Configuration();
            boolean doAll=true;
            try {
                base=new URI("file",System.getProperty("user.dir")+"/",null);
            }
            catch (java.net.URISyntaxException e) {
                throw new RuntimeException("unable to create default IRI base");
            }
            Collection<IRI> ontologies=new LinkedList<IRI>();
            boolean didSomething=false;
            {
                Getopt g=new Getopt("java-jar Hermit.jar",argv,Option.formatOptionsString(options),Option.createLongOpts(options));
                g.setOpterr(false);
                int opt;
                while ((opt=g.getopt())!=-1) {
                    switch (opt) {
                    // meta:
                    case 'h': {
                        System.out.println(usageString);
                        for (String s : helpHeader)
                            System.out.println(s);
                        System.out.println(Option.formatOptionHelp(options));
                        for (String s : footer)
                            System.out.println(s);
                        System.exit(0);
                        didSomething=true;
                    }
                        break;
                    case 'V': {
                        System.out.println(versionString);
                        for (String s : footer)
                            System.out.println(s);
                        System.exit(0);
                        didSomething=true;
                    }
                        break;
                    case 'v': {
                        String arg=g.getOptarg();
                        if (arg==null) {
                            verbosity+=1;
                        }
                        else
                            try {
                                verbosity+=Integer.parseInt(arg,10);
                            }
                            catch (NumberFormatException e) {
                                throw new UsageException("argument to --verbose must be a number");
                            }
                    }
                        break;
                    case 'q': {
                        String arg=g.getOptarg();
                        if (arg==null) {
                            verbosity-=1;
                        }
                        else
                            try {
                                verbosity-=Integer.parseInt(arg,10);
                            }
                            catch (NumberFormatException e) {
                                throw new UsageException("argument to --quiet must be a number");
                            }
                    }
                        break;
                    case 'o': {
                        String arg=g.getOptarg();
                        if (arg==null)
                            throw new UsageException("--output requires an argument");
                        if (arg.equals("-"))
                            output=new PrintWriter(System.out);
                        else {
                            try {
                                File file=new File(arg);
                                if (!file.exists())
                                    file.createNewFile();
                                file=file.getAbsoluteFile();
                                output=new PrintWriter(new BufferedOutputStream(new FileOutputStream(file)),true);
                                resultsFileLocation=file.getAbsolutePath();
                            }
                            catch (FileNotFoundException e) {
                                throw new IllegalArgumentException("unable to open "+arg+" for writing");
                            }
                            catch (SecurityException e) {
                                throw new IllegalArgumentException("unable to write to "+arg);
                            }
                            catch (IOException e) {
                                throw new IllegalArgumentException("unable to write to "+arg+": "+e.getMessage());
                            }
                        }
                    }
                        break;
                    case kPremise: {
                        String arg=g.getOptarg();
                        if (arg==null)
                            throw new UsageException("--premise requires a IRI as argument");
                        else {
                            ontologies.add(IRI.create(arg));
                        }
                    }
                        break;
                    case kConclusion: {
                        String arg=g.getOptarg();
                        if (arg==null)
                            throw new UsageException("--conclusion requires a IRI as argument");
                        else {
                            conclusionIRI=IRI.create(arg);
                        }
                    }
                        break;
                    // actions:
                    case 'l': {
                        // load is a no-op; loading happens no matter what the user asks
                    }
                        break;
                    case 'c': {
                        classifyClasses=true;
                    }
                        break;
                    case 'O': {
                        classifyOPs=true;
                    }
                        break;
                    case 'D': {
                        classifyDPs=true;
                    }
                        break;
                    case 'I': {
                        classifyIs=true;
                    }
                        break;
                    case 'Y': {
                        classifyPVs=true;
                    }
                        break;
                    case 'Z': {
                        classifyDs=true;
                    }
                        break;
                    case 'P': {
                        prettyPrint=true;
                    }
                        break;
                    case 'k': {
                        String arg=g.getOptarg();
                        if (arg==null) {
                            arg="http://www.w3.org/2002/07/owl#Thing";
                        }
                        actions.add(new SatisfiabilityAction(arg));
                    }
                        break;
                    case 'd': {
                        doAll=false;
                    }
                        break;
                    case 's': {
                        String arg=g.getOptarg();
                        actions.add(new SubsAction(arg,doAll));
                        doAll=true;
                    }
                        break;
                    case 'S': {
                        String arg=g.getOptarg();
                        actions.add(new SupersAction(arg,doAll));
                        doAll=true;
                    }
                        break;
                    case 'e': {
                        String arg=g.getOptarg();
                        actions.add(new EquivalentsAction(arg));
                    }
                        break;
                    case 'U': {
                        actions.add(new EquivalentsAction("http://www.w3.org/2002/07/owl#Nothing"));
                    }
                        break;
                    case 'E': {
                        if (conclusionIRI!=null)
                            actions.add(new EntailsAction(config, conclusionIRI));
                    }
                        break;
                    case kDumpPrefixes: {
                        actions.add(new DumpPrefixesAction());
                    }
                        break;
                    case 'N': {
                        ignoreOntologyPrefixes=true;
                    }
                        break;
                    case 'p': {
                        String arg=g.getOptarg();
                        int eqIndex=arg.indexOf('=');
                        if (eqIndex==-1) {
                            throw new IllegalArgumentException("the prefix declaration '"+arg+"' is not of the form PN=IRI.");
                        }
                        prefixMappings.put(arg.substring(0,eqIndex),arg.substring(eqIndex+1));
                    }
                        break;
                    case kDefaultPrefix: {
                        String arg=g.getOptarg();
                        defaultPrefix=arg;
                    }
                        break;
                    case kBase: {
                        String arg=g.getOptarg();
                        try {
                            base=new URI(arg);
                        }
                        catch (java.net.URISyntaxException e) {
                            throw new IllegalArgumentException("'"+arg+"' is not a valid base URI.");
                        }
                    }
                        break;

                    case kDirectBlock: {
                        String arg=g.getOptarg();
                        if (arg.toLowerCase().equals("pairwise")) {
                            config.directBlockingType=Configuration.DirectBlockingType.PAIR_WISE;
                        }
                        else if (arg.toLowerCase().equals("single")) {
                            config.directBlockingType=Configuration.DirectBlockingType.SINGLE;
                        }
                        else if (arg.toLowerCase().equals("optimal")) {
                            config.directBlockingType=Configuration.DirectBlockingType.OPTIMAL;
                        }
                        else
                            throw new UsageException("unknown direct blocking type '"+arg+"'; supported values are 'pairwise', 'single', and 'optimal'");
                    }
                        break;
                    case kBlockStrategy: {
                        String arg=g.getOptarg();
                        if (arg.toLowerCase().equals("anywhere")) {
                            config.blockingStrategyType=Configuration.BlockingStrategyType.ANYWHERE;
                        }
                        else if (arg.toLowerCase().equals("ancestor")) {
                            config.blockingStrategyType=Configuration.BlockingStrategyType.ANCESTOR;
                        }
                        else if (arg.toLowerCase().equals("core")) {
                            config.blockingStrategyType=Configuration.BlockingStrategyType.SIMPLE_CORE;
                        }
                        else if (arg.toLowerCase().equals("optimal")) {
                            config.blockingStrategyType=Configuration.BlockingStrategyType.OPTIMAL;
                        }
                        else
                            throw new UsageException("unknown blocking strategy type '"+arg+"'; supported values are 'ancestor' and 'anywhere'");
                    }
                        break;
                    case kBlockCache: {
                        config.blockingSignatureCacheType=Configuration.BlockingSignatureCacheType.CACHED;
                    }
                        break;
                    case kExpansion: {
                        String arg=g.getOptarg();
                        if (arg.toLowerCase().equals("creation")) {
                            config.existentialStrategyType=Configuration.ExistentialStrategyType.CREATION_ORDER;
                        }
                        else if (arg.toLowerCase().equals("el")) {
                            config.existentialStrategyType=Configuration.ExistentialStrategyType.EL;
                        }
                        else if (arg.toLowerCase().equals("reuse")) {
                            config.existentialStrategyType=Configuration.ExistentialStrategyType.INDIVIDUAL_REUSE;
                        }
                        else
                            throw new UsageException("unknown existential strategy type '"+arg+"'; supported values are 'creation', 'el', and 'reuse'");
                    }
                        break;
                    case kIgnoreUnsupportedDatatypes: {
                        config.ignoreUnsupportedDatatypes=true;
                    }
                        break;
                    case kDumpClauses: {
                        actions.add(new DumpClausesAction(g.getOptarg()));
                    }
                        break;
                    default: {
                        if (g.getOptopt()!=0) {
                            throw new UsageException("invalid option -- "+(char)g.getOptopt());
                        }
                        throw new UsageException("invalid option");
                    }
                    } // end option switch
                } // end loop over options
                for (int i=g.getOptind();i<argv.length;++i) {
                    try {
                        ontologies.add(IRI.create(base.resolve(argv[i])));
                    }
                    catch (IllegalArgumentException e) {
                        throw new UsageException(argv[i]+" is not a valid ontology name");
                    }
                }
            } // done processing arguments
            StatusOutput status=new StatusOutput(verbosity);
            if (verbosity>3)
                config.monitor=new Timer(new PrintWriter(System.err));
            if (classifyClasses || classifyOPs || classifyDPs || classifyIs)
                actions.add(new ClassifyAction(classifyClasses, classifyOPs, classifyDPs, classifyIs, classifyPVs, classifyDs, prettyPrint, resultsFileLocation));
            for (IRI ont : ontologies) {
                didSomething=true;
                status.log(2,"Processing "+ont.toString());
                status.log(2,String.valueOf(actions.size())+" actions");
                try {
                    long startTime=System.currentTimeMillis();
                    OWLOntologyManager ontologyManager=OWLManager.createOWLOntologyManager();
                    if (ont.isAbsolute()) {
                        URI uri=URI.create(ont.getStart());
                        String scheme = uri.getScheme();
                        if (scheme!=null && scheme.equalsIgnoreCase("file")) {
                            File file=new File(URI.create(ont.getStart()));
                            if (file.isDirectory()) {
                                OWLOntologyIRIMapper mapper=new AutoIRIMapper(file, false);
                                ontologyManager.addIRIMapper(mapper);
                            }
                        }
                    }
                    OWLOntology ontology=ontologyManager.loadOntology(ont);
//                    if (!ignoreOntologyPrefixes) {
//                        SimpleRenderer renderer=new SimpleRenderer();
//                        renderer.setPrefixesFromOntologyFormat(ontology, ontologyManager, true);
//                        ToStringRenderer.getInstance().setRenderer(renderer);
//                    }
                    long parseTime=System.currentTimeMillis()-startTime;
                    status.log(2,"Ontology parsed in "+String.valueOf(parseTime)+" msec.");
                    startTime=System.currentTimeMillis();

                    /*
                    uk.ac.manchester.cs.owlapi.dlsyntax.DLSyntaxObjectRenderer renderer = new uk.ac.manchester.cs.owlapi.dlsyntax.DLSyntaxObjectRenderer(); 
                    for (org.semanticweb.owlapi.model.SWRLRule rule : ontology.getAxioms(org.semanticweb.owlapi.model.AxiomType.SWRL_RULE)) { 
                      System.out.println(renderer.render(rule)); 
                    }
                    */
                    
                    /*
                    org.semanticweb.HermiT.Configuration.PrepareReasonerInferences prepareReasonerInferences=new org.semanticweb.HermiT.Configuration.PrepareReasonerInferences();
                    prepareReasonerInferences.classClassificationRequired=true;
                    prepareReasonerInferences.objectPropertyClassificationRequired=true;
                    prepareReasonerInferences.dataPropertyClassificationRequired=true;
                    prepareReasonerInferences.realisationRequired=true;
                    prepareReasonerInferences.objectPropertyRealisationRequired=true;
                    prepareReasonerInferences.dataPropertyRealisationRequired=true;
                    prepareReasonerInferences.objectPropertyDomainsRequired=true;
                    prepareReasonerInferences.objectPropertyRangesRequired=true;
                    prepareReasonerInferences.sameAs=true;
                    config.prepareReasonerInferences=prepareReasonerInferences;
                    */


                    Reasoner hermit=new Reasoner(config,ontology);
                    Prefixes prefixes=hermit.getPrefixes();
                    if (defaultPrefix!=null) {
                        try {
                            prefixes.declareDefaultPrefix(defaultPrefix);
                        }
                        catch (IllegalArgumentException e) {
                            status.log(2,"Default prefix "+defaultPrefix+" could not be registered because there is already a registered default prefix. ");
                        }
                    }
                    for (String prefixName : prefixMappings.keySet()) {
                        try {
                            prefixes.declarePrefix(prefixName, prefixMappings.get(prefixName));
                        }
                        catch (IllegalArgumentException e) {
                            status.log(2,"Prefixname "+prefixName+" could not be set to "+prefixMappings.get(prefixName)+" because there is already a registered prefix name for the IRI. ");
                        }
                    }
                    long loadTime=System.currentTimeMillis()-startTime;
                    status.log(2,"Reasoner created in "+String.valueOf(loadTime)+" msec.");
                    for (Action action : actions) {
                        status.log(2,"Doing action...");
                        startTime=System.currentTimeMillis();
                        action.run(hermit,status,output,ignoreOntologyPrefixes);
                        long actionTime=System.currentTimeMillis()-startTime;
                        status.log(2,"...action completed in "+String.valueOf(actionTime)+" msec.");
                    }
                }
                catch (org.semanticweb.owlapi.model.OWLException e) {
                    System.err.println("It all went pear-shaped: "+e.getMessage());
                    e.printStackTrace(System.err);
                }
            }
            if (!didSomething)
                throw new UsageException("No ontologies given.");
        }
        catch (UsageException e) {
            System.err.println(e.getMessage());
            System.err.println(usageString);
            System.err.println("Try 'hermit --help' for more information.");
        }
    }
}

enum Arg { NONE,OPTIONAL,REQUIRED }

class Option {
    protected int optChar;
    protected String longStr;
    protected String group;
    protected Arg arg;
    protected String metavar;
    protected String help;

    public Option(int inChar,String inLong,String inGroup,String inHelp) {
        optChar=inChar;
        longStr=inLong;
        group=inGroup;
        arg=Arg.NONE;
        help=inHelp;
    }
    public Option(int inChar,String inLong,String inGroup,boolean argRequired,String inMetavar,String inHelp) {
        optChar=inChar;
        longStr=inLong;
        group=inGroup;
        arg=(argRequired ? Arg.REQUIRED : Arg.OPTIONAL);
        metavar=inMetavar;
        help=inHelp;
    }
    public static LongOpt[] createLongOpts(Option[] opts) {
        LongOpt[] out=new LongOpt[opts.length];
        for (int i=0;i<opts.length;++i) {
            out[i]=new LongOpt(opts[i].longStr,(opts[i].arg==Arg.NONE ? LongOpt.NO_ARGUMENT : opts[i].arg==Arg.OPTIONAL ? LongOpt.OPTIONAL_ARGUMENT : LongOpt.REQUIRED_ARGUMENT),null,opts[i].optChar);
        }
        return out;
    }

    public String getLongOptExampleStr() {
        if (longStr==null||longStr.equals(""))
            return "";
        return new String("--"+longStr+(arg==Arg.NONE ? "" : arg==Arg.OPTIONAL ? "[="+metavar+"]" : "="+metavar));
    }

    public static String formatOptionHelp(Option[] opts) {
        StringBuffer out=new StringBuffer();
        int fieldWidth=0;
        for (Option o : opts) {
            int curWidth=o.getLongOptExampleStr().length();
            if (curWidth>fieldWidth)
                fieldWidth=curWidth;
        }
        String curGroup=null;
        for (Option o : opts) {
            if (o.group!=curGroup) {
                curGroup=o.group;
                out.append(System.getProperty("line.separator"));
                if (o.group!=null) {
                    out.append(curGroup+":");
                    out.append(System.getProperty("line.separator"));
                }
            }
            if (o.optChar<256) {
                out.append("  -");
                out.appendCodePoint(o.optChar);
                if (o.longStr!=null&&o.longStr!="") {
                    out.append(", ");
                }
                else {
                    out.append("  ");
                }
            }
            else {
                out.append("      ");
            }
            int fieldLeft=fieldWidth+1;
            if (o.longStr!=null&&o.longStr!="") {
                String s=o.getLongOptExampleStr();
                out.append(s);
                fieldLeft-=s.length();
            }
            for (;fieldLeft>0;--fieldLeft)
                out.append(' ');
            out.append(breakLines(o.help,80,6+fieldWidth+1));
            out.append(System.getProperty("line.separator"));
        }
        return out.toString();
    }

    public static String formatOptionsString(Option[] opts) {
        StringBuffer out=new StringBuffer();
        for (Option o : opts) {
            if (o.optChar<256) {
                out.appendCodePoint(o.optChar);
                switch (o.arg) {
                case REQUIRED:
                    out.append(":");
                    break;
                case OPTIONAL:
                    out.append("::");
                    break;
                case NONE:
                    break;
                }
            }
        }
        return out.toString();
    }

    protected static String breakLines(String str,int lineWidth,int indent) {
        StringBuffer out=new StringBuffer();
        BreakIterator i=BreakIterator.getLineInstance();
        i.setText(str);
        int curPos=0;
        int curLinePos=indent;
        int next=i.first();
        while (next!=BreakIterator.DONE) {
            String curSpan=str.substring(curPos,next);
            if (curLinePos+curSpan.length()>lineWidth) {
                out.append(System.getProperty("line.separator"));
                for (int j=0;j<indent;++j)
                    out.append(" ");
                curLinePos=indent;
            }
            out.append(curSpan);
            curLinePos+=curSpan.length();
            curPos=next;
            next=i.next();
        }
        return out.toString();
    }
}
