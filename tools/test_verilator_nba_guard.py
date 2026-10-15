#!/usr/bin/env python3
"""Real Verilator 5.050 tests for the in-place NBA-loop guard (tools/verilator_nba_guard.py) and the drop-in
front end (tools/verilator_guarded.py). Each model is built and SIMULATED: the guard must flag exactly the
models whose measured delay is wrong, and pass the ones that simulate correctly."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verilator_nba_guard as G  # noqa: E402
import verilator_guarded as W  # noqa: E402

VL = Path.home() / '.local/opentallas-tools/verilator-5.050/bin'
REAL = VL / 'verilator.real' if (VL / 'verilator.real').exists() else VL / 'verilator'

# Four chained ot_hdc_v41x_vdly-style delay lines (D stages each) per tile, NT tiles.
CHAIN = r'''
module vdly #(parameter integer D = 1) (input wire clk, input wire rst_n, input wire d, output wire q);
    reg [D:0] r; integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r[D:1] <= {D{1'b0}};
        else for (i = 1; i <= D; i = i + 1) r[i] <= (i == 1) ? d : r[i-1];
    end
    assign q = r[D];
endmodule
module tile #(parameter integer FPL=6) (input wire clk, input wire rst_n, input wire d, output wire [3:0] q);
  genvar l; generate for (l=0;l<4;l=l+1) begin: lv
    wire din = (l==0)? d : q[l-1];
    vdly #(.D(FPL)) u(.clk(clk),.rst_n(rst_n),.d(din),.q(q[l]));
  end endgenerate
endmodule
module tb;
  reg clk=0, rst_n=0, d=0; integer cyc=0, seen=-1; wire [3:0] q[0:NT-1];
  genvar t; generate for (t=0;t<NT;t=t+1) begin: tl
    tile #(.FPL(TFPL)) ti(.clk(clk),.rst_n(rst_n),.d(d),.q(q[t]));
  end endgenerate
  always #5 clk=~clk;
  always @(posedge clk) begin cyc<=cyc+1; if(cyc==2) rst_n<=1; d <= (cyc==5);
     if (q[NT-1][3] && seen<0) seen=cyc;
     if(cyc==LIMIT) begin $display("RESULT %0d", seen); $finish; end end
endmodule
'''
# Blocking prefix loop in a clocked process: same C++ shape, correct semantics -> must not be flagged.
BLOCKING = r'''
// A comment naming a module must not shift module scoping. Another module in the same sources writes a
// variable of the same name with <=; the tb's blocking loop must still be recognised as blocking.
module other(input wire clk); reg [8:0] p; integer i;
  always @(posedge clk) for (i=1;i<9;i=i+1) p[i] <= p[i-1];
endmodule
module tb;
  reg clk=0; integer cyc=0; reg [7:0] x=8'h5a; reg [8:0] p; reg [8:0] o2; integer i;
  always #5 clk=~clk;
  always @(posedge clk) begin
    p[0] = 1'b1; for (i=1;i<9;i=i+1) p[i] = p[i-1] ^ x[i-1];
    o2 <= p; x <= x + 8'd3; cyc <= cyc + 1;
    if (cyc==10) begin $display("RESULT %0d", o2); $finish; end
  end
endmodule
'''

# NBA loop whose value does not read the target, with a later read in the same process: Verilator may keep
# it in place legitimately (reads ordered first); it simulates correctly and must not be flagged.
NO_CARRY = r'''
module tb;
  reg clk=0; integer cyc=0; reg [7:0] src=0; reg [7:0] cflt; reg [31:0] acc; integer i, first=-1;
  always #5 clk=~clk;
  always @(posedge clk) begin
    if (cyc==0) begin cflt <= 0; acc <= 0; end
    else begin for (i = 0; i < 8; i = i + 1) cflt[i] <= src[i]; acc <= acc + (|cflt); end
    src <= (cyc==3) ? 8'h10 : 8'h00; cyc <= cyc + 1;
    if (acc!=0 && first<0) first = cyc;
    if (cyc==12) begin $display("RESULT %0d", first); $finish; end
  end
endmodule
'''


BIT_UPDATE = r'''
module bit_update(input wire clk, input wire [127:0] set_bits, clear_bits, output wire [127:0] q);
  reg [127:0] zv /* verilator public_flat_rw */;
  assign q = zv;
  integer i;
  initial zv = 0;
  always @(posedge clk) for(i=0;i<128;i=i+1) begin
    if (set_bits[i]) zv[i] <= 1'b1;
    else if (clear_bits[i]) zv[i] <= 1'b0;
  end
endmodule
module tb;
  reg clk=0; reg [127:0] set_bits=0,clear_bits=0, expected=0;
  wire [127:0] zv;
  bit_update dut(.clk(clk), .set_bits(set_bits), .clear_bits(clear_bits), .q(zv));
  always #5 clk=~clk;
  initial begin
    for(integer c=0;c<12;c=c+1) begin
      @(negedge clk);
      set_bits = 128'h16429adcbffedabe62894790398216ad ^ (128'h12345678123456789abcdef09abcdef0 << c);
      clear_bits = 128'hffeeddccbbaa00991122334455667788 >> c;
      expected = (expected | set_bits) & ~(clear_bits & ~set_bits);
      @(posedge clk); #1;
      if(zv !== expected) $fatal(1,"BIT_UPDATE_MISMATCH");
    end
    $display("RESULT 12"); $finish;
  end
endmodule
'''


@unittest.skipUnless(REAL.exists(), 'Verilator 5.050 fleet install required')
class Guard(unittest.TestCase):
    def build(self, w, src, flags, front=None):
        (w / 't.sv').write_text(src)
        cmd = [str(front or REAL), '--binary', '--timing', '-O1', '-Wno-fatal', '-Wno-lint', *flags,
               '--top-module', 'tb', '-Mdir', 'obj', '-o', 'sim', 't.sv']
        env = dict(os.environ, OT_VERILATOR_REAL=str(REAL))
        p = subprocess.run(cmd, cwd=w, capture_output=True, text=True, env=env, timeout=900)
        return p

    def sim(self, w):
        out = subprocess.run([str(w / 'obj/sim')], capture_output=True, text=True, timeout=120).stdout
        return int(re.search(r'RESULT (\d+)', out).group(1))

    def chain(self, fpl, unroll, nt=2):
        lim = 60 + 4 * fpl * 2
        src = CHAIN.replace('NT', str(nt)).replace('TFPL', str(fpl)).replace('LIMIT', str(lim))
        return src, (['--unroll-count', str(unroll)] if unroll else [])

    def test_miscompile_is_flagged_exactly_when_simulation_is_wrong(self):
        cases = [(6, 1, True), (6, 5, True), (6, 6, False), (6, None, False), (70, None, True), (70, 128, False)]
        for fpl, unroll, bad in cases:
            with self.subTest(fpl=fpl, unroll=unroll), tempfile.TemporaryDirectory() as d:
                w = Path(d)
                src, flags = self.chain(fpl, unroll)
                p = self.build(w, src, flags)
                self.assertEqual(p.returncode, 0, p.stdout[-3000:] + p.stderr[-3000:])
                seen = self.sim(w)
                expected = 6 + 4 * fpl  # pulse launched at cyc 5 crosses 4 x FPL stages
                self.assertEqual(seen != expected, bad, f'seen={seen} expected={expected}')
                r = G.scan(str(w / 'obj'))
                self.assertEqual(bool(r['findings']), bad, G.summarize(r))
                if bad:
                    self.assertTrue(all(f['source_check'] == 'NBA_IN_RTL' for f in r['findings']))

    def test_blocking_prefix_loop_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            p = self.build(w, BLOCKING, ['--unroll-count', '1'])
            self.assertEqual(p.returncode, 0, p.stderr[-3000:])
            r = G.scan(str(w / 'obj'))
            self.assertGreater(r['loops_checked'], 0)
            self.assertEqual(r['findings'], [])
            self.assertEqual(r['blocking_loops_excluded'], 1)

    def test_value_without_loop_carried_read_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            self.assertEqual(self.build(w, NO_CARRY, ['--unroll-count', '1']).returncode, 0)
            self.assertEqual(self.sim(w), 6)  # iverilog reference
            self.assertEqual(G.scan(str(w / 'obj'))['findings'], [])

    def test_front_end_refuses_bad_model_and_passes_good_one(self):
        front = HERE / 'verilator_guarded.py'
        for unroll, rc in ((1, W.GUARD_EXIT), (8, 0)):
            with self.subTest(unroll=unroll), tempfile.TemporaryDirectory() as d:
                w = Path(d)
                src, flags = self.chain(6, unroll)
                (w / 't.sv').write_text(src)
                (w / 'args.f').write_text('-Mdir objf -o sim\n')
                env = dict(os.environ, OT_VERILATOR_REAL=str(REAL))
                cmd = [sys.executable, str(front), '--binary', '--timing', '-Wno-fatal', '-Wno-lint', *flags,
                       '--top-module', 'tb', '-f', 'args.f', 't.sv']
                p = subprocess.run(cmd, cwd=w, capture_output=True, text=True, env=env, timeout=900)
                self.assertEqual(p.returncode, rc, p.stderr[-3000:])
                if rc:
                    self.assertIn('VERILATOR_NBA_GUARD FAIL', p.stderr)
                self.assertTrue((w / 'objf').is_dir())

    def test_independent_bit_set_clear_preserves_only_its_exact_word(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            p = self.build(w, BIT_UPDATE, ['--unroll-count', '1'])
            self.assertEqual(p.returncode, 0, p.stderr[-3000:])
            self.assertEqual(self.sim(w), 12)
            r = G.scan(str(w / 'obj'))
            self.assertGreater(r['independent_bit_updates_excluded'], 0)
            self.assertEqual(r['findings'], [], G.summarize(r))

    def test_preserve_match_is_exact_and_requires_independent_rtl_value(self):
        lhs = 'vlSelfRef.tb__DOT__zv[i >> 5U]'
        bit = '((IData)(1U) << (i & 31U))'
        self.assertTrue(G._preserves_exact_word(lhs, '(' + lhs + ' | ' + bit + ')'))
        self.assertTrue(G._preserves_exact_word(lhs, '(' + lhs + ' & ~' + bit + ')'))
        self.assertFalse(G._preserves_exact_word(lhs, '(vlSelfRef.tb__DOT__zv[j >> 5U] | ' + bit + ')'))
        self.assertFalse(G._preserves_exact_word(lhs, '(' + lhs + ' + ' + bit + ')'))
        parts = ['tb', 'zv']
        independent = {'tb': ["module tb; reg [127:0] zv; always @(posedge clk) if (s[i]) zv[i] <= 1'b1; endmodule"]}
        dependent = {'tb': ["module tb; reg [127:0] zv; always @(posedge clk) zv[i] <= zv[i-1]; endmodule"]}
        word_or = {'tb': ["module tb; reg [31:0] zv [0:1]; always @(posedge clk) zv[0] <= zv[0] | mask; endmodule"]}
        self.assertTrue(G._independent_nba_value(independent, parts))
        self.assertFalse(G._independent_nba_value(dependent, parts))
        self.assertFalse(G._independent_nba_value(word_or, parts))
        self.assertFalse(G._independent_nba_value(independent, ['missing', 'zv']))
        mixed = {'tb': ["module tb; reg [127:0] zv; always @(posedge clk) begin\n zv[i] <= 1'b1; if (c) begin\n zv[j] <= zv[j-1]; end end endmodule"]}
        self.assertFalse(G._independent_nba_value(mixed, parts))

    def test_no_model_modes_and_unreadable_sources(self):
        self.assertIsNone(W.model_dir(['--lint-only', 'x.sv'], Path('/tmp')))
        self.assertEqual(W.model_dir(['--cc', 'x.sv'], Path('/w')), Path('/w/obj_dir'))
        self.assertEqual(W.model_dir(['--Mdir=o2', 'x.sv'], Path('/w')), Path('/w/o2'))
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            src, flags = self.chain(6, 1, nt=1)
            self.assertEqual(self.build(w, src, flags).returncode, 0)
            (w / 't.sv').unlink()  # sources gone: findings are kept (fail closed), marked UNAVAILABLE
            r = G.scan(str(w / 'obj'))
            self.assertTrue(r['findings'])
            self.assertTrue(all(f['source_check'] == 'UNAVAILABLE' for f in r['findings']))


if __name__ == '__main__':
    unittest.main()
