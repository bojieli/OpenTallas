#!/usr/bin/env python3
"""Tests for tools/die_plan/qc_face_reach_form.py (QC-TYPES-6s FACE-REACH class)."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_face_reach_form as F  # noqa: E402

BOUND = '''module t_bound (input wire clk, input wire arst_n, output wire [4:0] cw_n2, output wire [4:0] cw_s2);
    wire rst_n = arst_n;
    wire [3:0] w_u_xh2_n_d, w_u_xh2_s_d;
    ot_dp_st #(.W(4)) u_bout_cw_n2 (.clk(clk), .rst_n(rst_n), .d(w_u_xh2_n_d[3:0]), .ea(rst_n), .q(cw_n2[3:0]), .eq(cw_n2[4]));
    ot_dp_st #(.W(4)) u_bout_cw_s2 (.clk(clk), .rst_n(rst_n), .d(w_u_xh2_s_d[3:0]), .ea(rst_n), .q(cw_s2[3:0]), .eq(cw_s2[4]));
endmodule
'''
CELLS = '''module ot_dp_st #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d, input wire ea,
    output reg [W-1:0] q, output reg eq);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n) if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
'''
PINS = [{'bus': 'cw_n2', 'bit': i, 'x': 48.0 + i, 'y': 1339.2, 'face': 'N'} for i in range(5)] + \
       [{'bus': 'cw_s2', 'bit': i, 'x': 48.0 + i, 'y': 0.0, 'face': 'S'} for i in range(5)]


def viol(slack, port, sx, sy):
    return '\t'.join([str(slack), 'a/QN', f'u_bound.u_bout_{port}/q[1]$_DFF_P_/D', 'u_bound.u_u_xh2.n_d[1]$_DFF_P_',
                      str(sx), str(sy), f'u_bound.u_bout_{port}/q[1]$_DFF_P_', '50', '1330'])


class T(unittest.TestCase):
    def kit(self):
        d = Path(tempfile.mkdtemp())
        (d / 'rtl').mkdir()
        (d / 'run/results').mkdir(parents=True)
        (d / 'rtl/t_bound.sv').write_text(BOUND)
        (d / 'rtl/bind_cells.sv').write_text(CELLS)
        (d / 'config.mk').write_text('export VERILOG_FILES = /work/rtl/t.sv /work/rtl/t_bound.sv\n')
        (d / 'face_flops.tcl').write_text('# hooks\n')
        (d / 'pins.json').write_text(json.dumps(PINS))
        (d / '.kwrs_done.1').write_text('do-cts\n')
        self.addCleanup(shutil.rmtree, d)
        return d

    def test_measure_far_face_only(self):
        lines = [viol(-106.3, 'cw_n2', 50, 240), viol(-90, 'cw_n2', 60, 250), viol(-5, 'cw_s2', 50, 40)]
        s = F.measure(lines, PINS, 450.0)
        self.assertEqual(list(s), ['cw_n2'])            # S face is 40 um away: no stage
        self.assertEqual(s['cw_n2']['stages'], 2)        # ~1090 um -> 3 hops of <= 450
        self.assertEqual(s['cw_n2']['endpoints'], 2)
        self.assertAlmostEqual(s['cw_n2']['worst_ps'], -106.3)

    def test_transform_exact_and_strict(self):
        new, olds, news, w = F.transform(BOUND, {'cw_n2': {'stages': 2}})
        self.assertIn('ot_qc_face_reach_n2 #(.W(4)) u_reach_cw_n2', new)
        self.assertIn('.d(reach_cw_n2), .ea(reach_cw_n2_eq), .q(cw_n2[3:0])', new)
        self.assertIn('u_bout_cw_s2 (.clk(clk), .rst_n(rst_n), .d(w_u_xh2_s_d[3:0])', new)   # untouched
        self.assertEqual(w, {'cw_n2': 4})
        with self.assertRaises(AssertionError):
            F.transform(BOUND, {'nope': {'stages': 1}})

    def test_transform_rstn_tap_face_flop(self):
        # RSTN-TAP (bind.py boundary_reset_selector): a far face flop on its same-depth tap net rst_n_t<i>
        b = BOUND.replace('u_bout_cw_n2 (.clk(clk), .rst_n(rst_n), .d(w_u_xh2_n_d[3:0]), .ea(rst_n)',
                          'u_bout_cw_n2 (.clk(clk), .rst_n(rst_n_t5), .d(w_u_xh2_n_d[3:0]), .ea(rst_n_t5)')
        new, olds, news, w = F.transform(b, {'cw_n2': {'stages': 1}})
        self.assertIn('u_reach_cw_n2 (.clk(clk), .rst_n(rst_n_t5), .d(w_u_xh2_n_d[3:0]), .ea(rst_n_t5)', new)
        self.assertIn('u_bout_cw_n2 (.clk(clk), .rst_n(rst_n_t5), .d(reach_cw_n2), .ea(reach_cw_n2_eq)', new)

    def test_module_stage_names(self):
        m = F.reach_module(3)
        for j in range(3):
            self.assertIn(f' s{j} (', m)
        self.assertIn('.q(q), .eq(eq)', m)

    def test_apply_writes_receipt_anchor_bench(self):
        k = self.kit()
        spec = {'cw_n2': {'stages': 2, 'src_xy': [50, 240], 'pin_xy': [50, 1339.2]}, '_die': [613.4, 1339.2]}
        b = k / 'bench'
        meta = F.apply(k, spec, b)
        self.assertEqual(meta['added_rx_clk_PIN_cycles'], {'cw_n2': 2})
        self.assertEqual(meta['added_data_flops'], 10)
        self.assertTrue((k / '.kwrs_done.1.before_face_reach').exists())
        self.assertFalse((k / '.kwrs_done.1').exists())
        self.assertIn('/work/rtl/ot_qc_face_reach.sv ', (k / 'config.mk').read_text())
        t = (k / 'face_reach_place.tcl').read_text()
        self.assertIn('u_bound.u_reach_cw_n2.s0 {', t)
        self.assertIn('u_bound.u_reach_cw_n2.s1 {', t)
        self.assertIn('source /work/face_reach_place.tcl', (k / 'face_flops.tcl').read_text())
        with self.assertRaises(AssertionError):     # a kit with a synthesis result is refused
            k2 = self.kit()
            (k2 / 'run/results/1_2_yosys.v').write_text('')
            F.apply(k2, spec, k2 / 'b')
        if shutil.which('iverilog'):
            r = subprocess.run(['bash', str(b / 'run.sh')], capture_output=True, text=True)
            self.assertIn('BENCH_RC 0', r.stdout, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
