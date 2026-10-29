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


if __name__ == '__main__':
    unittest.main()
