"""Causal checks of source/clock/depth identity used by the planning inventory."""
import unittest
import kv_reset_endpoint_calendar as R


class CalendarIdentity(unittest.TestCase):
    def vehicle(self, *, clock='n_clk_core_c', depth=1, root='rr'):
        lines = ['  qkd_rst_region rr (.ck(n_clk_core_c), .a(host_reset), .b(n_rst_root), .dly(d));',
                 '  qkd_rst_region other (.ck(n_clk_core_c), .a(other_reset), .b(n_rst_other), .dly(d));',
                 '  qkd_rlys_1 far (.ck(n_clk_core_c), .a(n_rst_root), .b(n_rrs_far));',
                 f'  qkd_rlys_1 near (.ck({clock}), .a({"n_rst_root" if root == "rr" else "n_rst_other"}), .b(n_rrs_near));',
                 '  qkd_landsh0_1 sink (.ck_s(n_clk_core_c), .ck(n_clk_core_WS), .en(n_rrs_far), .rs(receiver_reset));']
        if depth == 2:
            lines[3] = lines[3].replace('.a(n_rst_root)', '.a(n_rrs_far)')
        facts = dict(reach_um=405, wires=[
            dict(id='far/b->sink/en', witness_net='n_rrs_far[0]', pts=[[0, 0], [1000, 0]], max_um=1000),
            dict(id='near/b->dummy/a', witness_net='n_rrs_near[0]', pts=[[990, 0], [991, 0]], max_um=1)])
        # The nearby candidate's physical load needs a parseable instance.
        lines.append('  qkd_rlys_1 dummy (.ck(n_clk_core_c), .a(n_rrs_near), .b(n_rrs_dummy));')
        return R.inventory('\n'.join(lines), facts)

    def test_same_root_clock_depth_candidate(self):
        r = self.vehicle()
        self.assertEqual(r['nearest_same_root_depth_clock_within_reach'], 1)
        self.assertEqual(r['long_pairs'][0]['minimum_added_transport_edges'], 2)
        self.assertEqual(r['long_pairs'][0]['receiver_capture_edges'], 2)

    def test_source_clock_mutation_refused(self):
        self.assertEqual(self.vehicle(clock='n_clk_core_WS')['nearest_same_root_depth_clock_within_reach'], 0)

    def test_source_root_mutation_refused(self):
        self.assertEqual(self.vehicle(root='other')['nearest_same_root_depth_clock_within_reach'], 0)

    def test_reset_edge_mutation_refused(self):
        self.assertEqual(self.vehicle(depth=2)['nearest_same_root_depth_clock_within_reach'], 0)

    def test_cycle_refused(self):
        net = '  qkd_rlys_1 x (.ck(c), .a(n_rrs_y), .b(n_rrs_x));\n  qkd_rlys_1 y (.ck(c), .a(n_rrs_x), .b(n_rrs_y));'
        facts = dict(reach_um=405, wires=[dict(id='x/b->y/a', witness_net='n_rrs_x[0]', pts=[[0, 0], [1, 0]], max_um=1)])
        with self.assertRaisesRegex(ValueError, 'cycle'):
            R.inventory(net, facts)


if __name__ == '__main__':
    unittest.main()
