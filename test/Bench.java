/*
javac -cp ./antibio_arcenciel/owlready_cas_dut_1/owlapi-3.4.3.jar ./owlready2/test/Bench.java
java -cp ./antibio_arcenciel/owlready_cas_dut_1/owlapi-3.4.3.jar:./owlready2/test Bench > /dev/null

#Load time : 14.618 s.
#List class time : 3.074 s.
#Memory used : 1 123 Mb

*/

import java.io.*;
import java.util.*;

import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.util.*;
import org.semanticweb.owlapi.io.*;
import org.semanticweb.owlapi.apibinding.*;
import org.semanticweb.owlapi.vocab.*;

class Bench {
  public static void main(String[] args) throws Exception {
    
    long t;
    
    OWLOntologyManager m = OWLManager.createOWLOntologyManager();
    OWLDataFactory df = OWLManager.getOWLDataFactory();
    
    t = (new Date().getTime());

    IRI iri = IRI.create("file:///home/jiba/telechargements/base_med/go.owl");
    //IRI iri = IRI.create("file:///home/jiba/telechargements/base_med/obi.owl");
    //IRI iri = IRI.create("file:///home/jiba/telechargements/base_med/vto.owl");
    //IRI iri = IRI.create("file:///home/jiba/telechargements/base_med/uberon.owl");
    //IRI iri = IRI.create("file:///home/jiba/src/owlready2/test/test.owl");
    OWLOntology o = m.loadOntologyFromOntologyDocument(iri);
    
    t = (new Date().getTime()) - t;
    System.err.print("Loading ");
    System.err.println(t / 1000.0f);
    
    /*
    File saveas = new File("/home/jiba/telechargements/base_med/go2.owl");
    OWLOntologyFormat format = m.getOntologyFormat(o);
    OWLXMLOntologyFormat owlxmlFormat = new OWLXMLOntologyFormat();
    if (format.isPrefixOWLOntologyFormat()) { 
      owlxmlFormat.copyPrefixesFrom(format.asPrefixOWLOntologyFormat()); 
    }
    m.saveOntology(o, owlxmlFormat, IRI.create(saveas.toURI()));    
    
    System.err.println("saved");
    */
    
    
    
    t = (new Date().getTime());

    int nb = 0;
    for (OWLClass cls : o.getClassesInSignature()) {
      nb += 1;
      System.out.println(cls_2_str(df, o, cls));
      Set<OWLClassExpression> superClasses = cls.getSuperClasses(o);
      for (OWLClassExpression desc : superClasses) {
        System.out.print("    is a ");
        if(desc instanceof OWLClass) {
          System.out.println(cls_2_str(df, o, (OWLClass) desc));
        }
        else if(desc instanceof OWLObjectSomeValuesFrom) {
          OWLObjectSomeValuesFrom some = (OWLObjectSomeValuesFrom) desc;
          Object prop = some.getProperty();
          Object fill = some.getFiller();
          if (prop instanceof OWLEntity) 
            System.out.print  (cls_2_str(df, o, (OWLEntity) prop));
          else
            System.out.print  (prop);
          System.out.print  (" some ");
          if (fill instanceof OWLEntity) 
            System.out.println(cls_2_str(df, o, (OWLEntity) fill));
          else
            System.out.println(fill);
        }
        else {
          System.out.println(desc);
        }
      }
    }
    
    System.err.print("NB ");
    System.err.println(nb);
    
    t = (new Date().getTime()) - t;
    System.err.print("Listing ");
    System.err.println(t / 1000.0f);
    
    Thread.sleep(40000);
  }
  
  public static String cls_2_str(OWLDataFactory df, OWLOntology o, OWLEntity cls) {
    String iri = cls.getIRI().toString();
    String name = iri.substring(iri.lastIndexOf("/") + 1, iri.length());
    
    OWLAnnotationProperty label = df.getOWLAnnotationProperty(OWLRDFVocabulary.RDFS_LABEL.getIRI());
    
    for (OWLAnnotation annotation : cls.getAnnotations(o, label)) {
      if (annotation.getValue() instanceof OWLLiteral) {
        OWLLiteral val = (OWLLiteral) annotation.getValue();
        return name + ":'" + val.getLiteral() + "'";
      }
    }
    return name;
  }
}
