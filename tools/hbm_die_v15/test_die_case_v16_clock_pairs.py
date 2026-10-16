import unittest
from collections import defaultdict

from die_case_v16 import communicating_pairs


class CommunicatingPairs(unittest.TestCase):
    def test_all_105_multicast_branches_survive_clique_limit(self):
        sinks = [(f'tile{i:03}', 'i') for i in range(105)]
        nets = {('host', 'launch_v'): [('host', 'launch_v'), *sinks]}
        domains = defaultdict(set, {n: {'stream'} for n, _ in nets[('host', 'launch_v')]})
        pairs = communicating_pairs(nets, domains, 8)['stream']
        self.assertEqual(len(pairs), 105)
        self.assertIn(('host', 'tile104'), pairs)

    def test_small_clique_and_unrelated_domains(self):
        nets = {('a', 'o'): [('a', 'o'), ('b', 'i'), ('c', 'i'), ('d', 'i')]}
        domains = defaultdict(set, a={'stream'}, b={'stream'}, c={'stream'}, d={'hbm'})
        self.assertEqual(communicating_pairs(nets, domains)['stream'], [('a', 'b'), ('a', 'c'), ('b', 'c')])


if __name__ == '__main__':
    unittest.main()
