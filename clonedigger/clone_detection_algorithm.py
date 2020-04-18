from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import range
from builtins import *
from past.utils import old_div
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

import sys
import logging
import copy

from . import arguments
from . import suffix_tree
from .anti_unification import Cluster, Unifier
from .abstract_syntax_tree import StatementSequence, PairSequences

MAX_SEQUENCE_LENGTH = 1000


def findDuplicateCode(source_files, report):
    statement_sequences = []
    statement_count = 0
    sequences_lengths = []
    for source_file in source_files:
        sequences = source_file.getTree().getAllStatementSequences()
        statement_sequences.extend(sequences)
        sequences_lengths.extend([len(s) for s in sequences])
        statement_count += sum([len(s) for s in sequences])

    if not sequences_lengths:
        logging.warning('Input is empty or the size of the input is below the size threshold')
        return []

    n_sequences = len(sequences_lengths)
    avg_seq_length = old_div(sum(sequences_lengths), float(n_sequences))
    max_seq_length = max(sequences_lengths)

    logging.info('{} sequences'.format(n_sequences))
    logging.info('average sequence length: {}'.format(avg_seq_length))
    logging.info('maximum sequence length: {}'.format(max_seq_length))

    sequences_without_restriction = statement_sequences
    sequences = []
    if not arguments.force:
        for sequence in sequences_without_restriction:
            if len(sequence) > MAX_SEQUENCE_LENGTH:
                first_statement = sequence[0]
                logging.info('-----------------------------------------')
                logging.info(
                    'Warning: sequences of statements starting at {}:{}, consists of {} '
                    'elements which is too long.'.format(
                        first_statement.getSourceFile().getFileName(),
                        min(first_statement.getCoveredLineNumbers()),
                        len(sequence)))
                logging.info('It will be ignored. Use --force to override this restriction.')
                logging.info('Please refer to http://clonedigger.sourceforge.net/documentation.html')
                logging.info('-----------------------------------------')
            else:
                sequences.append(sequence)

    def calc_statement_sizes():
        for sequence in statement_sequences:
            for statement in sequence:
                statement.storeSize()

    def build_hash_to_statement(dcup_hash=True):
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
        processed_statements_count = 0
        clusters = []
        ret = {}
        for h in list(hash_to_statement.keys()):
            local_clusters = []
            statements = hash_to_statement[h]
            for statement in statements:
                processed_statements_count += 1
                if (processed_statements_count % 1000) == 0:
                    logging.info('{},'.format(processed_statements_count))
                bestcluster = None
                mincost = sys.maxsize
                for cluster in local_clusters:
                    cost = cluster.getAddCost(statement)
                    if cost < mincost:
                        mincost = cost
                        bestcluster = cluster
                assert(local_clusters == [] or bestcluster)
                if mincost < 0:
                    pdb.set_trace()
                assert mincost >= 0
                if bestcluster is None or mincost > arguments.clustering_threshold:
                    newcluster = Cluster(statement)
                    local_clusters.append(newcluster)
                else:
                    bestcluster.unify(statement)
            ret[h] = local_clusters
            clusters.extend(local_clusters)
        return ret

    def clusterize(hash_to_statement, clusters_map):
        processed_statements_count = 0
        # clusters_map contain hash values for statements, not unifiers
        # therefore it will work correct even if unifiers are smaller than hashing depth value
        for h in list(hash_to_statement.keys()):
            clusters = clusters_map[h]
            for statement in hash_to_statement[h]:
                processed_statements_count += 1
                if (processed_statements_count % 1000) == 0:
                    logging.info('{},'.format(processed_statements_count))
                mincost = sys.maxsize
                for cluster in clusters:
                    new_u = Unifier(cluster.getUnifierTree(), statement)
#                   assert(new_u.getSubstitutions()[0].getSize() == 0)
                    cost = new_u.getSize()
                    if cost < mincost:
                        mincost = cost
                        statement.setMark(cluster)
                        cluster.addWithoutUnification(statement)

    def filterOutLongEquallyLabeledSequences(statement_sequences):
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
                            first_statement = sequence[first_statement_index]
                            logging.info('-----------------------------------------')
                            logging.info('Warning: sequence of statements starting at {}:{} consists of many '
                                'similar statements.'.format(
                                    first_statement.getSourceFile().getFileName(),
                                    min(first_statement.getCoveredLineNumbers())))
                            logging.info('It will be ignored. Use --force to override this restriction.')
                            logging.info('Please refer to http://clonedigger.sourceforge.net/documentation.html')
                            logging.info('-----------------------------------------')
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

    def mark_using_hash(hash_to_statement):
        for h in hash_to_statement:
            cluster = Cluster()
            for statement in hash_to_statement[h]:
                cluster.addWithoutUnification(statement)
                statement.setMark(cluster)

    def findHugeSequences():
        def f_size(x):
            return x.getMaxCoveredLines()

        def f_elem(x):
            return StatementSequence(x).getCoveredLineNumbersCount()

        def fcode(x):
            return x.getMark()
        f = f_size
        suffix_tree_instance = suffix_tree.SuffixTree(fcode)
        for sequence in statement_sequences:
            suffix_tree_instance.add(sequence)
        return [PairSequences([StatementSequence(s1), StatementSequence(s2)]) for (s1, s2) in suffix_tree_instance.getBestMaxSubstrings(arguments.size_threshold, f, f_elem)]

    def refineDuplicates(pairs_sequences):
        r = []
        flag = False
        while pairs_sequences:
            pair_sequences = pairs_sequences.pop()

            def all_pairsubsequences_size_n_threshold(n):
                lr = []
                for first in range(0, pair_sequences.getLength() - n + 1):
                    new_pair_sequences = pair_sequences.subSequence(first, n)
                    size = new_pair_sequences.getMaxCoveredLineNumbersCount()
                    if size >= arguments.size_threshold:
                        lr.append((new_pair_sequences, first))
                return lr
            n = pair_sequences.getLength() + 1
            while 1:
                n -= 1
                if n == 0:
                    break
                new_pairs_sequences = all_pairsubsequences_size_n_threshold(n)
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

    logging.info('Number of statements: {}'.format(statement_count))
    logging.info('Calculating size for each statement...')
    calc_statement_sizes()
    logging.info('Calculating size for each statement... Done')

    logging.info('Building statement hash...')
    report.startTimer('Building statement hash')
    if arguments.clusterize_using_hash:
        hash_to_statement = build_hash_to_statement(dcup_hash=False)
    else:
        hash_to_statement = build_hash_to_statement(dcup_hash=True)
    report.stopTimer()
    logging.info('Building statement hash... Done')
    logging.info('Number of different hash values: {}'.format(len(hash_to_statement)))

    if arguments.clusterize_using_dcup or arguments.clusterize_using_hash:
        logging.info('Marking each statement with its hash value')
        mark_using_hash(hash_to_statement)
    else:
        logging.info('Building patterns...')
        report.startTimer('Building patterns')
        clusters_map = build_unifiers(hash_to_statement)
        report.stopTimer()
        logging.info('{} patterns were discovered'.format(Cluster.count))
        logging.info('Choosing pattern for each statement...')
        report.startTimer('Marking similar statements')
        clusterize(hash_to_statement, clusters_map)
        report.stopTimer()
        logging.info('Choosing pattern for each statement... Done')

    if arguments.report_unifiers:
        logging.info('Building reverse hash for reporting ...')
        reverse_hash = {}
        for sequence in statement_sequences:
            for statement in sequence:
                mark = statement.getMark()
                if mark not in reverse_hash:
                    reverse_hash[mark] = []
                reverse_hash[mark].append(statement)
        report.setMarkToStatementHash(reverse_hash)
        logging.info('Building reverse hash for reporting ... Done')

    logging.info('Finding similar sequences of statements...')

    if not arguments.force:
        statement_sequences = filterOutLongEquallyLabeledSequences(
            statement_sequences)

    report.startTimer('Finding similar sequences of statements')
    duplicate_candidates = findHugeSequences()
    report.stopTimer()
    logging.info('{} sequences were found'.format(len(duplicate_candidates)))
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

    # get covered source lines for all detected clones (set of all)
    covered_source_lines = set()
    for clone in clones:
        for sequence in clone:
            covered_source_lines |= sequence.getLineNumberHashables()

    # get source lines for all files/sequences (set of all)
    source_lines = set()
    for sequence in statement_sequences:
        source_lines |= sequence.getLineNumberHashables()

    report.all_source_lines_count = len(source_lines)
    report.covered_source_lines_count = len(covered_source_lines)

    return clones
