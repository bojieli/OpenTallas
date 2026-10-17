"""DIE-CLOCK 2026-10-16: fixed 3:4 seam constraints of the S81 die STA kit (tools/s81/die_sta.py seam_constraints)."""
import sys, types, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_sta as D  # noqa: E402

I = lambda n, m: types.SimpleNamespace(name=n, master=m)


class SeamTest(unittest.TestCase):
    def die(self):
        return dict(insts=[I('vt', 'ot_s81_vm_x43_t_w512_1015_f4'), I('vs', 'ot_s81_vm_x43_s_w1026_1015_f4'),
                           I('k34t', 'ot_s81_vm_x34_t'), I('ct', 'dsfd_capt_x8x_t_e'), I('cs', 'dsfd_capt_x8x_s_e'),
                           I('a', 'dsfd_hstnh_2164'), I('st', 'dsfd_capt_status_x43_s')],
                    buses=[('rst_cap', 'reset', 1, [('g', 'o'), ('ct', 'rst'), ('a', 'rst')]),
                           ('rst_x', 'reset', 1, [('g', 'o'), ('a', 'rst')]), ('d0', 'hub', 8, [('ct', 'b'), ('cs', 'b')])])

    def test_seams_related_with_compiled_windows(self):
        L, r = D.seam_constraints(self.die())
        t = '\n'.join(L)
        self.assertNotIn('-group {clk_serial}', t)               # serial and stream related
        self.assertIn('set_max_delay 1388.889 -from [get_clocks clk_stream] -to [get_pins -quiet {cs/* st/* vs/*}]', t)
        self.assertIn('set_min_delay -1111.111 -from [get_clocks clk_serial] -to [get_pins -quiet {ct/* k34t/* vt/*}]', t)
        self.assertIn('set_false_path -through [get_nets -quiet {n_rst_x}]', t)
        self.assertIn('set_false_path -through [get_nets {n_rst_cap}] -to [get_pins -quiet {a/rst}]', t)  # seam reset timed
        self.assertEqual(r['timed_reset_nets'], ['n_rst_cap'])
        self.assertNotIn('n_rst_*', t)

    def test_die_without_seams_unchanged(self):
        d = self.die()
        d['insts'] = [I('a', 'dsfd_hstnh_2164')]
        L, r = D.seam_constraints(d)
        self.assertEqual(L, ['set_clock_groups -asynchronous -group {clk_serial} -group {clk_hbm} -group [get_clocks -quiet {clk_stream ck_col_*}]',
                             'set_false_path -through [get_nets -quiet {n_rst_* n_rs_col_* por_n}]'])
        self.assertEqual(r['seam_instances'], 0)


if __name__ == '__main__':
    unittest.main()
