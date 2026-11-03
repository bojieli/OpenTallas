#!/usr/bin/env python3
"""DIE-HBM-61/SPLIT: facewrap.py regression -- a top with its own processes (always blocks) + a parameter, with and
without its child on the file list (--no-hier).  Run: python3 test_facewrap.py (needs the opentallas yosys)."""
import json, os, subprocess, sys, tempfile
H = os.path.dirname(os.path.abspath(__file__))
TOP = """module child (input wire clk, input wire [3:0] d, output reg [3:0] q); always @(posedge clk) q <= d; endmodule
module tproc #(parameter integer MUT = 0) (input wire clk, input wire rst_n, input wire [7:0] a, output reg [7:0] y, output wire [3:0] z);
    reg [7:0] r; always @(posedge clk or negedge rst_n) if (!rst_n) r <= 0; else r <= a + MUT;
    always @(posedge clk) y <= r;
    child u_c (.clk(clk), .d(a[3:0]), .q(z));
endmodule
"""
def run(extra, src):
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, 't.sv'); open(f, 'w').write(src); o = os.path.join(td, 'o.sv')
        r = subprocess.run([sys.executable, os.path.join(H, 'facewrap.py'), '--top', 'tproc', '--out', o, '--pass-param', 'MUT'] + extra + [f],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        p = json.loads(r.stdout); sv = open(o).read()
    assert p['clk'] == ['clk'] and p['rst'] == ['rst_n'], p
    assert p['ports'] == {'clk': ['input', 1], 'rst_n': ['input', 1], 'a': ['input', 8], 'y': ['output', 8], 'z': ['output', 4]}, p
    assert 'u_bin_a' in sv and 'u_bout_y' in sv and 'u_bout_z' in sv and 'u_bin_rst_n' not in sv and '#(.MUT(MUT))' in sv, sv
run([], TOP)                                              # full hierarchy, top with processes
run(['--no-hier'], TOP.split('\n', 1)[1])                 # child missing: --no-hier reads the top only
print('test_facewrap PASS')
