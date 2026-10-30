import unittest
from bind_tb_clocks import bind_clocks


class ClockBinding(unittest.TestCase):
    TOP = 'module qwen_kvsys_bound_top(clk_core,clk_region_h000,clk_region_h111); input wire clk_region_h000; input wire clk_region_h111; endmodule'
    TB = 'qwen_kvsys_bound_top dut (.clk_core(ck_core));'

    def test_current_regions_and_idempotence(self):
        patched, names = bind_clocks(self.TOP, self.TB)
        self.assertEqual(names, ['clk_region_h000', 'clk_region_h111'])
        self.assertIn('.clk_region_h111(ck_core)', patched)
        self.assertEqual(bind_clocks(self.TOP, patched)[0], patched)

    def test_missing_clock_mutant(self):
        with self.assertRaises(ValueError):
            bind_clocks(self.TOP, self.TB.replace('ck_core)', 'ck_core), .clk_region_h000(0)'))

    def test_no_regions_unchanged(self):
        self.assertEqual(bind_clocks('module qwen_kvsys_bound_top(clk_core); endmodule', self.TB)[0], self.TB)

    def test_missing_start_provider_cannot_silently_drive_zero(self):
        top = self.TOP.replace('endmodule', 'input wire pst_phy_EN_0; endmodule')
        with self.assertRaisesRegex(ValueError, 'missing native START provider.*pst_phy_EN_0'):
            bind_clocks(top, self.TB)
        for conn in ('.pst_phy_EN_0()', '.pst_phy_EN_0(pst_a), .pst_phy_EN_0(pst_b)'):
            with self.subTest(conn=conn), self.assertRaises(ValueError):
                bind_clocks(top, self.TB.replace(');', ', '+conn+');'))
        connected = self.TB.replace(');', ', .pst_phy_EN_0(planned_start));')
        self.assertIn('.pst_phy_EN_0(planned_start)', bind_clocks(top, connected)[0])

    def test_unknown_declaration_fails(self):
        with self.assertRaises(ValueError):
            bind_clocks(self.TOP.replace('input wire clk_region_h000;', 'input wire [1:0] clk_region_h000;'), self.TB)

    def test_start_stage_clocks_driven_by_core(self):
        # TOK-KV-7: an integrated START provider exposes stage clock inputs on the public top (fails on the old tool:
        # left unconnected, every stage holds and START never propagates); the private top in the same file keeps
        # the pst_* inputs the provider now drives, and they are not bench pins
        top = ('module qwen_kvsys_bound_top__without_start_provider(clk_core, clk_region_h000, pst_a); '
               'input wire clk_region_h000; input wire pst_a; '
               'endmodule\nmodule qwen_kvsys_bound_top(\n clk_core, clk_region_h000, t_st_b5__clk, t_st_r1_1__clk);\n'
               'input wire clk_region_h000;\n input wire  t_st_b5__clk;\n input wire  t_st_r1_1__clk;\nendmodule')
        patched, names = bind_clocks(top, self.TB)
        self.assertEqual(names, ['clk_region_h000', 't_st_b5__clk', 't_st_r1_1__clk'])
        for n in names:
            self.assertEqual(patched.count('.' + n + '(ck_core)'), 1)
        self.assertEqual(bind_clocks(top, patched)[0], patched)


if __name__ == '__main__':
    unittest.main()
