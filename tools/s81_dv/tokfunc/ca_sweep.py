#!/usr/bin/env python3
"""ca_sweep.py -- TOK-VERIFY-1: the real ot_dp_clk_landing_ca over the receiver-minus-sender phase d (unwrapped).

One bench per (DEPTH, K): N copies of the cell, copy i has its receiver clock at phase d_i = D0 + i*STEP (ns) against the
sender clock (fclk = sender clock, forwarded with zero delay; t_rst_n forwarded with it).  Both sides start at the SAME
count index E (sender: t_rst_n sampled high at its edge E; receiver: rst_n sampled high at its edge E), i.e. equal count
origins a_u = a_v.  The sender writes word n = its count.  After every receiver edge c >= E + 40 the bench records
c - E - q (the offset; the cell's contract is q = word (c - K), so offset == K) plus ready / fault.
Prints per copy: d_ns, d/T, offset set, ready, fault.  Window claim (binder): lag L = K T + d in [0.5 T, (DEPTH-0.5) T].
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def tb(n, d0, step, depth, k, T=10.0):
    B = 100 * T     # both clocks start after B, so a negative d still has a first edge at t > 0
    v = ['`timescale 1ns/1ps', 'module tb;', '  localparam integer N = %d, E = 20;' % n,
         '  reg cks = 0; integer sc = -1; reg trst = 0;',
         f'  initial begin #({B + T/2}); forever begin cks = 1; sc = sc + 1; #({T/2}); cks = 0; #({T/2}); end end',
         '  always @(negedge cks) if (sc == E - 1) trst <= 1;',
         "  reg [15:0] word = 16'hffff; always @(negedge cks) if (sc >= E - 1) word <= sc - (E - 1);"]
    for i in range(n):
        d = d0 + i * step
        v += [f'  // copy {i}: d = {d:+.3f} ns (receiver edge j at sender edge j + d)',
              f'  reg ckr{i} = 0; integer rc{i} = -1; reg rr{i} = 0; wire [15:0] q{i}; wire rdy{i}, flt{i};',
              f'  initial begin #({B + T/2 + d:.3f}); forever begin ckr{i} = 1; rc{i} = rc{i} + 1; #({T/2}); ckr{i} = 0; #({T/2}); end end',
              f'  always @(negedge ckr{i}) if (rc{i} == E - 1) rr{i} <= 1;',
              f'  ot_dp_clk_landing_ca #(.W(16), .DEPTH({depth}), .K({k})) u{i} (.fclk(cks), .t_rst_n(trst), .clk(ckr{i}), '
              f'.rst_n(rr{i}), .d(word), .q(q{i}), .ready(rdy{i}), .fault(flt{i}));',
              f'  integer omin{i} = 99999, omax{i} = -99999, nr{i} = 0; integer o{i};',
              f'  always @(posedge ckr{i}) begin #0.01; if (rc{i} >= E + 40 && rc{i} < E + 400) begin',
              f'    o{i} = (rc{i} - E) - q{i}; if (o{i} < omin{i}) omin{i} = o{i}; if (o{i} > omax{i}) omax{i} = o{i};',
              f'    if (!rdy{i}) nr{i} = nr{i} + 1; end end']
    v.append(f'  initial begin #({B + 460 * T});')
    for i in range(n):
        d = d0 + i * step
        v.append(f'    $display("CA {i} %f %0d %0d %0d %0d", {d:.4f}, omin{i}, omax{i}, nr{i}, flt{i});')
    v += ['    $finish; end', 'endmodule']
    return '\n'.join(v) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ca', type=Path, nargs='+', required=True, help='ot_dp_clk_landing_ca.sv + its deps (ot_dp_clk_landing.sv, ot_meso_fifo.sv)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--depth', type=int, default=4)
    ap.add_argument('--k', type=int, default=3)
    ap.add_argument('--d0', type=float, default=-30.0)
    ap.add_argument('--step', type=float, default=0.5)
    ap.add_argument('--n', type=int, default=161)
    a = ap.parse_args()
    o = a.out.resolve()
    o.mkdir(parents=True, exist_ok=True)
    (o / 'tb.v').write_text(tb(a.n, a.d0, a.step, a.depth, a.k))
    for f in a.ca:
        (o / f.name).write_text(f.read_text())
    cmd = ['timeout', '1500', 'docker', 'run', '--rm', '--memory', '8g', '-u', f'{os.getuid()}:{os.getgid()}', '-e',
           'HOME=/w', '-e', 'CCACHE_DISABLE=1', '-v', f'{o}:/w', '-w', '/w', 'verilator/verilator:v5.032', '--binary',
           '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-j', '8', '--top-module', 'tb', 'tb.v'] + [f.name for f in a.ca] + ['-o', 'sim']
    r = subprocess.run(cmd, capture_output=True, text=True)
    (o / 'build.log').write_text(r.stdout + r.stderr)
    if r.returncode:
        sys.exit(f'build failed: {o}/build.log')
    r = subprocess.run([str(o / 'obj_dir' / 'sim')], capture_output=True, text=True, timeout=1800)
    (o / 'sim.log').write_text(r.stdout + r.stderr)
    for line in r.stdout.splitlines():
        if line.startswith('CA '):
            _, i, d, mn, mx, nr, f = line.split()
            print(f'd {float(d):+8.3f} ns  d/T {float(d)/10:+6.2f}  offset {mn}..{mx}  not_ready {nr}  fault {f}')


if __name__ == '__main__':
    main()
