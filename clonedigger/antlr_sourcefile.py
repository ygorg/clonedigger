from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *
from builtins import object
#    Copyright 2008 Peter Bulychev
#    http://clonedigger.sourceforge.net
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

import os
import logging
import xml.parsers.expat
from .abstract_syntax_tree import *


class ExpatHandler(object):

    def __init__(self, start_node, parent):
        self.parent = parent
        self.stack = [start_node]

    def start_element(self, xml_node_name, attrs):
        line_number = int(attrs["line_number"]) - 1
        line_numbers = [line_number]
        if line_numbers == [-1]:
            line_numbers = []
        name = attrs["name"]
        r = AbstractSyntaxTree(name, line_numbers, self.parent)
        if xml_node_name == "statement_node" or name in ["stat", "chunk"]:
            r.markAsStatement()
        else:
            assert(xml_node_name == "node")
        self.stack[-1].addChild(r)
        self.stack.append(r)

    def end_element(self, name):
        self.stack.pop()


class ANTLRSourceFile(SourceFile):

    def __init__(self, file_name):
        SourceFile.__init__(self, file_name)
        self.extension = None
        self.producer_type = None
        self.antlr_run = None
        self.size_threshold = None
        self.distance_threshold = None

    def parse(self, file_name):
        tree_file_name = 'temporary_ast.xml'
        current_directory = os.path.realpath(os.path.dirname(__file__))
        producer_class_path = os.path.join(
            current_directory, self.producer_type, 'TreeProducer.jar')
        antlr_class_path = os.path.join(
            current_directory, 'antlr_runtime', self.antlr_run)
        if os.name in ['mac', 'posix']:
            class_path_delimeter = ':'
        elif os.name in ['nt', 'dos', 'ce']:
            class_path_delimeter = ';'
        else:
            logging.error('unsupported OS')
            assert 0

        command = (
            'java -classpath ' + producer_class_path +
            class_path_delimeter + antlr_class_path +
            ' TreeProducer %s %s 2>err.log' % (file_name, tree_file_name))
        input(command)
        if os.system(command):
            with open('err.log') as f:
                s = f.read()
            raise Exception(s)

        self._tree = AbstractSyntaxTree('program')
        handler = ExpatHandler(self._tree, self)
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = handler.start_element
        p.EndElementHandler = handler.end_element
        with open(tree_file_name) as f:
            p.Parse(f.read())
        os.remove(tree_file_name)


class JavaANTLRSourceFile(ANTLRSourceFile):
    extension = 'java'
    size_threshold = 10
    distance_threshold = 7

    def __init__(self, file_name):
        ANTLRSourceFile.__init__(self, file_name)

        self.producer_type = 'java_antlr'
        self.antlr_run = 'runtime-2008-01-10.16.jar'
        # self.antlr_run = 'antlr-4.7.1-complete.jar'

        self.parse(file_name)


class JsANTLRSourceFile(ANTLRSourceFile):
    extension = 'js'
    size_threshold = 5
    distance_threshold = 5

    def __init__(self, file_name):
        ANTLRSourceFile.__init__(self, file_name)

        self.producer_type = 'js_antlr'
        self.antlr_run = 'antlr-3.1.1.jar'

        self.parse(file_name)


class LuaANTLRSourceFile (ANTLRSourceFile):
    extension = 'lua'
    size_threshold = 5
    distance_threshold = 5

    def __init__(self, file_name):
        ANTLRSourceFile.__init__(self, file_name)

        self.producer_type = 'lua_antlr'
        self.antlr_run = 'antlr-runtime-3.1.jar'

        self.parse(file_name)
