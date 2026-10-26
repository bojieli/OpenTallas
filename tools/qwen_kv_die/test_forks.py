"""Exercise the actual relay allocator at the three PVJOIN data-fork widths."""
import copy
import unittest
import kv_die as K


def fixture():
    return dict(
        insts=[K.F.Inst(n, 'fixture', x, y, 86.4, 86.4) for n, x, y in
               [('d2d_kv', 216, 1080), ('host', 1080, 1080), ('kvnc', 1944, 1080),
                ('seq', 216, 216), ('lprg', 1080, 216)]],
        die={'w': 2592, 'h': 1944}, geo={},
        buses=[('hsvc', 'spine_local', 174, [('d2d_kv', 'svc'), ('host', 'svc')]),
               ('kvnc_cht', 'kv_oneway', 59, [('host', 'cohort_tag'), ('kvnc', 'cht')]),
               ('kvnc_chg', 'kv_oneway', 2, [('host', 'cohort_gen'), ('kvnc', 'chg')]),
               ('clk_core_c', 'clock_trunk', 1,
                [('host', 'cksrc'), ('d2d_kv', 'ck'), ('kvnc', 'ck'), ('seq', 'ck'), ('lprg', 'ck')])],
        forks={'hsvc': [('seq', 'svc')], 'kvnc_cht': [('lprg', 'cht')], 'kvnc_chg': [('lprg', 'chg')]})


class Forks(unittest.TestCase):
    def check_paths(self, near=False):
        m = fixture()
        if near:
            q = next(i for i in m['insts'] if i.name == 'lprg')
            q.x, q.y = 1296, 1296
        original = copy.deepcopy(m['buses'])
        K._relays(m)
        bynet = {n: (c, w, e) for n, c, w, e in m['buses']}
        relays = {i.name for i in m['insts'] if i.name.startswith('rly_')}
        for bid, _, bits, ends in original[:3]:
            first = bynet[bid]
            self.assertEqual(first[1], bits)
            self.assertEqual(first[2][0], ends[0])
            for branch, target in [(bid, ends[1]), (bid + '__f0', m['forks'][bid][0])]:
                n = m['relay_stages'][branch]
                actual = {q for q in relays if q.startswith('rly_' + branch + '_')
                          and q[len('rly_' + branch + '_'):].isdigit()}
                self.assertEqual(actual, {f'rly_{branch}_{j}' for j in range(n)})
                self.assertNotIn(branch + '__f0', bynet)
                for j in range(n):
                    src = ends[0] if j == 0 else (f'rly_{branch}_{j-1}', 'b')
                    dst = (f'rly_{branch}_{j}', 'a')
                    self.assertEqual(sum(w == bits and ep[0] == src and dst in ep[1:]
                                         for _, w, ep in bynet.values()), 1)
                src = (f'rly_{branch}_{n-1}', 'b') if n else ends[0]
                self.assertEqual(sum(w == bits and ep[0] == src and target in ep[1:]
                                     for _, w, ep in bynet.values()), 1)
            self.assertEqual(m['fork_stages'][bid + '__f0'], m['relay_stages'][bid + '__f0'])
        clock = bynet['clk_core_c']
        self.assertEqual(clock[:2], ('clock_trunk', 1))
        self.assertEqual(clock[2][:5], original[3][3])
        self.assertEqual(set(clock[2][5:]), {(q, 'ck') for q in relays})
        self.assertEqual(len(clock[2][5:]), len(relays))
        return m

    def test_three_real_widths_and_independent_stage_counts(self):
        m = self.check_paths()
        self.assertTrue(all(m['relay_stages'][b] > 0 for b in m['fork_stages']))

    def test_zero_relay_branch_still_joins_same_driver(self):
        m = self.check_paths(near=True)
        self.assertEqual(m['fork_stages']['kvnc_cht__f0'], 0)

    def test_literal_driver_clock_root_is_preserved(self):
        m = fixture()
        m['buses'][3] = ('clk_core_c', 'clock_trunk', 1,
                         [('host', 'cksrc'), ('kvnc', 'ck'), ('seq', 'ck'), ('lprg', 'ck')])
        m['buses'].append(('clk_core_w', 'clock_trunk', 1,
                           [('host', 'other_cksrc'), ('d2d_kv', 'ck')]))
        K._relays(m)
        clocks = {n: ep for n, cl, _, ep in m['buses'] if cl == 'clock_trunk'}
        self.assertEqual(clocks['clk_core_c'][0], ('host', 'cksrc'))
        self.assertEqual(clocks['clk_core_w'][0], ('host', 'other_cksrc'))
        for inst in m['insts']:
            if inst.name.startswith('rly_'):
                expected = 'clk_core_w' if inst.name.startswith('rly_hsvc_') else 'clk_core_c'
                self.assertIn((inst.name, 'ck'), clocks[expected])
                self.assertNotIn((inst.name, 'ck'), clocks['clk_core_c' if expected == 'clk_core_w' else 'clk_core_w'])

    def test_clock_fork_refused(self):
        m = fixture(); m['forks'] = {'clk_core_c': [('seq', 'bad_clock_alias')]}
        with self.assertRaisesRegex(ValueError, 'point-to-point data'):
            K._relays(m)

    def test_duplicate_or_driver_alias_refused(self):
        for load in [('d2d_kv', 'svc'), ('host', 'svc')]:
            m = fixture(); m['forks'] = {'hsvc': [load]}
            with self.assertRaisesRegex(ValueError, 'alias'):
                K._relays(m)

    def test_duplicate_load_refused(self):
        m = fixture(); m['forks']['hsvc'] *= 2
        with self.assertRaisesRegex(ValueError, 'duplicate load'):
            K._relays(m)

    def test_branch_name_collision_refused(self):
        m = fixture(); m['buses'].append(('hsvc__f0', 'kv_oneway', 3, [('host', 'a'), ('seq', 'b')]))
        with self.assertRaisesRegex(ValueError, 'name collision'):
            K._relays(m)

    def test_missing_trunk_refused(self):
        m = fixture(); m['forks'] = {'missing': [('seq', 'svc')]}
        with self.assertRaisesRegex(ValueError, 'exactly one trunk'):
            K._relays(m)


if __name__ == '__main__':
    unittest.main()
