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

"""suffix_tree module"""

"""from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import *
from builtins import object"""


class SuffixTree(object):
    """Data structure that holds suffixes of iterables

    Exemple:
    t = SuffixTree()
    t.add('banana')

    | (r (a (na (na)),
    |     banana,
    |     na (na)))

    t.add('ananas')

    | (r (a (s,
    |        na (s,
    |            na (s))),
    |     banana,
    |     na (s,
    |         na (s)),
    |     s))

    :param _node: Root node of the suffix tree
    :type _node: SuffixTreeNode
    :param _f_code: Function acting as key to add elements in SuffixTree, defaults to identity
    :type _f_code: Function[E, K], optional
    """

    class StringPosition(object):
        """Holds a position in a string

        :todo what is it morally used for

        :param string: Original string of the suffix
        :type string: Iterable[E]
        :param position: Beginning position of the suffix in the original string
        :type position: int
        :param prevelem: Is this the first element of the string
        :type prevelem: Union[K, None]
        """
        def __init__(self, string, position, prevelem):
            self.string = string
            self.position = position
            self.prevelem = prevelem

    class SuffixTreeNode(object):
        """A node of a suffix tree

        :param childs: Child nodes
        :type childs: Dict[K -> E]
        :param string_positions: Information about the strings that uses this node
        :type string_positions: List[StringPosition]
        :param ending_strings: Information about the strings that end in this node
        :type ending_strings: List[StringPosition]
        """
        def __init__(self):
            self.childs = {}
            self.string_positions = []
            self.ending_strings = []

    def __init__(self, f_code=None):
        self._node = self.SuffixTreeNode()
        if f_code is None:
            f_code = lambda x: x
        self._f_code = f_code  # Function[E -> K]

    def _add(self, string, prevelem):
        """Add a suffix to the tree

        [description]

        :param string: Suffix to add to tree
        :type string: Iterable[E]
        :param prevelem: Key of previous element
        :type prevelem: K
        """
        pos = 0
        node = self._node
        for pos, elt in enumerate(string):
            # Save string in node
            node.string_positions.append(
                self.StringPosition(string, pos, prevelem))

            # Walk the tree adding nodes
            code = self._f_code(elt)
            if code not in node.childs:
                node.childs[code] = self.SuffixTreeNode()
            node = node.childs[code]
        # Save string in the last node
        node.ending_strings.append(
            self.StringPosition(string, pos + 1, prevelem))

    def add(self, string):
        """Add all suffixes of string in the tree

        [description]

        :param string: String to add
        :type string: Iterable[E]
        """
        # For every suffix add the suffix
        for i in range(len(string)):
            if i == 0:
                prevelem = None
            else:
                prevelem = self._f_code(string[i - 1])
            self._add(string[i:], prevelem)

    def getBestMaxSubstrings(self, threshold, f=None, f_elem=None, node=None, initial_threshold=None):
        """[summary]

        [description]

        :param threshold: Used to know when to start adding candidate
        :type threshold: int
        :param f: Used to lower the threshold when visiting a children, defaults to None
        :type f: Function[K -> int], optional
        :param f_elem: Used to validate candidate according to initial_threshold, defaults to None
        :type f_elem: Function[List[E] -> int], optional
        :param node: Node to use as root, defaults to None
        :type node: SuffixTreeNode, optional
        :param initial_threshold: Leave empty, keep original threshold in recursive calls, defaults to None
        :type initial_threshold: [type], optional
        :returns: List of candidate clones
        :rtype: {List[Tuple[List[E], List[E]]]}
        """
        if f is None:
            f = lambda x: x
        if f_elem is None:
            f_elem = lambda x: x
        if node is None:
            node = self._node
        if initial_threshold is None:
            initial_threshold = threshold

        def check_left_diverse_and_add(s1, s2, p):
            # global variables are: f_elem, initial_threshold, r
            # If s1 or s2 are the whole string, s1 and s2 do not have the same parent
            # TODO: what is p ??
            if ((s1.prevelem is None) or (s2.prevelem is None) or (s1.prevelem != s2.prevelem)) and s1.position > p:
                candidate = (s1.string[:s1.position - p],
                             s2.string[:s2.position - p])
                # If either statement covers enough lines to meet arguments.size_threshold
                if f_elem(candidate[0]) >= initial_threshold or \
                        f_elem(candidate[1]) >= initial_threshold:
                    r.append(candidate)
                return True
            else:
                return False

        r = []
        if threshold <= 0:
            # TODO: use itertools.product(node.ending_strings, node.string_positions)
            for s1 in node.ending_strings:
                for s2 in node.string_positions:
                    if s1.string == s2.string:
                        # Because node.ending_strings is a subset of node.string_positions
                        continue
                    check_left_diverse_and_add(s1, s2, 0)

            # TODO: use itertools.combinations(node.ending_strings, 2)
            for i in range(len(node.ending_strings)):
                for j in range(i):
                    s1 = node.ending_strings[i]
                    s2 = node.ending_strings[j]
                    check_left_diverse_and_add(s1, s2, 0)

            # TODO: why not combinations(node.string_positions) ???

            # TODO: use itertools.combinations(node.childs, 2)
            for i in range(len(list(node.childs.keys()))):
                for j in range(i):
                    # TODO: This is dangerous the order of dict.keys is not ensured
                    c1 = list(node.childs.keys())[i]
                    c2 = list(node.childs.keys())[j]
                    # TODO: use itertools.product
                    for s1 in node.childs[c1].string_positions + node.childs[c1].ending_strings:
                        for s2 in node.childs[c2].string_positions + node.childs[c2].ending_strings:
                            check_left_diverse_and_add(s1, s2, 1)

        for (code, child) in list(node.childs.items()):
            r += self.getBestMaxSubstrings(
                threshold - f(code), f, f_elem, child, initial_threshold)
        return r


if __name__ == '__main__':
    class Elem(object):
        def __init__(self, code):
            self._code = code

        def getCode(self):
            return self._code

        def __str__(self):
            return str(self._code)

    def test1():
        t = SuffixTree()
        for w in ['abcPeter', 'Pet1erbca', 'Peter', 'aPet0--']:
            t.add([Elem(c) for c in w])
        maxs = t.getBestMaxSubstrings(3)
        l = []
        for (s1, s2) in maxs:
            l.append([''.join([str(e) for e in s1]),
                      ''.join([str(e) for e in s2])])
        assert l == [['Pe1t', 'P2et'], ['P3et', 'Pe4t'], ['Pet', 'Pet'],
                     ['Pet', 'Pet'], ['Pet', 'Pet'], ['Peter', 'Peter']]

    def test2():
        t = SuffixTree()
        for w in ['a', 'aa']:
            t.add([Elem(c) for c in w])
        maxs = t.getBestMaxSubstrings(0)
        l = []
        for (s1, s2) in maxs:
            l.append([''.join([str(e) for e in s1]),
                      ''.join([str(e) for e in s2])])
        assert l == [['a', 'a'], ['a', 'a'], ['a', 'a']]

    for s in dir():
        if s.find('test') == 0:
            eval(s + '()')
