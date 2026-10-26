#!/usr/bin/env python3
"""TOK-HBM-SUV 2026-10-26: lock-step tb, split assembly vs its unsplit master (same ports; from harden/gen_split_tb.py).
gen_lockstep_tb.py PARENT.v REF_TOP 'k=v,..' OUT.sv     (DUT module = `SUV_DUT define)
every clk* input = one clock; rst_n and every rst*_n input bit low 16 cycles then common random reset segments
(every 997 cycles, 8 low); *_v / *_we / *_done strobes 1/dens dense, other inputs uniformly random; ALL outputs compared
(!==) every cycle after reset.  +cycles= +seed= +dens= plusargs.  Prints LOCKSTEP PASS|FAIL ... cycles=N errors=E."""
import re, sys
par, ref, prm, out = sys.argv[1:5]
txt = open(par).read()
hdr = txt[:txt.index(');', txt.index('module elab_top'))] if False else txt[:2000000]
ports = []
for m in re.finditer(r'^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s*)?([A-Za-z_]\w*)\s*;', hdr, re.M):
    ports.append((m.group(1), int(m.group(2)) - int(m.group(3)) + 1 if m.group(2) else 1, m.group(4)))
    if len(ports) > 400:
        break
P = ', '.join(f'.{k}({v})' for k, v in (x.split('=') for x in prm.split(',') if x))
isrst = lambda n: n == 'rst_n' or (n.startswith('rst') and n.endswith('_n'))
L = ['`timescale 1ns/1ps', 'module tb_suv_lockstep;', '  reg clk = 0; reg rst = 0; integer cyc = 0, errs = 0, seed = 1, ncyc = 4000, dens = 8, nzo = 0;',
     '  reg [31:0] r;']
for d, w, n in ports:
    if d == 'input':
        if n.startswith('clk'):
            L.append(f'  wire [{w-1}:0] {n} = {{{w}{{clk}}}};')
        elif isrst(n):
            L.append(f'  wire [{w-1}:0] {n} = {{{w}{{rst}}}};')
        else:
            L.append(f'  reg [{w-1}:0] {n} = 0;')
    else:
        L.append(f'  wire [{w-1}:0] ref_{n}, dut_{n};')
conn = lambda pfx: ',\n    '.join(f'.{n}({(pfx + n) if d == "output" else n})' for d, w, n in ports)
L.append(f'  {ref} #({P}) u_ref (\n    {conn("ref_")});')
L.append(f'  `SUV_DUT u_dut (\n    {conn("dut_")});')
L.append('  always #1 clk = ~clk;')
L.append('  task automatic drive; begin')
for d, w, n in ports:
    if d != 'input' or n.startswith('clk') or isrst(n):
        continue
    if w == 1 or re.search(r'(_v|_we|_done|_re)$', n):
        L.append(f'    {n} = {{{w}{{1\'b0}}}}; for (int i = 0; i < {w}; i++) {n}[i] = ($urandom % dens) == 0;')
    else:
        L.append(f'    for (int i = 0; i < {w}; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < {w}; j++) {n}[i+j] = r[j]; end')
L.append('  end endtask')
L.append('  initial begin')
L.append('    if ($value$plusargs("seed=%d", seed)) ; if ($value$plusargs("cycles=%d", ncyc)) ; if ($value$plusargs("dens=%d", dens)) ;')
L.append('    r = $urandom(seed);')
L.append('  end')
L.append('  always @(posedge clk) begin cyc <= cyc + 1;')
L.append('    if (cyc == 16) rst <= 1; else if (cyc > 16 && (cyc % 997) == 0) rst <= 0; else if ((cyc % 997) == 8) rst <= 1;')
L.append('    drive();')
L.append('    if (cyc >= ncyc) begin $display("LOCKSTEP %s seed=%0d dens=%0d cycles=%0d errors=%0d nonzero_out_cycles=%0d", errs ? "FAIL" : "PASS", seed, dens, cyc, errs, nzo); $finish; end')
L.append('  end')
L.append('  always @(negedge clk) if (cyc > 18) begin')
outs = [n for d, w, n in ports if d == 'output']
L.append('    if (' + ' || '.join(f'|ref_{n}' for n in outs) + ') nzo = nzo + 1;')
for n in outs:
    L.append(f'    if (ref_{n} !== dut_{n}) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d {n}", cyc); end')
L.append('  end')
L.append('endmodule')
open(out, 'w').write('\n'.join(L) + '\n')
print(len(ports), 'ports')
