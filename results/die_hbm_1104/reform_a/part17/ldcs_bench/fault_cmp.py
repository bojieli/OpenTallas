#!/usr/bin/env python3
"""Replace the lane0_fault port compare in tb.sv with per-source compares (fault_r = OR of the stage fault flags,
each source later by its own stage shift).  fault_cmp.py TB MAP.json"""
import json, sys
tb, mp = sys.argv[1], json.load(open(sys.argv[2]))
DM, DA, MUT = mp['DM'], mp['DA'], mp['MUT']
src = {'f_m1': DM, 'f_m2': 2 * DM, 'f_q': 2 * DM, 'f_ad': 2 * DM + DA, 'f_e1m': 3 * DM + DA, 'f_e1a': 2 * DM + 2 * DA,  # E1 add: starts at E1 in, waits after (MLAT > ALAT)
      
       'f_e2': 4 * DM + DA, 'f_d1': 0, 'f_sfu': 0}
if MUT == 6: src['f_e2'] -= 1           # mutant: one fault source declared one edge early
L = open(tb).read().split('\n')
out = []
for l in L:
    if 'lane0_fault' in l and ('for (int b' in l or 'checks++' in l):
        continue
    if l.strip() == 'endmodule':
        P = 'u_ref.u_lane0.u_lane.', 'u_dut.u.u_lane0.u_lane.'
        for s, k in src.items():
            out.append(f'  wire fr_{s} = {P[0]}{s}; wire fd_{s} = {P[1]}{s}; integer fn_{s} = 0;')
            if k:
                out.append(f'  logic fh_{s} [0:{k-1}];')
                out.append(f'  always @(posedge clk0) begin fh_{s}[0] <= fr_{s};' + ''.join(f' fh_{s}[{i}] <= fh_{s}[{i-1}];' for i in range(1, k)) + ' end')
            ref = f'fh_{s}[{k-1}]' if k else f'fr_{s}'
            out.append(f'  always @(posedge clk0) if (cyc > 200) begin checks++; fn_{s} += fr_{s}; if ({ref} !== fd_{s}) begin errs++;'
                       f' if (errs <= 10) $display("MISMATCH cyc=%0d {s} ref=%b dut=%b", cyc, {ref}, fd_{s}); end end')
        out.append('  final $display("FAULT_SRC_PULSES ' + ' '.join(f'{s}=%0d' for s in src) + '", ' + ', '.join(f'fn_{s}' for s in src) + ');')
    out.append(l)
open(tb, 'w').write('\n'.join(out))
