# -*- coding: utf-8 -*-
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

from copy import copy

from .abstract_syntax_tree import AbstractSyntaxTree, free_variable_cost
from . import arguments

# NOTE that everywhere is written Unifier instead of AntiUnifier, for simplicity


class FreeVariable(AbstractSyntaxTree):
    """AST node used as placeholder for anti-unifiyng."""

    free_variables_count = 1  #: Count instanciation of this object

    def __init__(self):
        name = 'VAR({})'.format(FreeVariable.free_variables_count)
        FreeVariable.free_variables_count += 1
        AbstractSyntaxTree.__init__(self, name)


class Substitution(object):
    """A Dict[AbstractSyntaxTree, AbstractSyntaxTree] that replace recursively a
    tree by another.

    TODO: This could extend dict
    """
    def __init__(self, initial_value=None):
        if initial_value is None:
            initial_value = {}
        self._map = initial_value

    def substitute(self, tree, without_copying=False):
        """Recursively replace trees by substitution.

        :param tree: Tree to be substituted.
        :type tree: AbstractSyntaxTree
        :param without_copying: Return tree pointers, defaults to False
        :type without_copying: bool, optional
        :returns: Substituated tree
        :rtype: {AbstractSyntaxTree}
        """
        if tree in list(self._map.keys()):
            return self._map[tree]
        else:
            if isinstance(tree, FreeVariable):
                return tree
            if without_copying:
                return tree
            else:
                r = AbstractSyntaxTree(tree.getName())
                for child in tree.getChilds():
                    r.addChild(self.substitute(child, without_copying))
                return r

    def getMap(self):
        return self._map

    def getSize(self):
        """Compute size of a substitution.

        It is the sum of the size of the trees in substitution.

        :returns: Size of substitution.
        :rtype: {float}
        """
        ret = 0
        for tree in self.getMap().values():
            # TODO: Why  `- free_variable_cost` ?
            ret += tree.getSize(ignore_none=False) - free_variable_cost
        return ret


class Unifier(object):
    """An anti-unifier is a tree that generalize other trees (2) using placeholder.

    Example:
        Tree 1:       `Add (Name (i), Name (j))`
        Tree 2:       `Add (Name (n), Const (1))`
        Anti-unifier: `Add (Name (?1 ), ?2 )`

    Used in:
        - abstract_syntax_tree.PairSequences: used to compute distance between 2 trees
        - anti_unification.Cluster: used to add trees to cluster
        - report.Report: to know if there is a substitution between two code fragment and display them red or cyan

    From (Bulychev et al., 2008) II. A.:
    As the name suggests, given two terms, it produces a more general one that
    covers both rather than a more specific one as in unification. Let E1 and E2 be
    two terms. Term E is a generalization of E1 and E2 if there exist two
    substitutions σ1 and σ2 such that σ1(E) = E1 and σ2(E) = E2. The most specific
    generalization of E1 and E2 is called anti-unifier. The process of finding an
    anti-unifier is called anti-unification.
    [...]
    The anti-unifier tree of two trees T1 and T2 is obtained by replacing some
    subtrees in T1 and T2 by special nodes, containing term placeholders which are
    marked with integers. We will represent such nodes as ?n. For example, the
    anti-unifier of `Add (Name (i), Name (j))` and `Add (Name (n), Const (1))` will
    be `Add (Name (?1 ), ?2 )`.
    In some abstract syntax tree representations occurrences of the same variable
    refer to the same leaf in a tree. In this case the anti-unifier of
    `Add(Name(i),Name(i))` and `Add(Name(j),Name(j))` will be `Add(Name(?1),Name(?1))`.

    :param t1: Tree 1
    :type t1: AbstractSyntaxTree
    :param t2: Tree 2
    :type t2: AbstractSyntaxTree
    :param ignore_parametrization: todo:
    :type ignore_parametrization: bool, optional
    """
    def __init__(self, t1, t2, ignore_parametrization=False):
        (self._unifier, self._substitutions) = self._unify(t1, t2, ignore_parametrization)
        self._unifier.storeSize()
        for i in (0, 1):
            for key in self._substitutions[i].getMap():
                self._substitutions[i].getMap()[key].storeSize()

    def getSubstitutions(self):
        return self._substitutions

    def getUnifier(self):
        return self._unifier

    def getSize(self):
        return sum([s.getSize() for s in self.getSubstitutions()])

    def _combineSubs(self, node, s, t, ignore_parametrization=False):
        """Aggregate substitutions.

        Given an anti-unifier and two substitutions,
        modify node by replacing trees if the substittion are the same.
        If ignore_parametrization is True, this function morally performs `t.update(s)`.
        Else: some keys are not updated, but they will modify the `node`.

        :param node: anti-unifier
        :type node: AbstractSyntaxTree
        :param s: A substitution to use as update
        :type s: Tuple[Substitution,Substitution]]
        :param t: A substitution to update
        :type t: Tuple[Substitution,Substitution]]
        :param ignore_parametrization: TODO:, defaults to False
        :type ignore_parametrization: bool, optional
        :returns: an updated unifier
        :rtype: {Tuple[AbstractSyntaxTree, Tuple[Substitution,Substitution]]}
        """
        # s and t are 2-tuples
        assert s[0].getMap().keys() == s[1].getMap().keys()
        assert t[0].getMap().keys() == t[1].getMap().keys()
        newt = (copy(t[0]), copy(t[1]))
        relabel = {}
        for si in s[0].getMap():
            if not ignore_parametrization:
                found = False
                for ti in t[0].getMap():
                    # For two trees the same substitution is performed
                    # This is a pattern of substitution??
                    if (s[0].getMap()[si] == t[0].getMap()[ti]) and (s[1].getMap()[si] == t[1].getMap()[ti]):
                        # if s[si] == t[ti]  # the values of substitution is the same
                        relabel[si] = ti
                        found = True
                        break
            if ignore_parametrization or not found:
                # Add s[si] to t
                newt[0].getMap()[si] = s[0].getMap()[si]
                newt[1].getMap()[si] = s[1].getMap()[si]

        mod_node = Substitution(relabel).substitute(node)
        return (mod_node, newt)

    def _unify(self, node1, node2, ignore_parametrization):
        """Create anti-unifier for node1 and node2.

        Recursively create an anti-unifier using substitutions.

        :param node1: Tree to be anti-unified
        :type node1: AbstractSyntaxTree
        :param node2: Tree to be anti-unified
        :type node2: AbstractSyntaxTree
        :param ignore_parametrization: todo:
        :type ignore_parametrization: bool
        :returns: An anti-unifier and the substitutions performed.
        :rtype: {Tuple[AbstractSyntaxTree, Tuple[Substitution,Substitution]]}
        """
        if node1 == node2:
            # Two nodes are the same. From (Bulychev et al., 2008): II. A.
            # [...] the abstract syntax trees we use are not always trees, since
            # leaves containing the same variable references may be merged, [...]
            return (node1, (Substitution(), Substitution()))
        elif (node1.getName() != node2.getName()) or (node1.getChildCount() != node2.getChildCount()):
            # Nodes are different, replace node1 and node2 by a Free variable
            var = FreeVariable()
            return (var, (Substitution({var: node1}), Substitution({var: node2})))
        else:
            # Same name AND number of childs
            s = (Substitution(), Substitution())
            name = node1.getName()
            retNode = AbstractSyntaxTree(name)
            count = node1.getChildCount()
            for i in range(count):
                # Find anti-unifier for the childs
                (ai, si) = self._unify(
                    node1.getChilds()[i], node2.getChilds()[i],
                    ignore_parametrization)
                # ai: anti-unifier tree
                # si: substitutions from node1 and node2 to ai
                (ai, s) = self._combineSubs(
                    ai, si, s, ignore_parametrization)
                retNode.addChild(ai)
            return (retNode, s)


class Cluster(object):
    """Create a cluster consisting of AbstractSyntaxTree

    TODO: how it is used

    :param tree: First element to add, defaults to None
    :type tree: AbstractSyntaxTree, optional
    """
    count = 0  # Cluster instanciation counter, used as identifier

    def __init__(self, tree=None):
        self._n = 0  # TODO: this is len(self._trees)
        self._unifier_tree = None  # Anti-unifier of trees in cluster, if added via self.unify()
        self._trees = []  # List of trees in cluster
        self._max_covered_lines = 0  # Maximum lines covered by a tree in the cluster
        if tree:
            self._n = 1
            self._trees = [tree]
            self._max_covered_lines = len(tree.getCoveredLineNumbers())
            # TODO: replace by self.addWithoutUnification(tree)
            self._unifier_tree = tree
        Cluster.count += 1
        self._cluster_number = Cluster.count

    def getMaxCoveredLines(self):
        return self._max_covered_lines

    def getUnifierSize(self):
        return self.getUnifierTree().getSize()

    def getCount(self):
        return self._n

    def getAddCost(self, tree):
        """Compute the cost of adding a tree to the cluster.

        :param tree: tree
        :type tree: AbstractSyntaxTree
        """
        unifier = Unifier(self.getUnifierTree(), tree)
        # TODO: shouldn't this be count * (sub[0] + sub[1]) ??
        return (self.getCount() * unifier.getSubstitutions()[0].getSize() + unifier.getSubstitutions()[1].getSize())

    # Set tree

    def unify(self, tree):
        """Add tree to cluster by unifying cluster's unifier with `tree`.

        :param tree: Tree
        :type tree: AbstractSyntaxTree
        """
        # TODO: why isn't self._max_covered_lines updated here ?
        self._n += 1
        self._unifier_tree = Unifier(self.getUnifierTree(), tree).getUnifier()
        self._trees.append(tree)

    def addWithoutUnification(self, tree):
        """Add tree to cluster without updating unifier_tree

        :param tree: Tree
        :type tree: AbstractSyntaxTree
        """
        self._n += 1
        self._trees.append(tree)
        if len(tree.getCoveredLineNumbers()) > self._max_covered_lines:
            self._max_covered_lines = len(tree.getCoveredLineNumbers())

    def eraseAllTrees(self):
        self._n = 0
        self._trees = []

    # Get tree

    def getUnifierTree(self):
        return self._unifier_tree
