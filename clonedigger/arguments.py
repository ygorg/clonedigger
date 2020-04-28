"""from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import *
from builtins import object"""

# This file is used as a namespace to hold useful arguments from the CLI

clustering_threshold = None
clusterize_using_dcup = None  # How to compute hash and ?
clusterize_using_hash = None  # How to compute hash and ?
hashing_depth = None  # How to compute hash if ?
force = None  # Process big statements and ?
use_diff = None
print_time = None
report_unifiers = None
eclipse_output = None

distance_threshold = None  # Minimal edit distance to consider a candidate clone to be a clone
size_threshold = None  # Minimal size of statements

# Used in
# clonedigger.cli_arguments :
#    distance_threshold, size_threshold (set from suplier)
# abstract_syntax_tree.getAllStatementSequences :
#    size_threshold
# clone_detection_algorithm.py :
#    clustering_threshold, clusterize_using_dcup, clusterize_using_hash,
#    hashing_depth, force,
#    report_unifiers,
#    distance_threshold, size_threshold,
# reports.py :
#    clustering_threshold, clusterize_using_dcup, clusterize_using_hash,
#    hashing_depth, use_diff, print_time
#    distance_threshold, size_threshold

# All options are set here to be used everywhere -> define a dictionnary and pass it as `context` or whathever
