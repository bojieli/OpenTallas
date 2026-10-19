#!/usr/bin/env python3
"""unit tests of tools/die_port_bind.py (the die netlist -> real RTL port-bind gate): every finding class on a toy die."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent / 'die_port_bind.py'
RTL = """
module a #(parameter integer N = 2, W = N*8) (input wire ck, input wire [W-1:0] i, output reg [W-1:0] o, input wire en);
  always @(posedge ck) if (en) o <= i;
endmodule
module shell (input wire [3:0] x, output wire [3:0] y);
  assign y = 4'd0;
endmodule
module wrap (input wire ck, input wire [15:0] i, output wire [15:0] o);
  a #(.N(2)) u (.ck(ck), .i(i), .o(o), .en(1'b1));
endmodule
"""


def run(die, extra=()):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / 'r.sv').write_text(RTL)
        (d / 'd.v').write_text(die)
        out = d / 'o.json'
        p = subprocess.run([sys.executable, str(TOOL), str(d / 'd.v'), '--rtl-root', str(d / 'none'), '--rtl-file', str(d / 'r.sv'),
                            '--out', str(out)] + list(extra), capture_output=True, text=True)
        return p.returncode, json.loads(out.read_text())


class T(unittest.TestCase):
    def test_pass(self):
        rc, r = run("module top (ck);\n  input ck;\n  wire [15:0] n1;\n  wire [15:0] n2;\n"
                    "  a u0 (.ck(ck), .i(n2), .o(n1), .en(ck));\n  wrap w (.ck(ck), .i(n1), .o(n2));\nendmodule\n")
        self.assertEqual(rc, 0, r['summary'])
        self.assertEqual(r['verdict'], 'PASS')

    def test_unread_output_bits(self):
        # A named net with no consumer used to pass and the SM would be synthesised away.
        rc, r = run("module top (ck);\n input ck;\n wire [15:0] dead;\n"
                    " a u (.ck(ck), .i({16{ck}}), .en(ck), .o(dead));\nendmodule\n")
        self.assertEqual(rc, 1)
        self.assertEqual(r['summary']['unread_net_bits'], 16)
        self.assertEqual(r['unread_nets'], {'dead': 16})

    def test_open_output(self):
        rc, r = run("module top (ck);\n input ck;\n"
                    " a u (.ck(ck), .i({16{ck}}), .en(ck), .o());\nendmodule\n")
        self.assertEqual(rc, 1)
        self.assertEqual(r['summary']['output_open_ports'], 1)
        self.assertIn('OUTPUT_OPEN', r['masters']['a']['fails'])

    def test_top_output_is_a_consumer(self):
        rc, r = run("module top (ck, y);\n input ck;\n output [15:0] y;\n"
                    " a u (.ck(ck), .i({16{ck}}), .en(ck), .o(y));\nendmodule\n")
        self.assertEqual(rc, 0, r['summary'])

    def test_duplicate_port(self):
        # r2h2/r2h4 GEN emitted .tt(actual) AND .tt(1538'h0) on one instance; Verilog keeps one silently -> FAIL
        rc, r = run("module top (ck);\n  input ck;\n  wire [15:0] n1;\n  wire [15:0] n2;\n"
                    "  a u0 (.ck(ck), .i(n2), .o(n1), .en(ck), .i(16'h0));\n  wrap w (.ck(ck), .i(n1), .o(n2));\nendmodule\n")
        self.assertEqual(rc, 1)
        self.assertEqual(r['summary']['duplicate_port_connections'], 1)
        self.assertIn('DUPLICATE_PORT', r['masters']['a']['fails'])
        self.assertEqual(r['masters']['a']['duplicate_port'], ['i'])

    def test_findings(self):
        rc, r = run("module top (ck);\n  input ck;\n  wire [15:0] n1;\n  wire [7:0] n4;\n  wire [3:0] n3;\n"
                    "  a u1 (.ck(ck), .i(n4), .o(n1), .q(n3));\n  shell s (.x(n3), .y(n3));\n  missing m (.a(n1));\n"
                    "  a #(.N(1)) u2 (.ck(ck), .i(n4), .o(), .en(1'b0));\nendmodule\n")
        self.assertEqual(rc, 1)
        S = r['summary']
        self.assertEqual(S['unbound_masters'], 1)
        self.assertEqual(S['stub_masters'], 1)
        m = r['masters']['a']
        self.assertIn('q', m['die_port_not_in_rtl'])
        self.assertIn('i', m['width_mismatch'])          # 8 vs 16 on u1 (u2 has N 1: 8 = 8)
        self.assertIn('en', m['input_unconnected'])
        self.assertIn('en', m['input_tied'])
        self.assertGreater(S['undriven_net_bits'], 0)    # n4 has no driver

    def test_declared_strap(self):
        die = ("module top (ck);\n  input ck;\n  wire [15:0] n1;\n  wire [15:0] n2;\n"
               "  a u0 (.ck(ck), .i(n2), .o(n1), .en(1'b1));\n  wrap w (.ck(ck), .i(n1), .o(n2));\nendmodule\n")
        rc, r = run(die)
        self.assertEqual(rc, 1)
        self.assertIn('input_tied', r['failing'])
        rc, r = run(die, ['--strap', 'a:en'])
        self.assertEqual(rc, 0, r['summary'])
        self.assertEqual(r['masters']['a']['straps'], ['en'])
        self.assertEqual(r['summary']['strap_ports'], 1)
        rc, r = run(die, ['--strap', 'a:i'])          # a strap on another port does not excuse the tie
        self.assertEqual(rc, 1)

    def test_declared_pad_bits(self):
        # DEDUPE padding: a 16-bit standard master used at logical width 12 ties i[15:12] low and leaves o[15:12] open
        die = ("module top (ck);\n  input ck;\n  wire [15:0] n1;\n  wire [11:0] n2;\n"
               "  a u0 (.ck(ck), .i({4'b0, n2}), .o(n1), .en(ck));\n  wrap w (.ck(ck), .i(n1), .o({n2, n1[3:0]}));\nendmodule\n")
        die = die.replace(".o({n2, n1[3:0]})", ".o())")
        die = die.replace("wire [11:0] n2;", "wire [11:0] n2;\n  wire [15:0] n9;").replace(".o())", ".o(n9))")
        die = die.replace("a u0 (.ck(ck), .i({4'b0, n2})", "a u0 (.ck(ck), .i({4'b0, n9[11:0]})")
        rc, r = run(die)
        self.assertIn('input_tied', r['failing'])                 # undeclared: still a tie
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / 'pads.json'
            pf.write_text(json.dumps({'pads': {'a': {'reason': 'dedupe: 12-bit use of the 16-bit master',
                                                     'ports': {'i': {'logical_width': 12}}}}}))
            rc, r = run(die, ['--pad-file', str(pf)])
            self.assertNotIn('input_tied', r['failing'], r['summary'])
            self.assertEqual(r['masters']['a']['pad_bits'], {'i': 4})
            self.assertEqual(r['summary']['pad_bits'], 4)
            pf.write_text(json.dumps({'pads': {'a': {'reason': 'x', 'ports': {'i': [[13, 15]]}}}}))
            rc, r = run(die, ['--pad-file', str(pf)])
            self.assertIn('input_tied', r['failing'])             # bit 12 is not declared
            one = die.replace("{4'b0, n9[11:0]}", "{4'b1000, n9[11:0]}")
            pf.write_text(json.dumps({'pads': {'a': {'reason': 'x', 'ports': {'i': {'logical_width': 12}}}}}))
            rc, r = run(one, ['--pad-file', str(pf)])
            self.assertIn('input_tied', r['failing'])             # a pad bit tied HIGH is not padding

    def test_declared_spare_outputs(self):
        # TOK-S81-GAPS/SVCP: a declared spare output range may stay unread; undeclared bits and open ports still fail
        die = ("module top (ck, y);\n input ck;\n output [11:0] y;\n wire [15:0] o;\n"
               " a u (.ck(ck), .i({16{ck}}), .en(ck), .o(o));\n assign_free x ();\nendmodule\n").replace(" assign_free x ();\n", "")
        die = die.replace("output [11:0] y;\n wire [15:0] o;", "output [11:0] y;\n wire [15:0] o;\n wire [3:0] o_nc;")
        die = die.replace(".o(o)", ".o({o_nc, y})")
        rc, r = run(die)
        self.assertEqual(rc, 1)
        self.assertEqual(r['summary']['unread_net_bits'], 4)
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / 'pads.json'
            pf.write_text(json.dumps({'instances': {'u': {'master': 'a', 'reason': 'spare face', 'ports': {'o': [[12, 15]]}}}}))
            rc, r = run(die, ['--pad-file', str(pf)])
            self.assertEqual(rc, 0, r['summary'])
            self.assertEqual(r['summary']['spare_out_bits'], 4)
            pf.write_text(json.dumps({'instances': {'u': {'master': 'a', 'reason': 'x', 'ports': {'o': [[13, 15]]}}}}))
            rc, r = run(die, ['--pad-file', str(pf)])
            self.assertEqual(r['summary']['unread_net_bits'], 1)   # bit 12 is not declared
            opn = "module top (ck);\n input ck;\n a u (.ck(ck), .i({16{ck}}), .en(ck), .o());\nendmodule\n"
            pf.write_text(json.dumps({'instances': {'u': {'master': 'a', 'reason': 'x', 'ports': {'o': [[0, 15]]}}}}))
            rc, r = run(opn, ['--pad-file', str(pf)])
            self.assertEqual(rc, 0, r['summary'])                   # a fully declared open output port is spare
            pf.write_text(json.dumps({'instances': {'u': {'master': 'a', 'reason': 'x', 'ports': {'o': [[1, 15]]}}}}))
            rc, r = run(opn, ['--pad-file', str(pf)])
            self.assertEqual(r['summary']['output_open_ports'], 1)  # partly declared: still OUTPUT_OPEN

    def test_params_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            pj = Path(d) / 'p.json'
            pj.write_text(json.dumps({'masters': {'a': {'N': 1, '_source': 'test'}}}))
            rc, r = run("module top (ck);\n  input ck;\n  wire [7:0] n1;\n  wire [7:0] n2;\n"
                        "  a u0 (.ck(ck), .i(n2), .o(n1), .en(ck));\n  a u1 (.ck(ck), .i(n1), .o(n2), .en(ck));\nendmodule\n",
                        ('--params', str(pj)))
            self.assertEqual(rc, 0, r['summary'])


if __name__ == '__main__':
    unittest.main()


def test_ternary_packed_range_width():
    # qfd_collective_static_io_production relay_ck: the msb:lsb colon is the one outside the conditional
    import die_port_bind as P
    assert P._parse_ranges('[((2*(2*RU+RS0+RS1+RS2)>0)?2*(2*RU+RS0+RS1+RS2):1)-1:0]') == [
        ('((2*(2*RU+RS0+RS1+RS2)>0)?2*(2*RU+RS0+RS1+RS2):1)-1', '0')]
    src = ('module m #(parameter integer RU=5,RS0=0,RS1=0,RS2=5)(input wire[((2*(2*RU+RS0+RS1+RS2)>0)?'
           '2*(2*RU+RS0+RS1+RS2):1)-1:0]relay_ck, input wire [7:0] a); endmodule\n')
    m = P.parse_modules(src, 'x.sv')[0]
    assert m.width('relay_ck', m.env()) == 30 and m.width('a', m.env()) == 8


# ---- S81-LBGAP G6 (10-18): generate-label children, elaboration traps, duplicated child definitions
G6_P = """
module p #(parameter integer K = 1) (input wire ck, input wire [7:0] i, output wire [7:0] o);
  generate if (K == 1) begin : g_one
    c #(.RNE(1)) u_c (.ck(ck), .i(i), .o(o));
  end else begin : g_bad
    p_K_must_be_1 u_trap ();
  end endgenerate
endmodule
"""
G6_C_BASE = "module c (input wire ck, input wire [7:0] i, output reg [7:0] o); always @(posedge ck) o <= i; endmodule\n"
G6_C_RNE = ("module c #(parameter integer RNE = 0) (input wire ck, input wire [7:0] i, output reg [7:0] o);\n"
            "  always @(posedge ck) o <= RNE ? ~i : i; endmodule\n")
G6_DIE = "module die (ck);\n  input ck;\n  wire [7:0] n;\n  p u_p (.ck(ck), .i(n), .o(n));\nendmodule\n"


def run_g6(extra_fn=lambda d: []):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / 'rtl').mkdir()
        (d / 'rtl' / 'p.sv').write_text(G6_P)
        (d / 'rtl' / 'c.sv').write_text(G6_C_BASE)
        (d / 'rtl' / 'c_rne.sv').write_text(G6_C_RNE)
        (d / 'bench.f').write_text(f"+define+X\n{d / 'rtl' / 'c_rne.sv'}\n")
        (d / 'd.v').write_text(G6_DIE)
        out = d / 'o.json'
        p = subprocess.run([sys.executable, str(TOOL), str(d / 'd.v'), '--top', 'die', '--rtl-root', str(d / 'rtl'),
                            '--no-macro-dirs', '--out', str(out)] + list(extra_fn(d)), capture_output=True, text=True)
        return p.returncode, json.loads(out.read_text()), p.stdout


class G6(unittest.TestCase):
    def test_label_child_trap_and_ambiguous_child(self):
        rc, rec, so = run_g6()
        cc = rec['child_closure']
        self.assertEqual(rc, 1)
        self.assertIn('ambiguous_children', rec['failing'])
        self.assertIn('c', cc['ambiguous_children'])                 # the child after `begin : g_one` is seen
        self.assertEqual(cc['unresolved_children'], {})              # the port-less trap is not an unresolved child
        self.assertIn('p_K_must_be_1', cc['elab_traps'])

    def test_prefer_list_resolves(self):
        rc, rec, so = run_g6(lambda d: ['--prefer-list', str(d / 'bench.f')])
        cc = rec['child_closure']
        self.assertEqual(rc, 0, so)
        self.assertEqual(cc['ambiguous_children'], {})
        self.assertTrue(cc['variant_children']['c']['chosen'].endswith('c_rne.sv'))
        self.assertEqual(cc['variant_children']['c']['by'], 'prefer')

