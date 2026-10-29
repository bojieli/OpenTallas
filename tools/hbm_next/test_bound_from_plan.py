#!/usr/bin/env python3
"""TOK-HBM-4: bound_from_plan.py composes down/up legs from plan station registers and fails closed on absent legs."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bound_from_plan as B

def st(conn, n): return dict(conn=conn, regs_um=[[0, 0]] * n)
def hub():   # n4 -> {n3a (leaf), n3b (leaf)}: a = 3 down / 2 up, b = 1 / 1
    return dict(internal_stations=[st('mu_tree:u_mu_fused_n4.da|a', 3), st('mu_tree:a.uo|u_mu_fused_n4', 2),
                                   st('mu_tree:u_mu_fused_n4.db|b', 1), st('mu_tree:b.uo|u_mu_fused_n4', 1),
                                   st('bus:n4x_dn_i', 11), st('bus:n4x_up_o', 9)])
def plan(extra=None):
    root = [st(f'bus:n4x_{d}_{r}_{io}', 2) for r in ('nw', 'ne') for d, io in (('dn', 'o'), ('up', 'i'))]
    p = dict(partition_types=dict(root=dict(internal_stations=root), q_hub_nw=hub(), q_hub_ne=hub()),
             latency=dict(lanes={f'N4{x}_{r}': dict(cycles=2) for x in 'UD' for r in ('NW', 'NE')}), reset={})
    if extra: p['latency']['fused_legs'] = extra
    return p

class T(unittest.TestCase):
    def test_tree_legs(self):
        legs, miss = B.build(plan(), '', {})
        self.assertEqual((legs['down_NW']['cycles'], legs['up_NW']['cycles']), (2 + 2 + 11 + 3, 2 + 2 + 9 + 2))
        self.assertEqual(len(miss), 8)                       # resets + provider legs absent -> calendar fails closed
    def test_plan_legs_complete(self):
        ex = {k: dict(cycles=4, source='plan') for k in B.OTHER}
        self.assertEqual(B.build(plan(ex), '', {})[1], [])
    def test_leg_without_source(self):
        ex = {k: dict(cycles=4, source='plan') for k in B.OTHER}; ex['reset_SW'] = dict(cycles=4)
        self.assertEqual(len(B.build(plan(ex), '', {})[1]), 1)
    def test_missing_lane(self):
        p = plan(); del p['latency']['lanes']['N4D_NE']
        legs, miss = B.build(p, '', {}); self.assertNotIn('down_NE', legs); self.assertTrue(any('down_NE' in m for m in miss))

class TSide(unittest.TestCase):
    def side(self, sha='x' * 64):
        rl = {f'reset_{r}': dict(release_cycle=50, release_basis='wavefront') for r in ('SW', 'SE', 'NW', 'NE')}
        rl['reset_root'] = dict(release_cycle=17)
        return dict(plan_sha256=sha, reset_legs=rl, provider_legs=dict(host_to_provider=dict(length_um=6929.3),
                    provider_to_root=dict(cycles=0), root_to_provider=dict(cycles=0)))
    def test_side_fills_legs_host_stays_missing(self):
        legs, miss = B.build(plan(), '', {}, B.side_legs(self.side(), 's.json', 'x' * 64))
        self.assertEqual((legs['reset_SW']['cycles'], legs['reset_root']['cycles'], legs['provider_to_root']['cycles']), (50, 17, 0))
        self.assertEqual([m.split(':')[0] for m in miss], ['host_to_provider'])
    def test_side_plan_mismatch_fails_closed(self):
        with self.assertRaises(SystemExit): B.side_legs(self.side('y' * 64), 's.json', 'x' * 64)
    def test_plan_table_wins(self):
        ex = {k: dict(cycles=4, source='plan') for k in B.OTHER}
        legs, miss = B.build(plan(ex), '', {}, B.side_legs(self.side(), 's.json', 'x' * 64))
        self.assertEqual((legs['reset_SW']['cycles'], miss), (4, []))
    def test_bool_not_int(self):
        s = self.side(); s['reset_legs']['reset_SW']['release_cycle'] = True
        self.assertNotIn('reset_SW', B.side_legs(s, 's.json', 'x' * 64))

if __name__ == '__main__':
    unittest.main()
