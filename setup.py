#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2017 Jean-Baptiste LAMY

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os, os.path, sys, glob

HERE = os.path.dirname(sys.argv[0]) or "."

if len(sys.argv) <= 1: sys.argv.append("install")

import setuptools

setuptools.setup(
  name         = "Owlready2",
  version      = "0.5",
  license      = "LGPLv3+",
  description  = "A module for ontology-oriented programming in Python: load OWL 2.0 ontologies as Python objects, modify them, save them, and perform reasoning via HermiT. Includes an optimized RDF quadstore.",
  long_description = open(os.path.join(HERE, "README.rst")).read(),
  
  author       = "Lamy Jean-Baptiste (Jiba)",
  author_email = "jibalamy@free.fr",
  url          = "https://bitbucket.org/jibalamy/owlready2",
  classifiers  = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.6",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
    ],
  
  package_dir  = {"owlready2" : "."},
  packages     = ["owlready2"],
  package_data = {"owlready2" : ["owlready_ontology.owl", "hermit/*.*", "hermit/org/semanticweb/HermiT/cli/*"]},
)
