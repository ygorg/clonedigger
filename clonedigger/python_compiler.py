from __future__ import absolute_import
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

import compiler

from .abstract_syntax_tree import AbstractSyntaxTree, SourceFile


class PythonNodeLeaf:
    def __init__(self, val):
        self._val = val

    def getVal(self):
        return self._val

    def as_string(self):
        return str(self.getVal())

    def __str__(self):
        return self.as_string()


def flatten(lst):
    """Recursively flatten a list

    :param lst: An iterable which can contain other iterables
    :type lst: iterable
    :returns: A flattened list without iterables
    :rtype: {List}
    """
    l = []
    for elt in lst:
        t = type(elt)
        if t is tuple or t is list:
            for elt2 in flatten(elt):
                l.append(elt2)
        else:
            l.append(elt)
    return l


def add_childs(childs, r, is_statement, source_file):
    # Calls rec_build_tree on `childs`
    assert isinstance(childs, list)
    for child in childs:
        assert isinstance(child, compiler.ast.Node)
        t = source_file.rec_build_tree(child, is_statement)
        if t.getName() in source_file.ignored_statements:
            # TODO move it up
            continue
        t.setParent(r)
        r.addChild(t)


def add_leaf_child(child, name, r):
    assert not isinstance(child, list)
    assert not isinstance(child, compiler.ast.Node)
    t = AbstractSyntaxTree(repr(child))
    t.setParent(r)
    l = PythonNodeLeaf(child)
    t.ast_node = l
    r.addChild(t)
    # How is this different from `a[i] = l`
    setattr(r.ast_node, name, l)
    return t


def add_leaf_childs(childs, name, r):
    assert isinstance(childs, list) or isinstance(childs, tuple)
    a = getattr(r.ast_node, name)
    for i in range(len(childs)):
        child = childs[i]
        assert not isinstance(child, compiler.ast.Node)
        t = AbstractSyntaxTree(repr(child))
        t.setParent(r)
        l = PythonNodeLeaf(child)
        t.ast_node = l
        r.addChild(t)
        # How is this different from `setattr(r.ast_node, name, l)`
        a[i] = l


def add_leaf_string_childs(childs, r):
    assert isinstance(childs, list)
    for child in childs:
        assert not isinstance(child, compiler.ast.Node)
        t = AbstractSyntaxTree(repr(child))
        # Is this right ? Should it not be t.setParent(r) ?
        t.setParent(t)
        r.addChild(t)


class PythonCompilerSourceFile(SourceFile):
    extension = 'py'
    distance_threshold = 5
    size_threshold = 5
    ignored_statements = ['Import', 'From']

    def __init__(self, file_name, func_prefixes=()):
        SourceFile.__init__(self, file_name)
        self._func_prefixes = func_prefixes

        parsed = compiler.parseFile(file_name)
        self._setTree(self.rec_build_tree(parsed))

    def rec_build_tree(self, node, is_statement=False):

        if isinstance(node, compiler.ast.Node):
            name = node.__class__.__name__
            if name == 'Function':
                for prefix in self._func_prefixes:
                    if node.name.startswith(prefix):
                        # skip function that matches pattern
                        return AbstractSyntaxTree('none')
            if name in ['Function', 'Class']:
                # ignoring class and function docs
                node.doc = None
            if node.lineno:
                lines = [node.lineno - 1]
            else:
                lines = []
            r = AbstractSyntaxTree(name, lines, self)
            r.ast_node = node
            if is_statement and node.lineno:
                r.markAsStatement()
            is_statement = (name == 'Stmt')
            if name == "AssAttr":
                add_childs([node.expr], r, is_statement, self)
                add_leaf_child(node.attrname, 'attrname', r)
                add_leaf_string_childs([node.flags], r)
            elif name == "AssName":
                add_leaf_child(node.name, 'name', r)
                # add_leaf_child(node.flags, 'flags', r)
            elif name == "AugAssign":
                add_childs([node.node], r, is_statement, self)
                add_leaf_child(node.op, 'op', r)
                add_childs([node.expr], r, is_statement, self)
            elif name == "Class":
                add_leaf_child(node.name, 'name', r)
                # print '>>>>>>>>>>>>>>>>>>>>', flatten(node.bases)
                add_childs(flatten(node.bases), r, is_statement, self)
                # add_leaf_child(node.doc, 'doc', r) we don't want class docs in our tree, do we?
                add_childs([node.code], r, is_statement, self)
            elif name == "Compare":
                add_childs([node.expr], r, is_statement, self)
                for i in range(len(node.ops)):
                    (op, expr) = node.ops[i]
                    t = add_leaf_child(op, 'op', r)
                    add_childs([expr], r, is_statement, self)
                    node.ops[i] = (t.ast_node, expr)
            elif name == "Const":
                add_leaf_child(repr(node.value), "value", r)
            # elif name == "From":
                # add_leaf_child(node.modname, "modname", r)
                # add_childs(node.names, r, is_statement, self)
            elif name == "Function":
                # add_childs(node.decorators, r, is_statement, self)  FIXME do we need that?
                add_leaf_child(node.name, "name", r)
                add_leaf_childs(node.argnames, "argnames", r)
                if node.defaults == ():
                    node.defaults = []
                # TODO incomment and fix
                add_childs(node.defaults, r, is_statement, self)
                add_leaf_string_childs([node.flags], r)
                # add_leaf_child(node.doc, "doc", r) same as class docs... we don't need them
                add_childs([node.code], r, is_statement, self)
            elif name == "Getattr":
                add_childs([node.expr], r, is_statement, self)
                add_leaf_child(node.attrname, "attrname", r)
            elif name == "Global":
                add_leaf_childs(node.names, "names", r)
            # elif name == "Import":
                # add_leaf_childs(node.names, "names", r)
            elif name == "Keyword":
                add_leaf_child(node.name, "name", r)
                add_childs([node.expr], r, is_statement, self)
            elif name == "Lambda":
                # TODO: uncomment and fix
                add_leaf_childs(node.argnames, "argnames", r)
                if node.defaults == ():
                    node.defaults = []
                add_childs(node.defaults, r, is_statement, self)
                add_childs([node.code], r, is_statement, self)
            elif name == "Name":
                # the most important one :)
                add_leaf_child(node.name, "name", r)
            else:
                for c in node.getChildren():
                    t = self.rec_build_tree(c, is_statement)
                    if t.getName() in self.ignored_statements:
                        continue
                    t.setParent(r)
                    r.addChild(t)
            return r
        else:
            return AbstractSyntaxTree(repr(node))
