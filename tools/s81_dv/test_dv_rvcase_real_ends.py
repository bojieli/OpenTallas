"""STW-S81d-H11STA 10-23: gen_safety measures hop 0 / the last hop from the REAL bound-view pins, not the plan face seeds
(H11f3: 93/93 u_ctl lane ends 0.5-5.6 mm from their seeds, gen_safety PASS max_hop 384 um, die STA -8.5 ns / -10.4 ns);
and clock_sdc creates every clock before a clock group names it (STA-0351 'ck_head_lep_A not found')."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_rvcase as RV  # noqa: E402
from test_dv_rvcase_hop0 import LEF  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from die_safety import gen_check as DSG  # noqa: E402


class RealEnds(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'views').mkdir()
        (self.d / 'views' / 'blk.lef').write_text(LEF)
        # block at (1000, 1000): vo pins on the N face (x 1040 / 1060, y 1050); the plan seeded the lane on the W face
        self.insts = [('blk', 'u_a', None, {}), ('rly', 'st_ln_0', None, {})]
        self.ibits = {'u_a': {'vo': [('w_ln_src', 1), ('w_ln_src', 0)], 'vi': [('w_other_lnd', 0)]}}
        self.loc = {'u_a': (1000.0, 1000.0, 100.0, 50.0, 'FIRM')}
        self.links = {'ln': dict(src='a', dst='b', sxy=(1000.0, 1025.0), dxy=(5000.0, 1000.0), pts=[(900.0, 1025.0)], cls='unit')}

    def test_real_pin_centroid(self):
        e = RV.real_link_ends(self.d, self.insts, self.ibits, self.loc, {'u_a': 'closed'}, {}, self.links)
        x, y, n = e['ln']['src']
        self.assertEqual(n, 2)
        self.assertAlmostEqual(x, 1050.05, places=2)
        self.assertAlmostEqual(y, 1049.95, places=2)
        self.assertNotIn('dst', e['ln'])            # u_b has no view here: the seed stays

    def test_gate_sees_the_real_hop0(self):
        ends = RV.real_link_ends(self.d, self.insts, self.ibits, self.loc, {'u_a': 'closed'}, {}, self.links)
        pts_seed = [[1000.0, 1025.0], [900.0, 1025.0], [1300.0, 1025.0]]
        pts_real = [list(ends['ln']['src'][:2])] + pts_seed[1:]
        seed = DSG.check_facts(dict(wires=[dict(id='ln', pts=pts_seed)]), 120)
        real = DSG.check_facts(dict(wires=[dict(id='ln', pts=pts_real)]), 120)
        self.assertEqual(seed['counts']['hops_over'], 1)   # only the 400-um span
        self.assertEqual(real['counts']['hops_over'], 2)   # hop 0 from the N-face pins is 175 um > 120


class ClockGroups(unittest.TestCase):
    def test_groups_after_all_clocks(self):
        T = {'instance_clock_ports': True, 'clock_domains': {
            'ck_hbm': dict(period_ps=900.0, asynchronous_to_core=True),
            'ck_head_lep_A': dict(period_ps=833.333, relationship='same_pll_fixed_phase')}}
        lines = RV.clock_sdc(T, {'ck_a', 'ck_hbm', 'ck_head_lep_A'}).splitlines()
        g = [i for i, l in enumerate(lines) if l.startswith('set_clock_groups')]
        c = [i for i, l in enumerate(lines) if l.startswith('create_clock')]
        self.assertTrue(g and max(c) < min(g))
        self.assertIn('{clk ck_head_lep_A}', lines[g[0]])


if __name__ == '__main__':
    unittest.main()
