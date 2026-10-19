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


if __name__ == '__main__':
    unittest.main()
