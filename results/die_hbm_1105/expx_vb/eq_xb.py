#!/usr/bin/env python3
"""DIE-HBM-77-EXPX vB bench generator: old exp_x (+ sfu_s, part-18 composition) vs vB exp_x (+ the same sfu_s), lock-step.
Same inputs on both sides every edge (vB delays its own control fields).  Checks:
  write / reducer outputs (vm_*, kv_*, ro_*)  dut[t] == ref[t - T] (data under its valid), T = 5
  lane_fault, lane_coll                       dut[t] == ref[t - T] exactly
  fetch / bank outputs                        dut[t] == ref[t]
  f_sfu (seam fault net inside the lane)      dut[t] == ref[t - S], S = 3, and pulses must occur
Epochs of one ci/cs kind (0 none, 1 exp, 4 sigmoid, 5 SiLU) with drains; second half forces R to a signalling NaN.
    eq_xb.py SPLITX.sv OUT_tb.sv [EPOCHS] [LANE_ID]"""
import re, sys
src, out = sys.argv[1:3]; EP = int(sys.argv[3]) if len(sys.argv) > 3 else 40; LID = int(sys.argv[4]) if len(sys.argv) > 4 else 77
T, S, DRAIN, LEN = 5, 3, 400, 600
KINDS = [0, 1, 4, 5, 0, 5, 1, 4]
hdr = src_txt = open(src).read()
hdr = hdr[hdr.index('module ot_hbm_su_pg_lane_exp_core__splitx'):hdr.index(');')]
ports = {}
for m in re.finditer(r'(input|output) wire (?:\[(\d+):0\] )?(\w+)', hdr):
    ports[m.group(3)] = (m.group(1), int(m.group(2) or 0) + 1)
clks = [n for n in ports if re.search(r'(^|_)clk(_|$)', n)]
rsts = [n for n in ports if n.endswith('rst_n')]
ins = [n for n, (d, w) in ports.items() if d == 'input' and n not in clks and n not in rsts]
outs = [n for n, (d, w) in ports.items() if d == 'output']
post = 'lane_vm_we lane_vm_waddr lane_vm_wdata lane_kv_we lane_kv_waddr lane_kv_wdata lane_ro_v lane_ro_x lane_fault lane_coll'.split()
QUAL = {'lane_vm_waddr': 'lane_vm_we', 'lane_vm_wdata': 'lane_vm_we', 'lane_kv_waddr': 'lane_kv_we', 'lane_kv_wdata': 'lane_kv_we',
        'lane_ro_x': 'lane_ro_v'}
W = lambda n: ports[n][1]
L = ['`timescale 1ns/1ps', '`default_nettype none', 'module tb;']
for c in clks: L.append(f'  logic [{W(c)-1}:0] {c} = \'0;')
for r in rsts: L.append(f'  logic [{W(r)-1}:0] {r} = \'0;')
for n in ins: L.append(f'  logic [{W(n)-1}:0] {n}_r = \'0;')
for n in outs:
    L.append(f'  wire [{W(n)-1}:0] {n}_ref, {n}_dut;')
    if n in post: L.append(f'  logic [{W(n)-1}:0] {n}_h[0:{T-1}];')
L += ['  logic [2:0] kind = 0; logic drain = 1; logic cmp = 0;', f'  logic [{S-1}:0] sr = \'0;', '  longint sp = 0, sd = 0;']
def inst(mod, name, sfx, par):
    a = [f'.{c}({c})' for c in clks] + [f'.{r}({r})' for r in rsts] + [f'.{n}({n}_r)' for n in ins] + [f'.{n}({n}_{sfx})' for n in outs]
    return f'  {mod} #(.MUT({par})) {name} (' + ', '.join(a) + ');'
L += [inst('ot_hbm_su_pg_lane_exp_core__splitx', 'u_ref', 'ref', '0'), inst('ot_hbm_su_pg_lane_exp_core__splitx_vb', 'u_dut', 'dut', '`OT_MUT')]
def rnd(w):
    k = (w + 31) // 32
    return '{' + ','.join(['$urandom'] * k) + '}' if k > 1 else '$urandom'
L += ['  longint checks = 0, errs = 0, wr = 0, fp = 0, cp = 0; int ep = 0, cyc = 0;',
      '  task automatic bad(input string n); errs++; if (errs < 12) $display("MISMATCH %s cyc=%0d ep=%0d kind=%0d", n, cyc, ep, kind); endtask',
      '  always #0.5 begin'] + [f'    {c} = ~{c};' for c in clks] + ['  end', f'  always @(posedge {clks[0]}[0]) begin', '    cyc <= cyc + 1;']
for n in ins:
    if n == 'lane_lane_id': L.append(f'    {n}_r <= {W(n)}\'d{LID};')
    elif n in ('lane_ci_sfu', 'lane_cs_sfu'): L.append(f'    {n}_r <= kind;')
    elif n == 'lane_emit': L.append(f'    {n}_r <= drain ? 1\'b0 : $urandom;')
    else: L.append(f'    {n}_r <= {rnd(W(n))};')
for n in post: L.append(f'    {n}_h[0] <= {n}_ref; for (int i = 1; i < {T}; i++) {n}_h[i] <= {n}_h[i-1];')
SR = 'u_ref.u_l.u_fcore.u_lane.u_lane.f_sfu'; SD = 'u_dut.u_l.u_fcore.u_lane.u_lane.f_sfu'
L += [f'    sr <= {{sr[{S-2}:0], {SR}}};', '    if (cmp) begin', f'      if ({SR}) sp++; if ({SD}) sd++;',
      f'      if ({SD} !== sr[{S-1}]) bad("f_sfu");']
for n in outs:
    if n in post:
        q = QUAL.get(n); rv = f'{q}_h[{T-1}]' if q else "1'b1"
        L.append(f'      checks++; if ({rv} && {n}_dut !== {n}_h[{T-1}]) bad("{n}");')
    else:
        L.append(f'      checks++; if ({n}_dut !== {n}_ref) bad("{n}");')
L += ['      if (|lane_vm_we_ref) wr++; if (|lane_fault_ref) fp++; if (|lane_coll_ref) cp++;', '    end', '  end',
      '  initial begin'] + [f'    {r} = \'0;' for r in rsts] + [f'    repeat (20) @(posedge {clks[0]}[0]);'] + [f'    {r} = \'1;' for r in rsts]
L += [f'    repeat ({DRAIN}) @(posedge {clks[0]}[0]);', f'    for (ep = 0; ep < {EP}; ep++) begin',
      f'      kind = kinds[ep % {len(KINDS)}];', f'      repeat ({DRAIN}) @(posedge {clks[0]}[0]);',
      f'      if (ep >= {EP//2}) begin force {SR[:-5]}R = 32\'h7f800001; force {SD[:-5]}R = 32\'h7f800001; end',
      '      cmp = 1; drain = 0;', f'      repeat ({LEN}) @(posedge {clks[0]}[0]);', '      drain = 1;',
      f'      repeat ({DRAIN}) @(posedge {clks[0]}[0]);', '      cmp = 0;', f'      release {SR[:-5]}R; release {SD[:-5]}R;', '    end',
      '    $display("XEQ %s checks=%0d errs=%0d writes=%0d fault_cycles=%0d coll_cycles=%0d sfu_fault_ref=%0d sfu_fault_dut=%0d", '
      '(errs == 0 && wr > 0 && sp > 0 && fp > 0) ? "PASS" : "FAIL", checks, errs, wr, fp, cp, sp, sd);', '    $finish;', '  end',
      f'  int kinds[0:{len(KINDS)-1}] = \'{{' + ','.join(map(str, KINDS)) + '};', 'endmodule', '`default_nettype wire']
open(out, 'w').write('\n'.join(L) + '\n')
print('ins', len(ins), 'outs', len(outs), 'clks', clks, 'rsts', rsts)
