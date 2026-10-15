#!/usr/bin/env python3
"""fill2_relay_bench.py <rtl.sv> <module> <pass|mut_payload|mut_noreset> <out>: exact bench of a generated S81 die
relay-row master (dsfd_qbank_N/S: every output bus = its input bus registered once on ck, async reset rs -> 0).
The bench derives the in->out pairs from the RTL (r_<x> <= <in>; assign <out> = r_<x>), drives 4000 random words on
every input with reset pulses, and checks every output bit at every edge against the 1-edge-delayed input (0 during and
right after reset).  Mutants are DUT copies: mut_payload flips bit 0 of the first relayed bus, mut_noreset drops the
reset of the first register.  Prints "RELAY BENCH PASS <mode> ..." or "RELAY BENCH FAIL <mode> ..."."""
import re, subprocess, sys, os, random
from pathlib import Path
src, mod, mode, out = sys.argv[1:5]
out = Path(out); out.mkdir(parents=True, exist_ok=True)
txt = Path(src).read_text()
body = re.search(r'^module %s \((.*?)^endmodule' % mod, txt, re.S | re.M).group(0)
ports = re.findall(r'(input|output) wire \[(\d+):0\] (\w+)', body)
regs = re.findall(r'(\w+) <= (\w+);', body)          # r_x <= in
asg = dict((r, o) for o, r in re.findall(r'assign (\w+) = (\w+);', body))
pairs = [(i, asg[r], int(dict((p[2], p[1]) for p in ports)[i]) + 1) for r, i in regs if r in asg]
assert pairs, 'no relay pairs'
dut = body
if mode == 'mut_payload':
    r0, i0 = regs[0]
    dut = dut.replace(f'{r0} <= {i0};', f'{r0} <= {i0} ^ 1;', 1)
elif mode == 'mut_noreset':
    r0, i0 = regs[0]
    dut = re.sub(r'always @\(posedge ck\[0\] or negedge rs\[0\]\) if \(!rs\[0\]\) %s <= [^;]+; else %s <= %s;' % (r0, r0, i0),
                 f'always @(posedge ck[0]) {r0} <= {i0};', dut, count=1)
assert mode == 'pass' or dut != body, 'mutant not applied'
(out / 'dut.sv').write_text(dut)
decl = '\n'.join(f'  reg [{w-1}:0] {i}; wire [{w-1}:0] {o}; reg [{w-1}:0] exp_{o};' for i, o, w in pairs)
conn = ', '.join([f'.{i}({i})' for i, o, w in pairs] + [f'.{o}({o})' for i, o, w in pairs] + ['.ck(ck)', '.rs(rs)'])
rnd = '\n'.join(f'      {i} = {{' + ','.join(['$urandom'] * ((w + 31) // 32)) + '};' for i, o, w in pairs)
chk = '\n'.join(f'      if ({o} !== exp_{o}) begin errs = errs + 1; if (errs < 5) $display("MISMATCH %0d {o} got %h exp %h", cyc, {o}, exp_{o}); end' for i, o, w in pairs)
upd = '\n'.join(f'      exp_{o} = rs ? {i} : 0;' for i, o, w in pairs)
z = '\n'.join(f'      exp_{o} = 0;' for i, o, w in pairs)
tb = f'''`timescale 1ns/1ps
module tb;
  reg ck = 0; reg rs = 0; integer cyc, errs, checks;
{decl}
  {mod} dut ({conn});
  always #0.4166 ck = ~ck;
  initial begin
    errs = 0; checks = 0;
{z}
{rnd}
    repeat (3) @(negedge ck);
    rs = 1;
    for (cyc = 0; cyc < 4000; cyc = cyc + 1) begin
      if (cyc == 1500 || cyc == 2900) rs = 0;
      if (cyc == 1503 || cyc == 2902) rs = 1;
{rnd}
      @(posedge ck); #0.05;
{upd}
      @(negedge ck);
{chk}
      checks = checks + 1;
    end
    if (errs == 0) $display("RELAY BENCH PASS {mode} {mod} checks=%0d pairs={len(pairs)} bits={sum(w for _,_,w in pairs)} resets=2", checks);
    else $display("RELAY BENCH FAIL {mode} {mod} errors=%0d", errs);
    $finish;
  end
endmodule
'''
(out / 'tb.sv').write_text(tb)
r = subprocess.run(['iverilog', '-g2012', '-o', str(out / 'sim'), str(out / 'dut.sv'), str(out / 'tb.sv')], capture_output=True, text=True)
if r.returncode:
    print(r.stdout + r.stderr); print(f'RELAY BENCH BUILD_FAIL {mode}'); sys.exit(1)
r = subprocess.run(['vvp', '-n', str(out / 'sim')], capture_output=True, text=True)
print(r.stdout[-2000:])
sys.exit(0 if f'RELAY BENCH PASS {mode}' in r.stdout else 1)
