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

"""abstract_syntax_tree module

.. todo:: What do free_variable_cost represent ?
.. todo:: Move free_variable_cost to FreeVariable.free_variable_cost
"""

"""from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import *
from builtins import object
"""

from . import arguments

free_variable_cost = 0.5


def filter_func(s):
    """Remove trailing whitespace if begins with non space characters

    .. todo:: Equivalent of re.sub(r'[^\s]+)\s*', r'\1', s) ?

    :param s: String to be filtered
    :type s: str
    :returns: Trimmed string
    :rtype: {str}

    >>> filter_func('def function(): \\n')
    'def function():'
    >>> filter_func('\\n \\n')
    '\\n \\n'
    """
    for i in range(len(s) - 1, -2, -1):
        # Find first character from end that is not a space
        if i < 0 or not s[i].isspace():
            break
    # If found trim
    if i >= 0:
        return s[:i + 1]
    else:
        return s


class SourceFile(object):
    """Abstract class that create AST from a code file.

    Read a code file, parse it and create a corresponding AST.

    :param _source_lines: Original lines of the source file.
    :type _source_lines: List[str]
    :param _file_name: Name of the source file.
    :type _file_name: str
    :param _tree: AST representing the source file.
    :type _tree: AbstractSyntaxTree
    """
    size_threshold = 5  #: Minimum number of covered lines of a clone.
    distance_threshold = 5  #: Maximum edit distance of a clone.

    def __init__(self, file_name):
        with open(file_name, 'r') as f:
            self._source_lines = [filter_func(s) for s in f]
        self._file_name = file_name
        self._tree = None

    def getSourceLine(self, n):
        """Return n-th line of the file

        :param n: Line number
        :type n: int
        :returns: n-th line of self._file_name
        :rtype: {str}
        """
        # if n >= len(self._source_lines):
        #     return ''
        # TODO
        # error here
        return self._source_lines[n]

    def _setTree(self, tree):
        self._tree = tree

    def getTree(self):
        return self._tree

    def getFileName(self):
        return self._file_name


class AbstractSyntaxTree(object):
    """Tree structure representing code.

    From (Bulychev et al., 2008): II. A.
    Strictly speaking, the abstract syntax trees we use are not always trees, since
    leaves containing the same variable references may be merged, [...].

    A statement (stmt) is a node in the tree that contains an particular tree of code.
    It is defined by the Language, see `simple statements <https://docs.python.org/2/reference/simple_stmts.html>`_
    and `compound statements <https://docs.python.org/2/reference/compound_stmts.html>`_.
    A (really) non exhaustive example (made by printing a tree):

    - a class is a statement
    - an assignement using only builtin operation is a statement
    - __init__ function is a statement
    - global is a statement

    But:

    - a += is not a statement
    - return is not
    - calling a function is not
    - print is not
    - defining a function is not

    .. todo:: Why is += not a stmt, as it is a simple stmt according to the reference.
        Same for function definition.
    .. todo:: self._line_numbers is only used to initialize _covered_line_numbers
        in self.propagateCoveredLineNumbers. Remove the attribute and initialize
        _covered_line_numbers ?
    .. todo: self.getLineNumbers is never used anywhere

    :param _name: Name of the node
    :type _name: str
    :param _source_file: SourceFile containing this tree
    :type _source_file: SourceFile
    :param _line_numbers: Index of lines covered by the tree.
    :type _line_numbers: List[int]
    :param _covered_line_numbers: Line covered by the tree and subtrees
    :type _covered_line_numbers: List[int]
    :param _is_statement: This tree is a statement
    :type _is_statement: bool

    :param _hash: Hash of the tree
    :type _hash: int
    :param _mark: Used for clustering
    :type _mark: Cluster

    :param _parent: Parent node
    :type _parent: AbstractSyntaxTree
    :param _childs: List of child nodes
    :type _childs: List[AbstractSyntaxTree]
    :param _height: Depth of the tree
    :type _height: int
    :param _size: Number of node + free variable costs
    :type _size: float
    :param _none_count: Number of None node in subtrees
    :type _none_count: int
    """

    def __init__(self, name=None, line_numbers=[], source_file=None):
        self._name = name
        self._source_file = source_file
        # TODO: Arg is used in ExpatHandler.start_element, PythonCompilerSourceFile.rec_build_tree
        self._line_numbers = line_numbers
        # TODO: Arg is used in ExpatHandler.start_element, PythonCompilerSourceFile.rec_build_tree
        self._covered_line_numbers = None
        self._is_statement = False

        self._hash = None
        self._mark = None

        self._parent = None
        self._childs = []
        self._height = None
        self._size = None
        self._none_count = None

    # Members operations

    def getSourceFile(self):
        return self._source_file

    def getMark(self):
        return self._mark

    def setMark(self, mark):
        self._mark = mark

    def isStatement(self):
        return self._is_statement

    def markAsStatement(self, val=True):
        self._is_statement = val

    def getName(self):
        return self._name

    def setName(self, name):
        self._name = name

    def getLineNumbers(self):
        # TODO: Unused
        return self._line_numbers

    # Tree operations

    def getParent(self):
        return self._parent

    def setParent(self, parent):
        self._parent = parent

    def getChilds(self):
        return self._childs

    def getChildCount(self):
        return len(self._childs)

    def addChild(self, child, save_parent=False):
        """Add a child and set its parent to self if save_parent

        :param child: Child to add
        :type child: AbstractSyntaxTree
        :param save_parent: Set child's parent to self, defaults to False
        :type save_parent: bool, optional
        """
        if not save_parent:
            child.setParent(self)
        self._childs.append(child)

    def getCoveredLineNumbers(self):
        return self._covered_line_numbers

    def propagateCoveredLineNumbers(self):
        """Compute self._covered_line_numbers for self and childrens

        :returns: A set of line numbers
        :rtype: {Set[int]}
        """
        self._covered_line_numbers = set(self._line_numbers)
        for child in self.getChilds():
            self._covered_line_numbers.update(
                child.propagateCoveredLineNumbers())
        return self._covered_line_numbers

    def getHeight(self):
        """Return height for this tree

        The height is the maximum depth of the tree

        :returns: Height of tree
        :rtype: {int}
        """
        return self._height

    def propagateHeight(self):
        """Compute height for this tree

        The height is the maximum depth of the tree

        :returns: Height of self
        :rtype: {int}
        """
        if self.getChildCount() == 0:
            self._height = 0
        else:
            self._height = max(c.propagateHeight() for c in self.getChilds()) + 1
        return self._height

    def getAncestors(self):
        """Return ancestors which are statements.

        Used only in StatementSequence.getAncestors.

        :returns: Ancestors that are statements
        :rtype: {List[AbstractSyntaxTree]}
        """
        r = []
        t = self.getParent()
        while t:
            if t.isStatement():
                r.append(t)
            t = t.getParent()
        return r

    def getSourceLines(self):
        """Return source lines covered by the tree

        :returns: A list of lines
        :rtype: {List[str]}
        """
        source_line_numbers = self.getCoveredLineNumbers()
        source_line_numbers_list = sorted(
            range(min(source_line_numbers),
                  max(source_line_numbers) + 1))
        getLine = lambda i: self.getSourceFile().getSourceLine(i)
        return [getLine(i) for i in source_line_numbers_list]

    def getAllStatementSequences(self):
        """Return sequences of statement that cover at least *arguments.size_threshold* lines.

        Recursively search for statements, a new sequence is created when the lines
        covered by the sequence exceeds arguments.size_threshold.

        .. todo:: Are the sequence in a specific order and what do they represent ?
        .. todo:: Is it possible that a subtree `s` of `t` and `t` are in the same sequence ?

        :returns: todo:
        :rtype: {List[StatementSequence]}
        """
        r = []
        current = StatementSequence()
        for child in self.getChilds():
            if child.isStatement():
                current.addStatement(child)
            elif (not current.isEmpty()) and len(current.getCoveredLineNumbers()) >= arguments.size_threshold:
                # The current StatementSequence is full, make a new one
                r.append(current)
                current = StatementSequence()
            r.extend(child.getAllStatementSequences())
        if (not current.isEmpty()) and len(current.getCoveredLineNumbers()) >= arguments.size_threshold:
            r.append(current)
        return r

    def getSize(self, ignore_none=True):
        """Return number of nodes and free variables cost

        :param ignore_none: Do not account for None nodes, defaults to True
        :type ignore_none: bool, optional
        :returns: size of tree
        :rtype: {float}
        """
        ret = self._size
        if ignore_none:
            ret -= self._none_count
        return ret

    def storeSize(self):
        """Compute the number of nodes and free variables cost recursively

        The number of nodes and `free_variable_cost`, also compute the number
        of None node

        :returns: Size of tree
        :rtype: {float}
        """
        observed = set()
        self._none_count = 0

        def rec_calc_size(t):
            r = 0
            if t in observed:
                return r

            if t.getChildCount():
                for c in t.getChilds():
                    r += rec_calc_size(c)
            else:
                observed.add(t)
                if t.getName() == 'None':
                    self._none_count += 1
                if t.__class__.__name__ == 'FreeVariable':
                    r += free_variable_cost
                else:
                    r += 1
            return r
        if self._size is None:
            self._size = rec_calc_size(self)

    def getTokenCount(self):
        """Count certain tokens in tree

        Tokens are listed below

        :returns: Number of tokens
        :rtype: {int}

        .. todo:: What is this ? `t.getName()[0] != "'" and t.getName() != 'Pass'`
        """
        valid_tokens = ['Add', 'Assign', 'Sub', 'Div', 'Mul', 'Mod',
                        'Function', 'If', 'Class', 'Raise']

        def rec_calc_size(t):
            if t.getChildCount():
                r = 0
                if t.getName() in valid_tokens:
                    r = 1
                for c in t.getChilds():
                    r += rec_calc_size(c)
            else:
                # self is leaf
                if t.getName()[0] != "'" and t.getName() != 'Pass':
                    # TODO: What is this ?
                    return 0
                else:
                    return 1
            return r
        return rec_calc_size(self)

    # Compute hashes

    def getDCupHash(self, level):
        """Compute a hash using child nodes

        The hash is computed by summing per node hashes. A node hash is made of
        the depth of the node, the name and the number of child.

        :param level: maximum depth to compute hash
        :type level: int
        :returns: a tree hash
        :rtype: {int}
        """
        ret = 0  # in case of names and constants
        if len(self._childs):
            ret = (level + 1) * hash(self._name) * len(self._childs)
        # if level == -1, it will not stop until it reaches the leaves
        if level != 0:
            for i in range(len(self._childs)):
                child = self._childs[i]
                ret += (i + 1) * child.getDCupHash(level - 1)
        return hash(ret)

    def getFullHash(self):
        """Compute a hash for the whole tree

        :returns: a tree hash
        :rtype: {int}
        """
        return self.getDCupHash(-1)

    def __hash__(self):
        # TODO check correctness
        if not self._hash:
            self._hash = hash(self.getDCupHash(3) + hash(self.getName()))
        return self._hash

    def __str__(self):
        return ' ( {} {} ) '.format(
            self.getName(),
            ' '.join(map(str, self.getChilds())))

    def __eq__(self, tree2):
        tree1 = self
        if tree2 is None:
            return False
        if tree1.getName() != tree2.getName():
            return False
        if tree1.getChildCount() != tree2.getChildCount():
            return False
        for i in range(tree1.getChildCount()):
            if tree1.getChilds()[i] != tree2.getChilds()[i]:
                return False
        return True


class StatementSequence(object):
    """Holds a sequence of statements (AST)

    Used in suffix_tree.SuffixTree to find patterns in code.

    :param _sequence: A sequence of Statement.
    :type _sequence: List[AbstractSyntaxTree]
    :param _source_file: Source file Statements are from.
    :type _source_file: SourceFile
    """
    def __init__(self, sequence=[]):
        self._sequence = []
        self._source_file = None
        for s in sequence:
            self.addStatement(s)

    def isEmpty(self):
        return self._sequence == []

    def getSourceFile(self):
        return self._source_file

    def getLength(self):
        return len(self)

    def addStatement(self, statement):
        self._sequence.append(statement)
        if self._source_file is None:
            self._source_file = statement.getSourceFile()
        else:
            assert(self._source_file == statement.getSourceFile())

    def __getitem__(self, *args):
        return self._sequence.__getitem__(*args)

    def __len__(self):
        return self._sequence.__len__()

    def __str__(self):
        return ','.join(map(str, self))

    # Line counting/getting operations

    def getSourceLines(self):
        r = []
        for statement in self:
            r.extend(statement.getSourceLines())
        return r

    def getLineNumbers(self):
        # TODO: Unused
        r = []
        for statement in self:
            r.extend(statement.getLineNumbers())
        return r

    def getCoveredLineNumbers(self):
        r = set()
        for s in self:
            r.update(s.getCoveredLineNumbers())
        return r

    def getCoveredLineNumbersCount(self):
        return len(self.getCoveredLineNumbers())

    def getLineNumberHashables(self):
        """Return covered line numbers as (source_file, line_number)

        Return tuples so aggregating line numbers from different files will not
        overwrite line numbers from different files.

        .. todo:: rename function to getCoveredLineNumbersSourceFile ? or merge
            with getCoveredLineNumbers by adding a parameter ?

        :returns: List of covered line numbers
        :rtype: {List[Tuple[str, int]]}
        """
        source_file_name = self.getSourceFile().getFileName()
        line_numbers = self.getCoveredLineNumbers()
        return set([(source_file_name, line_number) for line_number in line_numbers])


    # Tree operation

    def constructTree(self):
        """Create a tree where childrens are the element of the sequence.

        Used in PairSequences to compute distance between two sequences.

        :returns: A tree containing every element of the sequence.
        :rtype: {AbstractSyntaxTree}
        """
        tree = AbstractSyntaxTree('__SEQUENCE__')
        for statement in self:
            tree.addChild(statement, True)
        return tree

    def getAncestors(self):
        """Return ancestors of first element

        Used only in clone_detection_algorithm.remove_dominated_clones. Depends
        on AST.getAllStatementSequences.

        .. todo:: Why self[0], and not a set of all ancestors of every statement ?
        """
        return self[0].getAncestors()

    def getWeight(self):
        """Unused

        .. todo:: AST.getCluster does not exist
        .. todo:: unused
        """
        return sum([s.getCluster().getUnifierSize() for s in self._sequence])


class PairSequences(object):
    def __init__(self, sequences):
        self._sequences = sequences

    def __getitem__(self, *args):
        return self._sequences.__getitem__(*args)

    def __str__(self):
        return ';\t'.join([str(s) for s in self])

    def getWeight(self):
        """Unused

        .. todo:: unused
        """
        assert(self[0].getWeight() == self[1].getWeight())
        return self[0].getWeight()

    def calcDistance(self):
        from . import anti_unification
        trees = [s.constructTree() for s in self]
        unifier = anti_unification.Unifier(trees[0], trees[1])
        return unifier.getSize()

    def subSequence(self, first, length):
        return PairSequences([StatementSequence(self[0][first:first + length]), StatementSequence(self[1][first:first + length])])

    def getLength(self):
        """Return length of first sequence

        .. todo:: Is len(self[0]) and len(self[1]) always equal ?
        """
        return self[0].getLength()

    def getMaxCoveredLineNumbersCount(self):
        return min([s.getCoveredLineNumbersCount() for s in self])
