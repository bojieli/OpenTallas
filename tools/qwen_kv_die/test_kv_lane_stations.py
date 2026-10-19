"""HKV-STATIONS: real relay-station insertion for overreaching forwarded-lane hops (kv_lane_stations.py)."""

import unittest

import kv_lane_stations as KS
from kv_fwd_lanes import expr_bits


def relay(name, W=12960, H=12960, pins=(('a', 0), ('b', 12900))):
    out = dict(name=name, W=W, H=H, pins=[])
    for pn, y in pins:     # M3 pins on the kvs14p lane lattice (test_kv_lane_orientation.macro)
        out['pins'].append(dict(name=pn, use='SIGNAL', rects=[('M3', (8100, y, 8118, y + 37))]))
    out['pd'] = {p['name']: p for p in out['pins']}
    return out


NET = """module die;
  wire [0:0] n_x;
  wire [0:0] n_y;
  qkd_rlys_1 rly_q_0__s0 (.ck(n_clk_core_c), .a(n_x[0]), .b(n_y[0]));
  blk u_ld (.i({1'b0, n_y[0]}));
endmodule""".split('\n')


class StationTest(unittest.TestCase):
    def test_pack_roundtrip_with_constants(self):
        bits = ['n_a[0]', 'n_a[1]', '0', '0', '1', 'n_b[3]']
        e = KS.pack(bits)
        self.assertEqual(e, "{n_b[3], 1'b1, 2'b00, n_a[1:0]}")
        self.assertEqual(expr_bits(e, {}), bits)

    def test_before_inserts_relay_and_rewires_load_station(self):
        lines, place = KS.apply_edits(NET, 'set _blk x\n', [dict(op='before', at='rly_q_0__s0', inst='rly_q_0__s0_x1',
                                                                  ck='n_clk_core_c', S=1, xy=(5400, 2700))], expr_bits)
        txt = '\n'.join(lines)
        self.assertIn('qkd_rlys_1 rly_q_0__s0_x1 (.ck(n_clk_core_c), .a(n_x[0]), .b(n_rly_q_0__s0_x1__o[0:0]));', txt)
        self.assertIn('rly_q_0__s0 (.ck(n_clk_core_c), .a(n_rly_q_0__s0_x1__o[0:0]), .b(n_y[0]));', txt)
        self.assertIn('wire [0:0] n_rly_q_0__s0_x1__o;', txt)
        self.assertLess(txt.index('wire [0:0] n_rly_q_0__s0_x1__o;'), txt.index('qkd_rlys_1 rly_q_0__s0_x1'))
        self.assertIn('findInst rly_q_0__s0_x1] 5.400 2.700 R0', place)

    def test_after_rewires_only_the_cluster_loads(self):
        lines, _ = KS.apply_edits(NET, '', [dict(op='after', at='rly_q_0__s0', inst='rly_q_0__s0_y1',
                                                 ck='n_clk_core_WS', S=1, xy=(0, 0), loads=['u_ld'])], expr_bits)
        txt = '\n'.join(lines)
        self.assertIn('qkd_rlys_1 rly_q_0__s0_y1 (.ck(n_clk_core_WS), .a(n_y[0]), .b(n_rly_q_0__s0_y1__o[0:0]));', txt)
        self.assertIn("blk u_ld (.i({1'b0, n_rly_q_0__s0_y1__o[0]}));", txt)

    def test_find_meets_reach_lattice_and_avoids_macros(self):
        m = relay('qkd_rlys_1')
        blk = dict(name='blk', W=200000, H=200000, pins=[], pd={})
        geo = KS.Geo({'qkd_rlys_1': m, 'blk': blk}, {'u': (0, 0, 'R0')}, (2000000, 2000000), {})
        geo.build_bins({'u': 'blk'})
        cons = [(geo.pin('qkd_rlys_1', 'a'), [(100000, 250000)], 400),
                (geo.pin('qkd_rlys_1', 'b'), [(700000, 250000)], 400)]
        xy = geo.find('qkd_rlys_1', cons)
        self.assertIsNotNone(xy)
        x, y = xy
        self.assertFalse(geo.collides(x, y, m['W'], m['H']))
        for offs, pts, r in cons:
            for dx, dy in offs:
                for X, Y in pts:
                    self.assertLessEqual(abs(X - x - dx) + abs(Y - y - dy), (r - KS.MARGIN_UM) * 1000)
        rule = geo.rule('qkd_rlys_1')
        self.assertIn(x % rule['x']['joint_period_nm'], rule['x']['legal_origins_mod_joint_nm'])

    def test_find_refuses_span_beyond_two_reaches(self):
        m = relay('qkd_rlys_1')
        geo = KS.Geo({'qkd_rlys_1': m}, {}, (4000000, 4000000), {})
        geo.build_bins({})
        cons = [(geo.pin('qkd_rlys_1', 'a'), [(0, 0)], 400), (geo.pin('qkd_rlys_1', 'b'), [(900000, 0)], 400)]
        self.assertIsNone(geo.find('qkd_rlys_1', cons))

    def test_siblings_cover_every_bus_slice(self):
        std = {'rly_pvin_EN_0_21__s0', 'rly_pvin_EN_0_21__s1', 'rly_pvin_EN_0_22__s0'}
        self.assertEqual(KS.siblings('rly_pvin_EN_0_21__s1', std), ['rly_pvin_EN_0_21__s0', 'rly_pvin_EN_0_21__s1'])

    def test_pvfork_payload_and_header_replicas_are_atomic(self):
        base = {f'pvfork_ES_2__u_r{i}' for i in range(4)}
        repaired = {n + '_x2' for n in base}
        other = {'pvfork_ES_3__u_r1', 'unrelated__u_r1', 'pvfork_ES_2__u_r1_x3'}
        for n in base:
            self.assertEqual(KS.siblings(n, base | repaired | other), sorted(base))
        for n in repaired:
            self.assertEqual(KS.siblings(n, base | repaired | other), sorted(repaired))
        self.assertEqual(KS.siblings('unrelated__u_r1', base | other), ['unrelated__u_r1'])

    def test_inserted_standard_stage_preserves_replica_depth(self):
        std = {'rly_q_0__s0_x2', 'rly_q_0__s1_x2', 'rly_q_0__s1_x3', 'rly_q_0__s1'}
        self.assertEqual(KS.siblings('rly_q_0__s1_x2', std), ['rly_q_0__s0_x2', 'rly_q_0__s1_x2'])


def blk(name='blk'):
    out = dict(name=name, W=12960, H=12960, pins=[dict(name='i', use='SIGNAL', rects=[('M3', (8100, 0, 8118, 37))])])
    out['pd'] = {p['name']: p for p in out['pins']}
    return out


SPINE = """module die;
  wire [0:0] n_x;
  wire [0:0] n_y;
  qkd_rlys_1 rly_q_0__s0 (.ck(n_clk_core_c), .a(n_x[0]), .b(n_y[0]));
  blk u_l0 (.i(n_y[0]));
  blk u_l1 (.i(n_y[0]));
  blk u_l2 (.i(n_y[0]));
endmodule""".split('\n')
CLASSES = [(36, 400.0), (296, 370.0), (100000, 340.0)]


class AfterSpineTest(unittest.TestCase):
    """KVR-PLACE2 10-19: an AFTER fan-out spread far beyond reach (kvs14r ks_acal -> 8 expanded ASTK eps over ~10 mm)
    is planned whole in ONE iteration as a tapped spine + pads; every load ends at the SAME depth (one bus age) and
    every hop of the rendered chain is within reach."""

    def plan(self):
        place = {'rly_q_0__s0': (0, 0, 'R0'), 'u_l0': (0, 1500000, 'R0'), 'u_l1': (0, 2700000, 'R0'),
                 'u_l2': (0, 3900000, 'R0')}
        macros = {'qkd_rlys_1': relay('qkd_rlys_1'), 'blk': blk()}
        geo = KS.Geo(macros, dict(place), (1000000, 5000000), {})
        geo.build_bins({'rly_q_0__s0': 'qkd_rlys_1', 'u_l0': 'blk', 'u_l1': 'blk', 'u_l2': 'blk'})
        dirs = {'blk': {'i': 'INPUT'}}
        edits, recs, ref = KS.plan_repairs({('rly_q_0__s0', 'u_l0')}, SPINE, SPINE, {}, [], geo, dirs, expr_bits,
                                           CLASSES, 2, None)
        return geo, edits, recs, ref

    def test_spine_equal_depth_and_reach(self):
        geo, edits, recs, ref = self.plan()
        self.assertEqual(ref, [])
        lines, place = KS.apply_edits(SPINE, '', edits, expr_bits)
        net = KS.Net(lines, {'blk': {'i': 'INPUT'}}, expr_bits)
        # walk every load back to the original station: equal depth, every hop within the 1-b class reach
        depths = {}
        for ld in ('u_l0', 'u_l1', 'u_l2'):
            d, cur, port = 0, ld, 'i'
            while cur != 'rly_q_0__s0':
                drv = net.drv[net.bits(cur, port)[0]]
                a = geo.ep_points(drv[0], net.insts[drv[0]][0], 'b', 0)
                b = geo.ep_points(cur, net.insts[cur][0], port, 0)
                self.assertTrue(a and b)
                self.assertLessEqual(min(abs(x - u) + abs(y - v) for x, y in a for u, v in b), 400000)
                cur, port, d = drv[0], 'a', d + 1
            depths[ld] = d - 1
        self.assertEqual(len(set(depths.values())), 1, depths)
        self.assertGreaterEqual(depths['u_l2'], 9)              # 3.9 mm at <= 400 um a hop
        roles = {r['role'] for r in recs}
        self.assertTrue({'spine', 'pad'} <= roles, roles)
        self.assertEqual(len(recs), len(edits))
        for e in edits:
            self.assertIn(f'findInst {e["inst"]}]', place)

    def test_progress_off_refuses(self):
        import os
        os.environ['OT_KV_STATIONS_AFTER_PROGRESS'] = '0'
        try:
            geo, edits, recs, ref = self.plan()
        finally:
            del os.environ['OT_KV_STATIONS_AFTER_PROGRESS']
        self.assertEqual(edits, [])
        self.assertEqual(ref[0]['op'], 'after')


class StaleGuardTest(unittest.TestCase):
    def test_render_refuses_stale_line_index(self):
        import kv_fwd_lanes as FL
        F = dict(new={'rly_q_0__s0': ('qkd_rlysh_1', '.a(n_x[0])')}, where={'rly_q_0__s0': (1, '  ')}, add_wires=[])
        with self.assertRaises(ValueError):
            FL.render(SPINE, F)

    def test_audit_fails_closed_on_missing_instance(self):
        import kv_lane_reach as LR
        r = LR.audit('\n'.join(SPINE), '', '', '', dict(changes=[]), CLASSES, extra={'rly_gone_y3'})
        self.assertEqual(r['status'], 'FAIL')
        self.assertEqual(r['unmeasured'][0]['reason'], 'audited instance missing from the netlist')


if __name__ == '__main__':
    unittest.main()
