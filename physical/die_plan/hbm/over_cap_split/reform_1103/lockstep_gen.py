#!/usr/bin/env python3
"""DIE-HBM-61/SPLIT 11-03: generic lock-step bench generator for RE-FORM splits (uncut core vs split composition).

    lockstep_gen.py SPEC.json OUT_tb.sv

SPEC = {
  "ref": "<uncut top (kit face-shelled form)>", "dut": "<split composition top (sub-blocks in face-shelled form)>",
  "ports": {name: ["input"|"output", width]},            # common port list (facewrap.py prints it)
  "clocks": [names], "resets": [names], "reset_active_low": true,
  "reset_cycles": 8, "warmup": 200, "cycles": 4000, "seed": 1,
  "stim": {port: "<SV expression, may use $urandom, cyc>"},  # default: $urandom bits every edge
  "shift": {output: k},                                   # declared cycle-shift map: dut out == ref out k edges earlier
  "hold": {port: "<expr held constant>"}
}
Every output is compared every edge after warmup (dut[t] vs ref[t - shift]); X/Z on ref skips the bit (4-state sims).
Prints  LOCKSTEP PASS checks=<n> toggles=<output bits that toggled>  or  LOCKSTEP FAIL <first mismatches>.
"""
import json, sys

S = json.load(open(sys.argv[1]))
P = S['ports']; clks = S.get('clocks', []); rsts = S.get('resets', [])
al = S.get('reset_active_low', True)
shift = S.get('shift', {}); stim = S.get('stim', {}); hold = S.get('hold', {})
outs = [n for n, (d, w) in P.items() if d == 'output']
ins = [n for n, (d, w) in P.items() if d == 'input' and n not in clks and n not in rsts]
W = lambda n: P[n][1]
dcl = lambda n: f'[{W(n)-1}:0] '
L = ['`timescale 1ns/1ps', '`default_nettype none', 'module tb;']
for c in clks:
    L.append(f'  logic {dcl(c)}{c};')
for r in rsts:
    L.append(f'  logic {dcl(r)}{r};')
for n in ins:
    L.append(f'  logic {dcl(n)}{n};')
for n in outs:
    L.append(f'  wire {dcl(n)}r_{n}, d_{n};')
    k = shift.get(n, 0)
    if k:
        L.append(f'  logic {dcl(n)}rh_{n} [0:{k-1}];')
conn = lambda pfx: ', '.join([f'.{c}({c})' for c in clks] + [f'.{r}({r})' for r in rsts] + [f'.{n}({n})' for n in ins] +
                             [f'.{n}({pfx}_{n})' for n in outs])
L.append(f"  {S['ref']} u_ref ({conn('r')});")
L.append(f"  {S['dut']} u_dut ({conn('d')});")
L.append('  integer cyc = 0, checks = 0, errs = 0, tog = 0; logic clk0 = 0;')
for c in clks:
    L.append(f"  always_comb {c} = {{{W(c)}{{clk0}}}};")
L.append('  always #1 clk0 = ~clk0;')
for n in outs:
    L.append(f'  logic {dcl(n)}last_{n}; logic {dcl(n)}tg_{n};')
L.append('  initial begin')
for n in outs:
    L.append(f"    tg_{n} = '0;")
L.append('  end')
# stimulus on negedge
L.append('  always @(negedge clk0) begin')
L.append('    cyc <= cyc + 1;')
rv = (lambda: "'0") if al else (lambda: "'1")
ra = (lambda: "'1") if al else (lambda: "'0")
for r in rsts:
    L.append(f"    {r} <= (cyc < {S.get('reset_cycles', 8)}) ? {rv()} : {ra()};")
for n in ins:
    if n in hold:
        L.append(f'    {n} <= {hold[n]};')
    elif n in stim:
        L.append(f'    {n} <= {stim[n]};')
    else:
        nw = (W(n) + 31) // 32
        L.append(f"    {n} <= {{{', '.join(['$urandom()'] * nw)}}};")
L.append('  end')
# compare on posedge (just before the edge: use #0.5 after negedge? compare at negedge-0 = sample at posedge+0.5)
L.append('  always @(posedge clk0) begin')
L.append(f"    if (cyc > {S.get('warmup', 200)}) begin")
for n in outs:
    k = shift.get(n, 0)
    ref = f'rh_{n}[{k-1}]' if k else f'r_{n}'
    L.append(f'      for (int b = 0; b < {W(n)}; b++) if ({ref}[b] !== 1\'bx && {ref}[b] !== d_{n}[b]) begin errs++;'
             f' if (errs <= 10) $display("MISMATCH cyc=%0d {n}[%0d] ref=%b dut=%b", cyc, b, {ref}[b], d_{n}[b]); end')
    L.append(f'      checks++; tg_{n} |= (r_{n} ^ last_{n});')
L.append('    end')
for n in outs:
    k = shift.get(n, 0)
    L.append(f'    last_{n} <= r_{n};')
    if k:
        L.append(f'    rh_{n}[0] <= r_{n};')
        for i in range(1, k):
            L.append(f'    rh_{n}[{i}] <= rh_{n}[{i-1}];')
L.append(f"    if (cyc == {S.get('cycles', 4000)}) begin")
L.append('      tog = 0;')
for n in outs:
    L.append(f'      tog += $countones(tg_{n});')
L.append('      if (errs == 0) $display("LOCKSTEP PASS checks=%0d toggled_out_bits=%0d", checks, tog);')
L.append('      else $display("LOCKSTEP FAIL errs=%0d checks=%0d toggled_out_bits=%0d", errs, checks, tog);')
L.append('      $finish;')
L.append('    end')
L.append('  end')
L.append('endmodule')
open(sys.argv[2], 'w').write('\n'.join(L) + '\n')
