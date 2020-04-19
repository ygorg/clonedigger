#!/usr/bin/python

#    Copyright 2008 Peter Bulychev
#
#    This file is part of Clone Digger.
#
#    Clone Digger is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Clone Digger is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Clone Digger.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *
import sys

"""if __name__ == '__main__':
    sys.modules['clonedigger.logilab'] = __import__('logilab')"""

import os
import traceback
import logging
from optparse import OptionParser

from . import ast_suppliers
from . import clone_detection_algorithm
from . import arguments
from . import reports


def parse_file(file_name, func_prefixes, report, options, supplier):
    source_file = None
    try:
        logging.info('Parsing {}...'.format(file_name))
        sys.stdout.flush()
        if options.language == 'python':
            source_file = supplier(file_name, func_prefixes)
        else:
            # TODO implement func_prefixes for java also
            source_file = supplier(file_name)
        source_file.getTree().propagateCoveredLineNumbers()
        source_file.getTree().propagateHeight()
        report.addFileName(file_name)
    except:
        s = 'Error: can\'t parse "%s" \n: ' % (file_name,) + traceback.format_exc()
        report.addErrorInformation(s)
        logging.error(s)
    return source_file


def cli_arguments():
    cmdline = OptionParser(usage="""To run Clone Digger type:
python clonedigger.py [OPTION]... [SOURCE FILE OR DIRECTORY]...

The typical usage is:
python clonedigger.py source_file_1 source_file_2 ...
  or
python clonedigger.py path_to_source_tree
Don't forget to remove automatically generated sources, tests and third party
libraries from the source tree.

Notice:
The semantics of threshold options is discussed in the paper "Duplicate code detection
using anti-unification", which can be downloaded from the site http://clonedigger.sourceforge.net .
All arguments are optional. Supported options are:
""")
    cmdline.add_option('-l', '--language', dest='language', default='python',
                       type='choice', choices=['python', 'java', 'lua', 'javascript', 'js'],
                       help='the programming language')

    cmdline.add_option('--distance-threshold',
                       type='int', dest='distance_threshold',
                       help='the maximum amount of differences between pair of'
                       'sequences in clone pair (5 by default). Larger value leads'
                       'to larger amount of false positives')
    cmdline.add_option('--size-threshold',
                       type='int', dest='size_threshold',
                       help='the minimum clone size. The clone size for its turn'
                       ' is equal to the count of lines of code in its the largest fragment')

    cmdline.add_option('--clusterize-using-dcup',
                       action='store_true', dest='clusterize_using_dcup',
                       help='mark each statement with its D-cup value instead of'
                       ' the most similar pattern. This option together with '
                       '--hashing-depth=0 make it possible to catch all considered'
                       ' clones (but it is slow and applicable only to small programs)')
    cmdline.add_option('--fast',
                       action='store_true', dest='clusterize_using_hash',
                       help='find only clones, which differ in variable and function names and constants')
    cmdline.add_option('--clustering-threshold',
                       type='int', dest='clustering_threshold', default=10,
                       help='read the paper for semantics')
    cmdline.add_option('--hashing-depth',
                       type='int', dest='hashing_depth', default=1,
                       help='default value if 1, read the paper for semantics. '
                       'Computation can be speeded up by increasing this value '
                       '(but some clones can be missed)')

    # Deal with input
    cmdline.add_option('--no-recursion', dest='no_recursion',
                       action='store_true',
                       help='do not traverse directions recursively')
    cmdline.add_option('--ignore-dir',
                       action='append', dest='ignore_dirs', default=[],
                       help='exclude directories from parsing')
    cmdline.add_option('--file-list', dest='file_list',
                       help='a file that contains a list of file names that must'
                       ' be processed by Clone Digger')
    cmdline.add_option('--func-prefixes',
                       action='store', dest='f_prefixes', default=(),
                       help='skip functions/methods with these prefixes (provide'
                       ' a CSV string as argument)')

    # Deal with output
    cmdline.add_option('-o', '--output', dest='output',
                       help='the name of the output file ("output.html" by default)')
    cmdline.add_option('--eclipse-output',
                       dest='eclipse_output',
                       help='for internal usage only')
    cmdline.add_option('--cpd-output',
                       action='store_true', dest='cpd_output',
                       help='output as PMD''s CPD''s XML format. If output file '
                       'not defined, output.xml is generated')
    cmdline.add_option('--report-unifiers',
                       action='store_true', dest='report_unifiers',
                       help='')
    cmdline.add_option('-f', '--force',
                       action='store_true', dest='force',
                       help='By default clonedigger ignore statements with more '
                       'than 1000 elements.\nThis option prevent this behaviour.')
    cmdline.add_option('-v', '--verbose',
                       action='store_true',
                       help='Print informations')

    # Deal with displaying result
    cmdline.add_option('--dont-print-time',
                       action='store_false', dest='print_time',
                       help='do not print time')
    cmdline.add_option('--force-diff',
                       action='store_true', dest='use_diff',
                       help='force highlighting of differences based on the diff algorithm')

    return cmdline.parse_args()


def main():
    ##
    # Deal with CLI arguments
    ##

    (options, source_file_names) = cli_arguments()

    if options.verbose:
        logging.basicConfig(level=logging.INFO)

    if options.f_prefixes:
        options.f_prefixes = tuple([x.strip() for x in options.f_prefixes.split(',')])
    func_prefixes = options.f_prefixes

    if options.language != 'python':
        options.use_diff = True

    supplier = ast_suppliers.abstract_syntax_tree_suppliers[options.language]
    if not options.size_threshold:
        options.size_threshold = supplier.size_threshold
    if not options.distance_threshold:
        options.distance_threshold = supplier.size_threshold

    if options.cpd_output:
        # Kept here to specify the extension
        if options.output is None:
            options.output = 'output.xml'
        report = reports.CPDXMLReport()
    else:
        if options.output is None:
            options.output = 'output.html'
        report = reports.HTMLReport()

    output_file_name = options.output

    # Fill `arguments` from `options` (the variables are hard coded, they
    #  were retrieved by looking at what variable from `options` were used)
    setattr(arguments, 'clustering_threshold', options.clustering_threshold)
    setattr(arguments, 'clusterize_using_dcup', options.clusterize_using_dcup)
    setattr(arguments, 'clusterize_using_hash', options.clusterize_using_hash)
    setattr(arguments, 'hashing_depth', options.hashing_depth)
    setattr(arguments, 'force', options.force)
    setattr(arguments, 'use_diff', options.use_diff)
    setattr(arguments, 'print_time', options.print_time)
    setattr(arguments, 'report_unifiers', options.report_unifiers)
    setattr(arguments, 'eclipse_output', options.eclipse_output)
    setattr(arguments, 'size_threshold', options.size_threshold)
    setattr(arguments, 'distance_threshold', options.distance_threshold)

    ##
    # Deal with files
    ##

    # source_file_names is a list of files provided in the CLI

    # Add files from `file_list` to files to process
    if options.file_list is not None:
        with open(options.file_list) as f:
            source_file_names.extend(f.read().split())

    # Search for directories in source_file_name
    extended_source_file_names = []  # Copy source_file_names
    for file_name in source_file_names:
        # Add files from original `source_file_names`
        if not os.path.isdir(file_name):
            if os.path.splitext(file_name)[1][1:] == supplier.extension:
                extended_source_file_names.append(file_name)
            continue
        dir_name = file_name
        # Add files from `dir_name` if not ignored
        if options.no_recursion:
            if dir_name in options.ignore_dirs:
                continue
            files = [os.path.join(dir_name, f) for f in os.listdir(dir_name)]
            files = [f for f in files if os.path.splitext(f)[1][1:] == supplier.extension]
            extended_source_file_names.extend(files)
        else:
            for walked_dir_name, _, filenames in os.walk(dir_name):
                if walked_dir_name in options.ignore_dirs:
                    continue
                files = [os.path.join(walked_dir_name, f) for f in filenames]
                files = [f for f in files if os.path.splitext(f)[1][1:] == supplier.extension]
                extended_source_file_names.extend(files)

    source_file_names = extended_source_file_names

    ##
    # Parse files
    ##

    source_files = []  # Contains parsed files

    report.startTimer('Construction of AST')

    for file_name in source_file_names:
        source_file = parse_file(file_name, func_prefixes, report, options, supplier)
        if source_file:
            source_files.append(source_file)

    report.stopTimer()

    ##
    # Detect Clones
    ##

    duplicates = clone_detection_algorithm.findDuplicateCode(source_files, report)

    ##
    # Create report
    ##

    for duplicate in duplicates:
        report.addClone(duplicate)
    report.sortByCloneSize()

    try:
        report.writeReport(output_file_name)
    except:
        logging.error("catched error, removing output file")
        if os.path.exists(output_file_name):
            os.remove(output_file_name)
        raise


if __name__ == '__main__':
    main()
