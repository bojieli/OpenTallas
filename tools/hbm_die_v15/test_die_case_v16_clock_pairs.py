import unittest
from collections import defaultdict

from die_case_v16 import communicating_pairs, clock_entries


class CommunicatingPairs(unittest.TestCase):
    def test_multiple_literal_entries_keep_geometry_and_all_pairs(self):
        pl = dict(a=dict(x=10, y=20, w=100, h=80, o='R0'),
                  b=dict(x=200, y=20, w=100, h=80, o='MX'))
        pins = dict(c={'clk_n': (10, 80), 'clk_s': (90, 0)})
        sinks, aliases, pairs = clock_entries({'a': ['clk_n', 'clk_s'], 'b': ['clk_s']},
                                               pl, {'a': 'c', 'b': 'c'}, pins, [('a', 'b')])
        self.assertEqual(sinks, [('a', 'clk_n', 20, 100), ('a__ckp001', 'clk_s', 100, 20),
                                 ('b', 'clk_s', 290, 100)])
        self.assertEqual(aliases['a__ckp001'], ('a', 'clk_s'))
        self.assertEqual(set(pairs), {('a', 'a__ckp001'), ('a', 'b'), ('a__ckp001', 'b')})

    def test_missing_physical_clock_pin_is_rejected(self):
        with self.assertRaises(KeyError):
            clock_entries({'a': ['clk']}, {'a': dict(x=0, y=0, w=10, h=10, o='R0')},
                          {'a': 'c'}, {'c': {}}, [])

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
