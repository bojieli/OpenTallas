#!/usr/bin/env python3
"""PATH-HBM/Q3 (2026-10-25): lock-step bench of a split assembly vs its master (same port list, master params).
gen_tb.py PARENT.v REF_TOP 'k=v,..' ASM_TOP OUT.sv  -- every clk* input = one clock; rst_n low 16 cycles then random
reset segments; *_v / *_we / launch strobes 1/8 dense, other inputs uniformly random; ALL outputs compared each cycle."""
import re, sys
par, ref, prm, asm, out = sys.argv[1:6]
txt = open(par).read()
hdr = txt
ports = []
for m in re.finditer(r'^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s*)?([A-Za-z_]\w*)\s*;', hdr, re.M):
    ports.append((m.group(1), int(m.group(2)) - int(m.group(3)) + 1 if m.group(2) else 1, m.group(4)))
P = ', '.join(f'.{k}({v})' for k, v in (x.split('=') for x in prm.split(',') if x))
L = ['`timescale 1ns/1ps', 'module tb;', '  reg clk = 0; reg [3:0] mut = 0; integer cyc = 0, errs = 0, seed = 1, ncyc = 4000, dens = 8;',
     '  reg [31:0] r;']
for d, w, n in ports:
    if d == 'input':
        if n.startswith('clk'):
            L.append(f'  wire [{w-1}:0] {n} = {{{w}{{clk}}}};')
        else:
            L.append(f'  reg [{w-1}:0] {n} = 0;')
    else:
        L.append(f'  wire [{w-1}:0] ref_{n}, dut_{n};')
def conn(pfx):
    return ',\n    '.join(f'.{n}({(pfx + n) if d == "output" else n})' for d, w, n in ports)
L.append(f'  {ref} #({P}) u_ref (\n    {conn("ref_")});')
L.append(f'  {asm} u_dut (.lockstep_mut(mut),\n    {conn("dut_")});')
L.append('  always #1 clk = ~clk;')
L.append('  task automatic drive; begin')
for d, w, n in ports:
    if d != 'input' or n.startswith('clk') or n == 'rst_n':
        continue
    if w == 1 or re.search(r'(_v|_we|launch_v|phy_up)$', n):
        L.append(f'    {n} = {{{w}{{1\'b0}}}}; for (int i = 0; i < {w}; i++) {n}[i] = ($urandom % dens) == 0;')
    else:
        L.append(f'    for (int i = 0; i < {w}; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < {w}; j++) {n}[i+j] = r[j]; end')
L.append('  end endtask')
L.append('  initial begin')
L.append('    if ($value$plusargs("seed=%d", seed)) ; if ($value$plusargs("mut=%d", mut)) ; if ($value$plusargs("cycles=%d", ncyc)) ;')
L.append('    if ($value$plusargs("dens=%d", dens)) ; r = $urandom(seed); rst_n = 0; qid = 0;')
L.append('  end')
L.append('  always @(posedge clk) begin cyc <= cyc + 1;')
L.append('    if (cyc == 16) rst_n <= 1; else if (cyc > 16 && (cyc % 997) == 0) rst_n <= 0; else if ((cyc % 997) == 8) rst_n <= 1;')
L.append('    drive();')
L.append('    if (cyc >= ncyc) begin $display("LOCKSTEP %s mut=%0d seed=%0d dens=%0d cycles=%0d errors=%0d", errs ? "FAIL" : "PASS", mut, seed, dens, cyc, errs); $finish; end')
L.append('  end')
L.append('  always @(negedge clk) if (cyc > 2) begin')
for d, w, n in ports:
    if d == 'output':
        L.append(f'    if (ref_{n} !== dut_{n}) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d {n}", cyc); end')
L.append('  end')
L.append('endmodule')
open(out, 'w').write('\n'.join(L) + '\n')
print(len(ports), 'ports')
