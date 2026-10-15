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
