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

"""clone_detection_algorithm module"""

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
from past.utils import old_div"""

import sys
import logging
import copy

from . import arguments
from . import suffix_tree
from .anti_unification import Cluster, Unifier
from .abstract_syntax_tree import StatementSequence, PairSequences

MAX_SEQUENCE_LENGTH = 1000


def build_hash_to_statement(statement_sequences, dcup_hash=True):
    """Compute hash for every statement

    Two statement can have the same hash

    :param statement_sequences: Statements to compute hash
    :type statement_sequences: List[StatementSequence]
    :param dcup_hash: Use dcup hash, defaults to True
    :type dcup_hash: bool, optional
    :returns: A map Hash -> List[Statement]
    :rtype: {Dict[int -> List[Statement]]}
    """
    hash_to_statement = {}
    for statement_sequence in statement_sequences:
        for statement in statement_sequence:
            if dcup_hash:
                # 3 - CONSTANT HERE!
                h = statement.getDCupHash(arguments.hashing_depth)
            else:
                h = statement.getFullHash()
            if h not in hash_to_statement:
                hash_to_statement[h] = [statement]
            else:
                hash_to_statement[h].append(statement)
    return hash_to_statement


def build_unifiers(hash_to_statement):
    """Populate Cluster object with Statement.

    Greedily add the cheapest statement to Clusters by unifying, thus creating
    Unifiers for each cluster. This clusters on hash, but finer.

    :param hash_to_statement: Statements grouped by hash
    :type hash_to_statement: Dict[int, List[AbstractSyntaxTree]]
    :returns: A list of unified Cluster
    :rtype: {Dict[int, Cluster]}
    """
    processed_statements_count = 0
    clusters = []
    ret = {}
    for h in list(hash_to_statement.keys()):
        # For each hash cluster it's statements
        local_clusters = []
        statements = hash_to_statement[h]
        for statement in statements:
            processed_statements_count += 1
            if (processed_statements_count % 1000) == 0:
                logging.info('{},'.format(processed_statements_count))

            # Fig 1. in (Bulychev et al., 2008)
            # Compute the local cluster that has the lowest cost of adding the
            #  statement
            bestcluster = None
            mincost = sys.maxsize
            for cluster in local_clusters:
                cost = cluster.getAddCost(statement)
                if cost < mincost:
                    mincost = cost
                    bestcluster = cluster
            assert(local_clusters == [] or bestcluster)

            # The minimum cost should not be <0 (how would this be possible ??)
            # mincost is (len(cluster) * len(cluster.unifier.subs[0]) + len(cluster.unifier.subs[1]))
            if mincost < 0:
                pdb.set_trace()
            assert mincost >= 0

            # There was no pre-existing local cluster
            #  or the cost of adding the statement is too big
            #  Creating a new local cluster
            if bestcluster is None or mincost > arguments.clustering_threshold:
                newcluster = Cluster(statement)
                local_clusters.append(newcluster)
            else:
                bestcluster.unify(statement)
        ret[h] = local_clusters
        clusters.extend(local_clusters)
    return ret


def clusterize(hash_to_statement, clusters_map):
    """Add statements to Cluster's unifier

    Greedily add statements to cluster based on distance to Cluster's unifier

    :param hash_to_statement: Statements grouped by hash
    :type hash_to_statement: Dict[int, List[Statement]]
    :param clusters_map: Clusters grouped by hash
    :type clusters_map: Dict[int, List[Cluster]]
    """
    # Are the same Statements added to the same clusters than in build_unifiers ??
    # What does this function do more than just calling setMark on statements

    processed_statements_count = 0
    # clusters_map contain hash values for statements, not unifiers
    # therefore it will work correct even if unifiers are smaller than hashing depth value
    for h in hash_to_statement:
        # For each hash, get statements and local_clusters
        clusters = clusters_map[h]
        for statement in hash_to_statement[h]:
            processed_statements_count += 1
            if (processed_statements_count % 1000) == 0:
                logging.info('{},'.format(processed_statements_count))
            mincost = sys.maxsize
            for cluster in clusters:
                # For each local_cluster add statement if adding it is cheap
                # But the statement will always be added to the first local_cluster,
                #  and the last will likely be never

                # TODO: should this be cluster.getAddCost(statement)
                new_u = Unifier(cluster.getUnifierTree(), statement)
                # assert(new_u.getSubstitutions()[0].getSize() == 0)
                cost = new_u.getSize()
                if cost < mincost:
                    # statement.setMark can only hold one value
                    # The statement can be theoretically added to multiple
                    #  clusters (is this the case?)
                    # This will result in statement occuring in multiple cluster,
                    #  but statement will belong to only one (according to stmt._mark)
                    mincost = cost
                    statement.setMark(cluster)
                    cluster.addWithoutUnification(statement)
                    # It this the wanted behaviour ?
                    # Why not creating new Cluster objects ? The same statement
                    #  can be added once in build_unifiers and once again in here


def filterOutLongSequences(statement_sequences, max_length):

    def print_warn(seq):
        # This function is defined here to clear the body of the function
        stmt = seq[0]
        logging.info('-----------------------------------------')
        logging.info(
            'Warning: sequences of statements starting at {}:{}, consists of {} '
            'elements which is too long.'.format(
                stmt.getSourceFile().getFileName(),
                min(stmt.getCoveredLineNumbers()),
                len(seq)))
        logging.info('It will be ignored. Use --force to override this restriction.')
        logging.info('Please refer to http://clonedigger.sourceforge.net/documentation.html')
        logging.info('-----------------------------------------')

    sequences = []
    for sequence in statement_sequences:
        if len(sequence) > max_length:
            print_warn(sequence)
            continue
        sequences.append(sequence)
    return sequences


def filterOutLongEquallyLabeledSequences(statement_sequences):

    def print_warn(stmt):
        # This function is defined here to clear the body of the function
        logging.info('-----------------------------------------')
        logging.info(
            'Warning: sequence of statements starting at {}:{} consists of many '
            'similar statements.'.format(
                stmt.getSourceFile().getFileName(),
                min(stmt.getCoveredLineNumbers())))
        logging.info('It will be ignored. Use --force to override this restriction.')
        logging.info('Please refer to http://clonedigger.sourceforge.net/documentation.html')
        logging.info('-----------------------------------------')

    # TODO - refactor, combine with the previous warning
    sequences_without_restriction = statement_sequences
    statement_sequences = []
    for sequence in sequences_without_restriction:
        new_sequence = copy.copy(sequence._sequence)
        current_mark = None
        length = 0
        first_statement_index = None
        flag = False
        for i in range(len(sequence)):
            statement = sequence[i]
            if statement.getMark() != current_mark:
                if flag is True:
                    flag = False
                current_mark = statement.getMark()
                length = 0
                first_statement_index = i
            else:
                length += 1
                if length > 10:
                    new_sequence[i] = None
                    if not flag:
                        for i in range(first_statement_index, i):
                            new_sequence[i] = None
                        print_warn(sequence[first_statement_index])
                        flag = True
        new_sequence = new_sequence + [None]
        cur_sequence = StatementSequence()
        for statement in new_sequence:
            if statement is None:
                if cur_sequence:
                    statement_sequences.append(cur_sequence)
                    cur_sequence = StatementSequence()
            else:
                cur_sequence.addStatement(statement)
    return statement_sequences


# TODO: rename to findCandidateClones
# TODO: add threshold argument to explicitly say what this function does
def findHugeSequences(statement_sequences):
    """Return candidate clones which cover at least `arguments.size_threshold` lines

    Use a suffixTree to find candidate clones.

    :param statement_sequences: Candidate StatetementSequences
    :type statement_sequences: List[PairSequences]
    """
    # Function[Cluster -> int]
    f_size = lambda x: x.getMaxCoveredLines()
    # Function[List[AbstractSyntaxtree] -> int]
    f_elem = lambda x: StatementSequence(x).getCoveredLineNumbersCount()
    # Key to use in SuffixTree, Function[AbstractSyntaxTree -> Cluster]
    fcode = lambda x: x.getMark()

    suffix_tree_instance = suffix_tree.SuffixTree(fcode)
    for sequence in statement_sequences:
        suffix_tree_instance.add(sequence)

    tmp = suffix_tree_instance.getBestMaxSubstrings(arguments.size_threshold, f_size, f_elem)
    return [PairSequences([StatementSequence(s1), StatementSequence(s2)]) for (s1, s2) in tmp]


def all_pairsubsequences_size_n_threshold(n, pair_sequences):
    lr = []
    for first in range(0, pair_sequences.getLength() - n + 1):
        new_pair_sequences = pair_sequences.subSequence(first, n)
        size = new_pair_sequences.getMaxCoveredLineNumbersCount()
        if size >= arguments.size_threshold:
            lr.append((new_pair_sequences, first))
    return lr


def refineDuplicates(pairs_sequences):
    r = []
    flag = False
    while pairs_sequences:
        pair_sequences = pairs_sequences.pop()
        n = pair_sequences.getLength() + 1
        while 1:
            n -= 1
            if n == 0:
                break
            new_pairs_sequences = all_pairsubsequences_size_n_threshold(n, pair_sequences)
            for (candidate_sequence, first) in new_pairs_sequences:
                distance = candidate_sequence.calcDistance()
                if (distance < arguments.distance_threshold):
                    r.append(candidate_sequence)
                    if first > 0:
                        pairs_sequences.append(
                            pair_sequences.subSequence(0, first - 1))
                    if first + n < pair_sequences.getLength():
                        pairs_sequences.append(pair_sequences.subSequence(
                            first + n, pair_sequences.getLength() - first - n))
                    n += 1
                    flag = True
                    break
            if flag:
                flag = False
                break
    return r


def remove_dominated_clones(clones):
    """[summary]

    [description]

    :param clones: [description]
    :type clones: List[PairSequence]
    :returns: [description]
    :rtype: {List[PairSequence]}
    """
    ret_clones = []
    # def f_cmp(a, b):
    #     return a.getLevel().__cmp__(b.getLevel())
    # clones.sort(f_cmp)
    statement_to_clone = {}
    for clone in clones:
        for sequence in clone:
            for statement in sequence:
                if statement not in statement_to_clone:
                    statement_to_clone[statement] = []
                statement_to_clone[statement].append(clone)

    for clone in clones:
        ancestors_2 = clone[1].getAncestors()
        flag = True
        for s1 in clone[0].getAncestors():
            if s1 in statement_to_clone:
                for clone2 in statement_to_clone[s1]:
                    if s1 in clone2[0]:
                        seq = clone2[1]
                    else:
                        assert(s1 in clone2[1])
                        seq = clone2[0]
                    for s2 in seq:
                        if s2 in ancestors_2:
                            flag = False
                            break
                    if not flag:
                        break
            if not flag:
                break
        if flag:
            ret_clones.append(clone)
    return ret_clones


def print_statistics(sequences_lengths, statement_count):
    n_sequences = len(sequences_lengths)
    avg_seq_length = sum(sequences_lengths) / n_sequences
    max_seq_length = max(sequences_lengths)

    logging.info('{} sequences'.format(n_sequences))
    logging.info('average sequence length: {}'.format(avg_seq_length))
    logging.info('maximum sequence length: {}'.format(max_seq_length))
    logging.info('number of statements: {}'.format(statement_count))


def findDuplicateCode(source_files, report):
    statement_sequences = []
    statement_count = 0
    sequences_lengths = []

    # Retrieve statements from every files
    for source_file in source_files:
        sequences = source_file.getTree().getAllStatementSequences()
        statement_sequences.extend(sequences)
        sequences_lengths.extend([len(s) for s in sequences])
        # TODO: Compute afterwards, it is [[len(s) for s in stmt] for stmt in seqs]
        statement_count += sum([len(s) for s in sequences])
        # TODO: Compute afterwards, it is sum(flatten(sequence_lengths))

    if not sequences_lengths:
        logging.error('Input is empty or the size of the input is below the size threshold')
        return []

    print_statistics(sequences_lengths, statement_count)

    ##
    # Prepare statements
    #  Compute hash value for every statement
    ##

    if not arguments.force:
        statement_sequences = filterOutLongSequences(
            statement_sequences, MAX_SEQUENCE_LENGTH)

    # TODO: In order to call `storeSize` and compute hash, the trees must be
    #  completed. Could this be done earlier ? (Right after parsing files)

    logging.info('Calculating size for each statement...')
    for sequence in statement_sequences:
        for statement in sequence:
            statement.storeSize()

    # First step of clustering:
    #  Use hash to cluster Statements
    logging.info('Building statement hash...')
    report.startTimer('Building statement hash')
    hash_to_statement = build_hash_to_statement(
        statement_sequences,
        dcup_hash=arguments.clusterize_using_hash)
    report.stopTimer()

    logging.info('Number of different hash values: {}'.format(len(hash_to_statement)))

    ##
    # Group statements in clusters of similar statements
    #  Based on hash, group statements (by setting the `.mark` attribute)
    ##

    # Second step of clustering:
    #  Find patterns which are recurring sequences of Clusters

    if arguments.clusterize_using_dcup or arguments.clusterize_using_hash:
        # As statements can have the same hash, use the hash to make clusters
        logging.info('Marking each statement with its hash value')
        # mark_using_hash
        # For each hash make a Cluster
        # Populate Cluster objects and setMark
        for h in hash_to_statement:
            cluster = Cluster()
            for statement in hash_to_statement[h]:
                cluster.addWithoutUnification(statement)
                statement.setMark(cluster)
    else:
        logging.info('Building patterns...')
        report.startTimer('Building patterns')
        clusters_map = build_unifiers(hash_to_statement)
        # Populate Cluster objects
        report.stopTimer()
        logging.info('{} patterns were discovered'.format(Cluster.count))

        logging.info('Choosing pattern for each statement...')
        report.startTimer('Marking similar statements')
        clusterize(hash_to_statement, clusters_map)
        report.stopTimer()

    if arguments.report_unifiers:
        # TODO: Why do we need to do this, when the Cluster object exist?
        #  Is there no dict holding Statement -> Cluster ?
        # We have hash_to_statement : Dict[int -> List[Statement]]

        # Compute a Dict[Cluster -> List[Statement]]
        logging.info('Building reverse hash for reporting...')
        reverse_hash = {}
        for sequence in statement_sequences:
            for statement in sequence:
                mark = statement.getMark()
                if mark not in reverse_hash:
                    reverse_hash[mark] = []
                reverse_hash[mark].append(statement)
        report.setMarkToStatementHash(reverse_hash)

    ##
    # Gathering clone candidates
    ##

    logging.info('Finding similar sequences of statements...')

    if not arguments.force:
        statement_sequences = filterOutLongEquallyLabeledSequences(
            statement_sequences)

    report.startTimer('Finding similar sequences of statements')
    # Get clone candidates
    duplicate_candidates = findHugeSequences(statement_sequences)
    report.stopTimer()
    logging.info('{} sequences were found'.format(len(duplicate_candidates)))

    ##
    # Filtering clone candidates
    ##

    logging.info('Refining candidates...')
    if arguments.distance_threshold != -1:
        report.startTimer('Refining candidates')
        clones = refineDuplicates(duplicate_candidates)
        report.stopTimer()
    else:
        clones = duplicate_candidates
    logging.info('{} clones were found'.format(len(clones)))

    if arguments.distance_threshold != -1:
        logging.info('Removing dominated clones...')
        old_clone_count = len(clones)
        clones = remove_dominated_clones(clones)
        logging.info('{} clones were removed'.format(len(clones) - old_clone_count))

    ##
    # Filling report
    ##

    # Count covered lines by all clones
    # todo: in a sequence do all trees and subtrees belong to the same _source_file ?
    #    if no then the StatementSequence.source_file is 
    # get covered source lines for all detected clones (set of all)
    covered_source_lines = set()
    for clone in clones:
        # clone is a pair sequence thus it has 2 elements
        for sequence in clone:
            covered_source_lines |= sequence.getLineNumberHashables()

    # get source lines for all files/sequences (set of all)
    source_lines = set()
    for sequence in statement_sequences:
        source_lines |= sequence.getLineNumberHashables()

    report.all_source_lines_count = len(source_lines)
    report.covered_source_lines_count = len(covered_source_lines)

    return clones
