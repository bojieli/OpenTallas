import unittest
from join_scope import joined_instance, rescope

PLAIN = 'module qwen_kvsys_bound_top(clk_core); input wire clk_core; kv3_sys_c_part sys_c (.clk(clk_core)); endmodule'
JOIN = ('module qwen_kvsys_bound_top__without_start_provider(clk_core, pst_a); input wire clk_core; input wire pst_a;\n'
        ' kv3_sys_c_part sys_c (.clk(clk_core)); endmodule\n'
        'module qwen_kvsys_bound_top(\n clk_core, t_st_b5__clk);\n input wire clk_core;\n'
        '    qwen_kvsys_bound_top__without_start_provider u_bound (.clk_core(clk_core), .pst_a(rs_a));\n'
        '    ot_die_start_stages u_start_provider (.rs_a(rs_a));\nendmodule\n')
TB = 'assign a = dut.sys_c.d5_x[0]; assign b = dut.x_hub_Wi_o_host_n; qwen_kvsys_bound_top dut (.clk_core(ck_core));'


class JoinScope(unittest.TestCase):
    def test_plain_top_untouched(self):
        self.assertIsNone(joined_instance(PLAIN))

    def test_joined_top_rescopes_bench_refs(self):
        # fails on the pre-TOK-KV-7 bench (refs stay dut.sys_c -> Verilator "Can't find definition of 'sys_c'")
        inst = joined_instance(JOIN)
        self.assertEqual(inst, 'u_bound')
        out = rescope(TB, inst)
        self.assertIn('dut.u_bound.sys_c.d5_x[0]', out)
        self.assertIn('dut.u_bound.x_hub_Wi_o_host_n', out)
        self.assertIn('qwen_kvsys_bound_top dut (.clk_core(ck_core))', out)
        self.assertEqual(rescope(out, inst), out)

    def test_two_private_instances_fail(self):
        bad = JOIN.replace('    ot_die_start_stages', '    qwen_kvsys_bound_top__without_start_provider u_b2 (.clk_core(clk_core));\n    ot_die_start_stages')
        with self.assertRaises(ValueError):
            joined_instance(bad)


if __name__ == '__main__':
    unittest.main()
