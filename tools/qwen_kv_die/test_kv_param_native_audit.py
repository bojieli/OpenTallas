#!/usr/bin/env python3
"""KV-PARAMS 10-19: native parameter audit + receipts + unsigned [31:0] parameter parsing.

The end-to-end cases run the real audit (real Yosys equiv over Liberty cell models) on a hand-routed ASAP7 netlist:
a 2-stage async-reset shift register with an ot_prs_* replica flop and a tap cell.  D=2 must prove, D=3 (the parameter
the view was NOT built with) must refuse, and only the proven audit becomes a receipt that strict
kv_expand_parameters.preserve accepts.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import kv_expand_parameters as EP  # noqa: E402
import kv_param_native_audit as A  # noqa: E402
from dft import liberty as lib  # noqa: E402

ROOT = HERE.parents[1]
RTL = '''module t #(parameter integer D = 2) (input ck, input rst_n, input a, output y);
  reg [D-1:0] sr;
  always @(posedge ck or negedge rst_n) if (!rst_n) sr <= 0; else sr <= {sr[D-2:0], a};
  assign y = sr[D-1];
endmodule
'''
GATE = r'''module t (ck, rst_n, a, y);
 input ck;
 input rst_n;
 input a;
 output y;
 wire q0n;
 wire q1n;
 wire q1r;
 wire s0;
 wire hi;
 TIEHIx1_ASAP7_75t_R tie (.H(hi));
 DFFASRHQNx1_ASAP7_75t_R \sr[0]$_DFF_PN0_  (.CLK(ck),
    .D(a),
    .QN(q0n),
    .RESETN(rst_n),
    .SETN(hi));
 INVx1_ASAP7_75t_R i0 (.A(q0n),
    .Y(s0));
 DFFASRHQNx1_ASAP7_75t_R \sr[1]$_DFF_PN0_  (.CLK(ck),
    .D(s0),
    .QN(q1n),
    .RESETN(rst_n),
    .SETN(hi));
 DFFASRHQNx1_ASAP7_75t_R ot_prs_00000_ff (.CLK(ck),
    .D(s0),
    .QN(q1r),
    .RESETN(rst_n),
    .SETN(hi));
 INVx1_ASAP7_75t_R i1 (.A(q1r),
    .Y(y));
 TAPCELL_ASAP7_75t_R TAP_0 ();
endmodule
'''


def have_tools():
    return Path(A.YOSYS).is_file() and all(p.is_file() for p in lib.default_asap7_liberty())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Fixture:
    def __init__(self, gate=GATE, rtl=RTL):
        self.root = Path(tempfile.mkdtemp(prefix='kvp_'))
        (self.root / 'rtl').mkdir()
        (self.root / 'rtl/t.v').write_text(rtl)
        self.view = 'physical/ref_tile/k/views/t'
        vd = self.root / self.view
        vd.mkdir(parents=True)
        for f, txt in (('t.lef', 'MACRO t\nEND t\n'), ('t_tt.lib', 'library(t_tt) {}\n'), ('t_ff.lib', 'library(t_ff) {}\n'),
                       ('insertion.json', '{}\n')):
            (vd / f).write_text(txt)
        (vd / 'abstract.json').write_text(json.dumps(dict(orfs_dir='/x/closure-loop/k-1/routes')))
        self.arch = self.root / 'arch/t/k-1'
        (self.arch / 'final').mkdir(parents=True)
        (self.arch / 'run/routes/r').mkdir(parents=True)
        for f in ('t.lef', 't_tt.lib', 't_ff.lib'):
            shutil.copy(vd / f, self.arch / 'final' / f)
        (self.arch / 'final/6_final.v').write_text(gate)
        (self.arch / 'commit.txt').write_text('0' * 40 + '\n')
        (self.arch / 'run/routes/r/physical.json').write_text(json.dumps(dict(design=dict(
            top='t', parameters=dict(D=2), sources=[dict(path='rtl/t.v', sha256=sha(self.root / 'rtl/t.v'))]))))
        self.audits = self.root / 'audits'
        self.audits.mkdir()

    def audit(self, name, d, expect='pass'):
        out = self.audits / f'{name}.audit.json'
        rc = A.main(['audit', '--root', str(self.root), '--module', 't', '--rtl', 'rtl/t.v', '--view', self.view,
                     '--params', json.dumps(dict(D=d)), '--archive-run', str(self.arch), '--work',
                     str(self.root / 'work' / name), '--out', str(out), '--expect', expect])
        return rc, json.loads(out.read_text())


class ParserTest(unittest.TestCase):
    def test_unsigned_vector_parameter(self):
        src = (ROOT / 'rtl/hdc/nearhbm/ot_qkh_subtiles.sv').read_text()
        d = EP.integer_defaults(src, 'ot_qkh_ktree')
        self.assertEqual(d, dict(ADD_LAT=7, MUL_LAT=6, SCALE=0x3DB504F3))
        self.assertIsInstance(d['SCALE'], EP.U32)
        values, lit = EP.evaluated({'SCALE': format(0xBDB504F3, '032b')}, d, 'ot_qkh_ktree')
        self.assertEqual(values['SCALE'], 0xBDB504F3)            # never sign-reinterpreted
        self.assertEqual(lit['SCALE'], "32'sb" + format(0xBDB504F3, '032b'))
        v2, _ = EP.evaluated({'ADD_LAT': '1' * 32}, d, 'ot_qkh_ktree')
        self.assertEqual(v2['ADD_LAT'], -1)                      # integers stay signed

    def test_other_vectors_refuse(self):
        for bad in ("parameter [7:0] A = 3", "parameter A = 3", "parameter [31:0] A = 33'h1",
                    "parameter [31:0] A = 32'h1FFFFFFFF", "parameter [31:0] A = B+1", "parameter logic [3:0] P=0"):
            with self.assertRaisesRegex(ValueError, 'unsupported parameter'):
                EP.integer_defaults(f'module m #({bad}) (input a);', 'm')


@unittest.skipUnless(have_tools(), 'yosys 0.68 / ASAP7 liberty not installed (fleet test)')
class AuditTest(unittest.TestCase):
    def test_matching_parameters_prove_and_receipt_is_strictly_admitted(self):
        fx = Fixture()
        rc, r = fx.audit('t', 2)
        self.assertEqual(rc, 0, r)
        self.assertTrue(r['proven'])
        self.assertEqual(r['gate']['replicas'], 1)
        self.assertEqual(r['state']['gold_only'], 0)
        self.assertIn('liberty bytes', r['closed']['view_tie'])
        rc, m = fx.audit('t_mut', 3, 'fail')                     # parameter the view was not built with
        self.assertEqual(rc, 0)
        self.assertFalse(m['proven'])
        A.main(['receipt', '--root', str(fx.root), '--audits', str(fx.audits), '--out', str(fx.root / 'rc')])
        prof = json.loads((fx.root / 'rc/profiles.json').read_text())
        self.assertEqual(set(prof), {'t'})
        lits, checked = EP.preserve(fx.root, 't', {'D': format(2, '032b')}, 'rtl/t.v', fx.view, prof)
        self.assertTrue(checked['native_qualified'])
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            EP.preserve(fx.root, 't', {'D': format(3, '032b')}, 'rtl/t.v', fx.view, prof)

    def test_unproven_or_drifted_audit_gives_no_receipt(self):
        fx = Fixture()
        fx.audit('t', 2)
        (fx.root / fx.view / 'insertion.json').write_text('{"changed": 1}\n')   # view drifted after the audit
        A.main(['receipt', '--root', str(fx.root), '--audits', str(fx.audits), '--out', str(fx.root / 'rc')])
        self.assertEqual(json.loads((fx.root / 'rc/profiles.json').read_text()), {})
        fx2 = Fixture(gate=GATE.replace('INVx1_ASAP7_75t_R i0', 'BUFx2_ASAP7_75t_R i0'))  # wrong routed logic
        rc, r = fx2.audit('t', 2)
        self.assertFalse(r['proven'])

    def test_view_from_another_run_refuses(self):
        fx = Fixture()
        (fx.arch / 'final/t_tt.lib').write_text('library(other) {}\n')
        (fx.arch / 'final/t.lef').write_text('MACRO other\nEND other\n')
        with self.assertRaises(SystemExit):
            fx.audit('t', 2)


# KV-PARAMS2 10-19 joint mode: unreset data pipe d0->d1 and an unreset constant metadata chain m0->m1 that synthesis
# m0->m1->m2->m3 removed (e's routed D is tied low; deeper than equiv_simple -seq 2), like the fp32 adder's *_err[1] chain.
JRTL = """module t #(parameter integer D = 2) (input ck, input rst_n, input a, output reg y, output reg e);
  reg d0, d1, m0, m1, m2, m3;
  always @(posedge ck) begin d0 <= a; d1 <= d0; m0 <= 1'b0; m1 <= m0; m2 <= m1; m3 <= m2; end
  always @(posedge ck or negedge rst_n) if (!rst_n) begin y <= 1'b0; e <= 1'b0; end else begin y <= d1; e <= m3; end
endmodule
"""
JGATE = r"""module t (ck, rst_n, a, y, e);
 input ck;
 input rst_n;
 input a;
 output y;
 output e;
 wire d0n, d0q, d1n, d1q, yn, en, hi, lo;
 TIEHIx1_ASAP7_75t_R tie (.H(hi));
 TIELOx1_ASAP7_75t_R til (.L(lo));
 DFFHQNx1_ASAP7_75t_R \d0$_DFF_P_  (.CLK(ck), .D(a), .QN(d0n));
 INVx1_ASAP7_75t_R i0 (.A(d0n), .Y(d0q));
 DFFHQNx1_ASAP7_75t_R \d1$_DFF_P_  (.CLK(ck), .D(d0q), .QN(d1n));
 INVx1_ASAP7_75t_R i1 (.A(d1n), .Y(d1q));
 DFFASRHQNx1_ASAP7_75t_R \y$_DFF_PN0_  (.CLK(ck), .D(d1q), .QN(yn), .RESETN(rst_n), .SETN(hi));
 INVx1_ASAP7_75t_R i2 (.A(yn), .Y(y));
 DFFASRHQNx1_ASAP7_75t_R \e$_DFF_PN0_  (.CLK(ck), .D(lo), .QN(en), .RESETN(rst_n), .SETN(hi));
 INVx1_ASAP7_75t_R i3 (.A(en), .Y(e));
endmodule
"""


@unittest.skipUnless(have_tools(), 'yosys 0.68 / ASAP7 liberty not installed (fleet test)')
class JointModeTest(unittest.TestCase):
    def run_audit(self, fx, name, extra):
        out = fx.audits / f'{name}.audit.json'
        A.main(['audit', '--root', str(fx.root), '--module', 't', '--rtl', 'rtl/t.v', '--view', fx.view,
                '--params', json.dumps(dict(D=2)), '--archive-run', str(fx.arch), '--work',
                str(fx.root / 'work' / name), '--out', str(out)] + extra)
        return json.loads(out.read_text())

    def test_constant_metadata_needs_joint_observation_and_reset_base(self):
        fx = Fixture(gate=JGATE, rtl=JRTL)
        plain = self.run_audit(fx, 'plain', [])
        self.assertFalse(plain['proven'])                         # e: arbitrary m3 in the induction state
        self.assertEqual(plain['state']['gold_only'], 4)
        os.remove(fx.audits / 'plain.audit.json')
        # the metadata registers have no routed flop (tied 0): the one power-up state gives them 0, so even a short
        # reset base holds; the base stays causal for real netlist differences (preset test below, ktree native mutant)
        short = self.run_audit(fx, 'short', ['--observe-zero-regex', r'^m[0-3]$', '--reset-base', '2'])
        self.assertTrue(short['base']['proven'])
        self.assertEqual(short['base']['paired_initial'], 8)
        os.remove(fx.audits / 'short.audit.json')
        r = self.run_audit(fx, 'joint', ['--observe-zero-regex', r'^m[0-3]$', '--reset-base', '4'])
        self.assertTrue(r['proven'], r)
        self.assertEqual(r['observe_zero']['signals'], ['m0', 'm1', 'm2', 'm3'])
        self.assertTrue(r['base']['proven'])
        self.assertEqual(r['base']['paired_initial'], 8)
        A.main(['receipt', '--root', str(fx.root), '--audits', str(fx.audits), '--out', str(fx.root / 'rc')])
        rec = json.loads((fx.root / 'rc/receipts/t.json').read_text())
        self.assertEqual(rec['evidence']['observe_zero']['signals'], ['m0', 'm1', 'm2', 'm3'])
        self.assertTrue(rec['evidence']['reset_base']['proven'])

    def test_netlist_that_differs_after_reset_refuses(self):
        # routed y presets to 1 instead of resetting to 0: the joint proof must refuse
        g = JGATE.replace('(.CLK(ck), .D(d1q), .QN(yn), .RESETN(rst_n), .SETN(hi))',
                          '(.CLK(ck), .D(d1q), .QN(yn), .RESETN(hi), .SETN(rst_n))')
        fx = Fixture(gate=g, rtl=JRTL)
        r = self.run_audit(fx, 'joint', ['--observe-zero-regex', r'^m[0-3]$', '--reset-base', '4'])
        self.assertFalse(r['proven'])


# KV-PARAMS3 10-20: --macro-cut (hard macro as a cut point) and --induct-seq (base window = induction depth).
CBB = """(* blackbox *)
module mac (input wire clk, input wire [1:0] a, output wire [1:0] q);
endmodule
"""
CRTL = """module t #(parameter integer D = 2) (input ck, input rst_n, input [1:0] x, output reg [1:0] y);
  reg [1:0] a_r;
  wire [1:0] q;
  always @(posedge ck) a_r <= x;
  mac u_m (.clk(ck), .a(a_r), .q(q));
  always @(posedge ck or negedge rst_n) if (!rst_n) y <= 2'b0; else y <= q;
endmodule
"""
CGATE = r"""module t (ck, rst_n, x, y);
 input ck;
 input rst_n;
 input [1:0] x;
 output [1:0] y;
 wire hi;
 wire an0, an1, aq0, aq1, q0, q1, yn0, yn1;
 TIEHIx1_ASAP7_75t_R tie (.H(hi));
 DFFHQNx1_ASAP7_75t_R \a_r[0]$_DFF_P_  (.CLK(ck), .D(x[0]), .QN(an0));
 INVx1_ASAP7_75t_R ia0 (.A(an0), .Y(aq0));
 DFFHQNx1_ASAP7_75t_R \a_r[1]$_DFF_P_  (.CLK(ck), .D(x[1]), .QN(an1));
 INVx1_ASAP7_75t_R ia1 (.A(an1), .Y(aq1));
 mac u_m (.clk(ck), .a({aq1, aq0}), .q({q1, q0}));
 DFFASRHQNx1_ASAP7_75t_R \y[0]$_DFF_PN0_  (.CLK(ck), .D(q0), .QN(yn0), .RESETN(rst_n), .SETN(hi));
 INVx1_ASAP7_75t_R iy0 (.A(yn0), .Y(y[0]));
 DFFASRHQNx1_ASAP7_75t_R \y[1]$_DFF_PN0_  (.CLK(ck), .D(q1), .QN(yn1), .RESETN(rst_n), .SETN(hi));
 INVx1_ASAP7_75t_R iy1 (.A(yn1), .Y(y[1]));
endmodule
"""


class CutFixture(Fixture):
    def __init__(self, gate=CGATE):
        super().__init__(gate=gate, rtl=CRTL)
        (self.root / 'rtl/mac_bb.v').write_text(CBB)
        pj = self.arch / 'run/routes/r/physical.json'
        d = json.loads(pj.read_text())
        d['design']['sources'].append(dict(path='rtl/mac_bb.v', sha256=sha(self.root / 'rtl/mac_bb.v')))
        pj.write_text(json.dumps(d))


@unittest.skipUnless(have_tools(), 'yosys 0.68 / ASAP7 liberty not installed (fleet test)')
class MacroCutTest(JointModeTest):
    def test_macro_cut_proves_and_records_cut_points(self):
        fx = CutFixture()
        r = self.run_audit(fx, 'cut', ['--macro-cut', 'mac', '--reset-base', '2', '--induct-seq', '2'])
        self.assertTrue(r['proven'], r)
        self.assertEqual(r['macro_cuts']['mac']['instances'], ['u_m'])
        self.assertEqual(r['macro_cut_points'], dict(compared_inputs=2, compared_input_bits=3, free_outputs=1,
                                                     free_output_bits=2))
        self.assertEqual(r['base']['checked_steps'], [3, 4])
        self.assertIn('macro cut points', r['equiv']['method'])
        A.main(['receipt', '--root', str(fx.root), '--audits', str(fx.audits), '--out', str(fx.root / 'rc')])
        self.assertEqual(set(json.loads((fx.root / 'rc/profiles.json').read_text())), {'t'})

    def test_macro_input_that_differs_refuses(self):
        fx = CutFixture(gate=CGATE.replace('INVx1_ASAP7_75t_R ia0', 'BUFx2_ASAP7_75t_R ia0'))
        r = self.run_audit(fx, 'cut', ['--macro-cut', 'mac', '--reset-base', '2', '--induct-seq', '2'])
        self.assertFalse(r['proven'])

    def test_short_induction_base_still_catches_reset_bug(self):
        g = JGATE.replace('(.CLK(ck), .D(d1q), .QN(yn), .RESETN(rst_n), .SETN(hi))',
                          '(.CLK(ck), .D(d1q), .QN(yn), .RESETN(hi), .SETN(rst_n))')
        fx = Fixture(gate=g, rtl=JRTL)
        r = self.run_audit(fx, 'joint', ['--observe-zero-regex', r'^m[0-3]$', '--reset-base', '2', '--induct-seq', '2'])
        self.assertFalse(r['proven'])
        # a 4-deep constant metadata chain needs a deeper induction: -seq 2 REFUSES (never a false pass); -seq 4 proves
        fx2 = Fixture(gate=JGATE, rtl=JRTL)
        r2 = self.run_audit(fx2, 'joint', ['--observe-zero-regex', r'^m[0-3]$', '--reset-base', '2', '--induct-seq', '2'])
        self.assertFalse(r2['proven'])
        self.assertIsNone(r2.get('base'))


if __name__ == '__main__':
    unittest.main()
