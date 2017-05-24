/*
javac -cp ./antibio_arcenciel/owlready_cas_dut_1/owlapi-3.4.3.jar ./owlready2/test/Save.java
java -cp ./antibio_arcenciel/owlready_cas_dut_1/owlapi-3.4.3.jar:./owlready2/test Save   > /dev/null

*/

import java.io.*;
import java.util.*;

import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.util.*;
import org.semanticweb.owlapi.io.*;
import org.semanticweb.owlapi.apibinding.*;
import org.semanticweb.owlapi.vocab.*;
import org.coode.owlapi.turtle.*;
  
class Save {
  public static void main(String[] args) throws Exception {
    
    long t;
    
    OWLOntologyManager m = OWLManager.createOWLOntologyManager();
    OWLDataFactory df = OWLManager.getOWLDataFactory();
    
    m.addIRIMapper(new AutoIRIMapper(new File("/home/jiba/telechargements/base_med"), false));
    
    IRI iri = IRI.create("file://" + args[0]);
    OWLOntology o = m.loadOntologyFromOntologyDocument(iri);
    
    File saveas = new File(args[2]);
    OWLOntologyFormat format = m.getOntologyFormat(o);
    OWLXMLOntologyFormat   owlformat = new OWLXMLOntologyFormat();
    RDFXMLOntologyFormat   rdfformat = new RDFXMLOntologyFormat();
    TurtleOntologyFormat   ntformat  = new TurtleOntologyFormat();
    if (format.isPrefixOWLOntologyFormat()) { 
      owlformat.copyPrefixesFrom(format.asPrefixOWLOntologyFormat()); 
      rdfformat.copyPrefixesFrom(format.asPrefixOWLOntologyFormat()); 
      ntformat .copyPrefixesFrom(format.asPrefixOWLOntologyFormat()); 
    }
    if     (args[1].equals("nt")) {
      m.saveOntology(o, ntformat, IRI.create(saveas.toURI()));
    }
    else if(args[1].equals("rdf")) {
      m.saveOntology(o, rdfformat, IRI.create(saveas.toURI()));
    }
    else{
      m.saveOntology(o, owlformat, IRI.create(saveas.toURI()));
    }
        
    
    System.err.println("saved");
    
  }
}
