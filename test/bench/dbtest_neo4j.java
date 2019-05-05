import java.io.*;
import java.util.*;

import org.neo4j.driver.v1.*;

/*

Random write: 247.56763 objects/second
Random read: 267.50842 objects/second

 */

public class dbtest_neo4j {
  private static final int NB = 10000;
  
  public static void main( String... args ) throws Exception {
    long t, dt;
    Driver db = GraphDatabase.driver( "bolt://localhost", AuthTokens.basic( "", "" ) );
    Session session = db.session();
    Transaction tx = session.beginTransaction();
    tx.run("CREATE INDEX ON :Node(label)");
    tx.success();
    tx.close();
    
    t = (new Date().getTime());
    tx = session.beginTransaction();
    Value node;
    Value previous = null;
    for (int i = 0; i < NB; i++) {
      String label = "node number " + i;
      node = tx.run("CREATE (x:Node {label:'" + label + "'}) RETURN id(x)").single().get(0);
      if (previous != null) {
        tx.run("MATCH (x:Node) WHERE id(x)=" + previous + " MATCH (y:Node) WHERE id(y)=" + node + " CREATE (x)-[:NEXT]->(y)");
      }
      previous = node;
    }
    tx.success();
    tx.close();
    dt = (new Date().getTime()) - t;
    System.err.print("Random write: "); System.err.print(1.0f/(dt/1000.0f)*NB); System.err.println(" objects/second");

    t = (new Date().getTime());
    tx = session.beginTransaction();
    node = tx.run("MATCH (x:Node) WHERE x.label='node number 0' RETURN id(x)").single().get(0);
    while (true) {
      Value label = tx.run("MATCH (x:Node) WHERE id(x)=" + node + " RETURN x.label").single().get(0);
      try {
        node = tx.run("MATCH (x:Node)-[:NEXT]->(y:Node) WHERE id(x)=" + node + " RETURN id(y)").single().get(0);
      }
      catch (org.neo4j.driver.v1.exceptions.NoSuchRecordException e) { break; }
    }
    tx.success();
    tx.close();
    dt = (new Date().getTime()) - t;
    System.err.print("Random read: "); System.err.print(1.0f/(dt/1000.0f)*NB); System.err.println(" objects/second");
    
  }
}

/*

javac -cp ~/src/neo4j-java-driver-1.0.0.jar ./dbtest_neo4j.java 

java -cp ~/src/neo4j-java-driver-1.0.0.jar:. dbtest_neo4j


 Supprime toute la base :

MATCH (n)  OPTIONAL MATCH (n)-[r]-()  DELETE n,r

    

*/
