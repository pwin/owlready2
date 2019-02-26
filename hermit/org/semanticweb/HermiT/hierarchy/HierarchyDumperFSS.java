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
package org.semanticweb.HermiT.hierarchy;

import java.io.PrintWriter;
import java.util.Comparator;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;

import org.semanticweb.HermiT.model.AtomicConcept;
import org.semanticweb.HermiT.model.AtomicRole;
import org.semanticweb.HermiT.model.InverseRole;
import org.semanticweb.HermiT.model.Role;

public class HierarchyDumperFSS {
    protected final PrintWriter m_out;

    public HierarchyDumperFSS(PrintWriter out) {
        m_out=out;
    }
    public void printAtomicConceptHierarchy(Hierarchy<AtomicConcept> atomicConceptHierarchy) {
        for (HierarchyNode<AtomicConcept> node : atomicConceptHierarchy.getAllNodesSet()) {
            SortedSet<AtomicConcept> equivs=new TreeSet<AtomicConcept>(AtomicConceptComparator.INSTANCE);
            equivs.addAll(node.getEquivalentElements());
            AtomicConcept representative=equivs.first();
            if (equivs.size()>1) {
                boolean first=true;
                for (AtomicConcept equiv : equivs) {
                    if (first) {
                        m_out.print("EquivalentClasses( <");
                        m_out.print(representative.getIRI());
                        m_out.print(">");
                        first=false;
                    }
                    else {
                        m_out.print(" <");
                        m_out.print(equiv.getIRI());
                        m_out.print(">");
                    }
                }
                m_out.print(" )");
                m_out.println();
            }
            if (!representative.equals(AtomicConcept.THING)) {
                for (HierarchyNode<AtomicConcept> sub : node.getChildNodes()) {
                    AtomicConcept subRepresentative=sub.getRepresentative();
                    if (!subRepresentative.equals(AtomicConcept.NOTHING)) {
                        m_out.print("SubClassOf( <");
                        m_out.print(subRepresentative.getIRI());
                        m_out.print("> <");
                        m_out.print(representative.getIRI());
                        m_out.print("> )");
                        m_out.println();
                    }
                }
            }
        }
        m_out.println();
    }

    public void printInferredProperties(Hierarchy<RoleElementManager.RoleElement> currentRoleHierarchy) {
        Set<RoleElementManager.RoleElement> allElements = currentRoleHierarchy.getAllElements();
        for (RoleElementManager.RoleElement roleElement : allElements) {
            m_out.println(roleElement.toString());
        }
    }

    public void printObjectPropertyHierarchy(Hierarchy<Role> objectRoleHierarchy) {
        for (HierarchyNode<Role> node : objectRoleHierarchy.getAllNodesSet()) {
            SortedSet<Role> equivs=new TreeSet<Role>(ObjectRoleComparator.INSTANCE);
            equivs.addAll(node.getEquivalentElements());
            Role representative=equivs.first();
            if (equivs.size()>1) {
                boolean first=true;
                for (Role equiv : equivs) {
                    if (first) {
                        m_out.print("EquivalentObjectProperties( ");
                        print(representative);
                        first=false;
                    }
                    else {
                        m_out.print(" ");
                        print(equiv);
                    }
                }
                m_out.print(" )");
                m_out.println();
            }
            if (!representative.equals(AtomicRole.TOP_OBJECT_ROLE)) {
                for (HierarchyNode<Role> sub : node.getChildNodes()) {
                    Role subRepresentative=sub.getRepresentative();
                    if (!subRepresentative.equals(AtomicRole.BOTTOM_OBJECT_ROLE)) {
                        m_out.print("SubObjectPropertyOf( ");
                        print(subRepresentative);
                        m_out.print(" ");
                        print(representative);
                        m_out.print(" )");
                        m_out.println();
                    }
                }
            }
        }
        m_out.println();
    }
    public void printDataPropertyHierarchy(Hierarchy<AtomicRole> dataRoleHierarchy) {
        for (HierarchyNode<AtomicRole> node : dataRoleHierarchy.getAllNodesSet()) {
            //m_out.println(node.toString());
            
            SortedSet<AtomicRole> equivs=new TreeSet<AtomicRole>(DataRoleComparator.INSTANCE);
            equivs.addAll(node.getEquivalentElements());
            AtomicRole representative=equivs.first();
            if (equivs.size()>1) {
                boolean first=true;
                for (AtomicRole equiv : equivs) {
                    if (first) {
                        m_out.print("EquivalentDataProperties( <");
                        m_out.print(representative.getIRI());
                        m_out.print(">");
                        first=false;
                    }
                    else {
                        m_out.print(" >");
                        m_out.print(equiv.getIRI());
                        m_out.print(">");
                    }
                }
                m_out.print(" )");
                m_out.println();
            }
            if (!representative.equals(AtomicRole.TOP_DATA_ROLE)) {
                for (HierarchyNode<AtomicRole> sub : node.getChildNodes()) {
                    AtomicRole subRepresentative=sub.getRepresentative();
                    if (!subRepresentative.equals(AtomicRole.BOTTOM_DATA_ROLE)) {
                        m_out.print("SubDataPropertyOf( <");
                        m_out.print(subRepresentative.getIRI());
                        m_out.print("> <");
                        m_out.print(representative.getIRI());
                        m_out.print("> )");
                        m_out.println();
                    }
                }
            }
        }
        m_out.println();
    }
    protected void print(Role role) {
        if (role instanceof AtomicRole)
            print((AtomicRole)role);
        else {
            m_out.print("ObjectInverseOf( ");
            print(((InverseRole)role).getInverseOf());
            m_out.print(" )");
        }
    }
    protected void print(AtomicRole atomicRole) {
        m_out.print("<");
        m_out.print(atomicRole.getIRI());
        m_out.print(">");
    }

    protected static class AtomicConceptComparator implements Comparator<AtomicConcept> {
        public static final AtomicConceptComparator INSTANCE=new AtomicConceptComparator();

        public int compare(AtomicConcept atomicConcept1,AtomicConcept atomicConcept2) {
            int comparison=getAtomicConceptClass(atomicConcept1)-getAtomicConceptClass(atomicConcept2);
            if (comparison!=0)
                return comparison;
            return atomicConcept1.getIRI().compareTo(atomicConcept2.getIRI());
        }
        protected int getAtomicConceptClass(AtomicConcept atomicConcept) {
            if (AtomicConcept.NOTHING.equals(atomicConcept))
                return 0;
            else if (AtomicConcept.THING.equals(atomicConcept))
                return 1;
            else
                return 2;
        }
    }

    protected static class ObjectRoleComparator implements Comparator<Role> {
        public static final ObjectRoleComparator INSTANCE=new ObjectRoleComparator();

        public int compare(Role role1,Role role2) {
            int comparison=getRoleClass(role1)-getRoleClass(role2);
            if (comparison!=0)
                return comparison;
            comparison=getRoleDirection(role1)-getRoleDirection(role2);
            if (comparison!=0)
                return comparison;
            return getInnerAtomicRole(role1).getIRI().compareTo(getInnerAtomicRole(role2).getIRI());
        }
        protected int getRoleClass(Role role) {
            if (AtomicRole.BOTTOM_OBJECT_ROLE.equals(role))
                return 0;
            else if (AtomicRole.TOP_OBJECT_ROLE.equals(role))
                return 1;
            else
                return 2;
        }
        protected AtomicRole getInnerAtomicRole(Role role) {
            if (role instanceof AtomicRole)
                return (AtomicRole)role;
            else
                return ((InverseRole)role).getInverseOf();
        }
        protected int getRoleDirection(Role role) {
            return role instanceof AtomicRole ? 0 : 1;
        }
    }

    protected static class DataRoleComparator implements Comparator<AtomicRole> {
        public static final DataRoleComparator INSTANCE=new DataRoleComparator();

        public int compare(AtomicRole atomicRole1,AtomicRole atomicRole2) {
            int comparison=getAtomicRoleClass(atomicRole1)-getAtomicRoleClass(atomicRole2);
            if (comparison!=0)
                return comparison;
            return atomicRole1.getIRI().compareTo(atomicRole2.getIRI());
        }
        protected int getAtomicRoleClass(AtomicRole atomicRole) {
            if (AtomicRole.BOTTOM_DATA_ROLE.equals(atomicRole))
                return 0;
            else if (AtomicRole.TOP_DATA_ROLE.equals(atomicRole))
                return 1;
            else
                return 2;
        }
    }
}
