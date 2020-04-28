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

from . import arguments

# TODO: What is this ?
free_variable_cost = 0.5


def filter_func(s):
    for i in range(len(s) - 1, -2, -1):
        if i < 0 or not s[i].isspace():
            break
    if i >= 0:
        return s[:i + 1]
    else:
        return s


class SourceFile(object):
    size_threshold = 5
    distance_threshold = 5

    def __init__(self, file_name):
        with open(file_name, 'r') as f:
            self._source_lines = [filter_func(s) for s in f]
        self._file_name = file_name
        self._tree = None  # AbstractSyntaxTree

    def getSourceLine(self, n):
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
    """
    def __init__(self, name=None, line_numbers=[], source_file=None):
        self._line_numbers = line_numbers
        self._source_file = source_file  # SourceFile containing this tree
        self._name = name  # Name of the node
        self._hash = None  # Hash of the tree
        self._is_statement = False  # TODO: What is this ?
        self._mark = None  # Used for clustering

        self._covered_line_numbers = None  # Line covered by the tree and subtrees
        self._height = None  # Depth of the tree
        self._size = None  # Number of node + free variable costs
        self._none_count = None  # Number of None node in subtrees
        self._parent = None  # Parent node
        self._childs = []  # List of child nodes

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
        """Return statement ancestors

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
        # TODO: What is a statement ?
        r = []
        current = StatementSequence()
        for child in self.getChilds():
            if child.isStatement():
                current.addStatement(child)
            elif (not current.isEmpty()) and len(current.getCoveredLineNumbers()) >= arguments.size_threshold:
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
    def __init__(self, sequence=[]):
        self._sequence = []
        self._source_file = None
        for s in sequence:
            self.addStatement(s)

    def isEmpty(self):
        return self._sequence == []

    def getSourceFile(self):
        return self._source_file

    def getCoveredLineNumbers(self):
        r = set()
        for s in self:
            r.update(s.getCoveredLineNumbers())
        return r

    def getAncestors(self):
        return self[0].getAncestors()

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

    def getWeight(self):
        return sum([s.getCluster().getUnifierSize() for s in self._sequence])

    def getSourceLines(self):
        r = []
        for statement in self:
            r.extend(statement.getSourceLines())
        return r

    def getLineNumbers(self):
        r = []
        for statement in self:
            r.extend(statement.getLineNumbers())
        return r

    def getLineNumberHashables(self):
        source_file_name = self.getSourceFile().getFileName()
        line_numbers = self.getCoveredLineNumbers()
        return set([(source_file_name, line_number) for line_number in line_numbers])

    def constructTree(self):
        tree = AbstractSyntaxTree('__SEQUENCE__')
        for statement in self:
            tree.addChild(statement, True)
        return tree

    def getCoveredLineNumbersCount(self):
        covered = set()
        for t in self:
            covered.update(t.getCoveredLineNumbers())
        return len(covered)


class PairSequences(object):
    def __init__(self, sequences):
        self._sequences = sequences

    def __getitem__(self, *args):
        return self._sequences.__getitem__(*args)

    def __str__(self):
        return ';\t'.join([str(s) for s in self])

    def getWeight(self):
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
        return self[0].getLength()

    def getMaxCoveredLineNumbersCount(self):
        return min([s.getCoveredLineNumbersCount() for s in self])
