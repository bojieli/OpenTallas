#!/usr/bin/env python3
"""HBM-GAPS-5-L1P lane1p latency-shift lock-step bench generator.
ref = main ot_hbm_su_pg_lane1p_core (MLAT 4, ALAT 3, no LDCS; modules renamed __ref)
dut = branch ot_hbm_su_pg_lane1p_core with #(MLAT, ALAT, LDCS) inside a wrapper that delays each per-stage
      control input by the stage shift (the controller pipe delivers it that many edges later), outputs compared
      dut[t] == ref[t - k] with the declared output shift k.
mk_bench.py SRC OUT MLAT ALAT LDCS DM DA LANE_ID CYC [MUT]
  DM/DA = declared extra multiplier / adder edges (pin cycles), MUT: 0 none, 3 output shift - 1, 4 cm_* not delayed, 6 f_e2 fault shift - 1,
  5 ALAT not declared (DA forced 0)."""
import json, re, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
MLAT, ALAT, LDCS, DM, DA, LID, CYC = sys.argv[3:10]; MUT = int(sys.argv[10]) if len(sys.argv) > 10 else 0
DM, DA, CYC = int(DM), int(DA), int(CYC)
if MUT == 5: DA = 0
T = 'ot_hbm_su_pg_lane1p_core'
# ref: rename the three changed modules
ren = [('ot_hbm_su_pg_lane1p_core', 'ot_hbm_su_pg_lane1p_core__ref'),
       ('ot_hbm_su_static_lane_pinreg', 'ot_hbm_su_static_lane_pinreg__ref'),
       ('ot_hbm_su_static_lane', 'ot_hbm_su_static_lane__ref')]
for f in ['ot_hbm_su_pg_lane1p_core.sv', 'ot_hbm_su_static_lane.sv', 'ot_hbm_su_static_lane_pinreg.sv']:
    t = (src / 'old' / f).read_text()
    for a, b in ren:
        t = re.sub(r'\b%s\b' % a, b, t)
    (out / ('ref_' + f)).write_text(t)
# ports of the core
txt = (src / 'new' / f'{T}.sv').read_text()
hdr = txt[txt.index(f'module {T}'):txt.index(');')]
ports = {}
for m in re.finditer(r'(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)', hdr):
    ports[m.group(3)] = [m.group(1), int(m.group(2)) + 1 if m.group(2) else 1]
clocks = [n for n in ports if re.search(r'(^|_)clk(_|$)', n)]
resets = [n for n in ports if n.endswith('rst_n')]
# input delay per port (edges): stage where the lane consumes it (ot_hbm_su_static_lane per-stage control)
d = {}
for n in ports:
    s = n.split('_', 1)[1] if n.startswith('lane0_') else ''
    if s.startswith('cm_'): d[n] = DM                  # at M1 out
    elif s.startswith('ca_'): d[n] = 2 * DM            # at AD in (after M2)
    elif s.startswith('ci_') or s.startswith('cs_') or s == 'side_y': d[n] = 2 * DM + DA   # at S in / out
    elif s.startswith('ce_'): d[n] = 3 * DM + DA       # at E2 in (after E1)
    elif s.startswith('co_'): d[n] = 4 * DM + DA       # at OUT in
if MUT == 4:
    for n in list(d):
        if n.startswith('lane0_cm_'): d[n] = 0
kout = 4 * DM + DA - (1 if MUT == 3 else 0)
shift = {n: kout for n in ports if ports[n][0] == 'output' and re.match(r'lane0_(vm_|kv_|ro_)', n)}
# DUT wrapper
L = ['`timescale 1ns/1ps', '`default_nettype none', f'module {T}__dutw (']
L.append(',\n'.join(f'    {ports[n][0]} wire [{ports[n][1]-1}:0] {n}' for n in ports))
L.append(');')
ck = clocks[0] if 'bank0_clk' not in ports else 'bank0_clk'
conn = []
for n, (dr, w) in ports.items():
    k = d.get(n, 0)
    if dr == 'input' and k:
        L.append(f'    reg [{w-1}:0] dl_{n} [0:{k-1}];')
        L.append(f'    always @(posedge {ck}) begin dl_{n}[0] <= {n};' + ''.join(f' dl_{n}[{i}] <= dl_{n}[{i-1}];' for i in range(1, k)) + ' end')
        conn.append(f'.{n}(dl_{n}[{k-1}])')
    else:
        conn.append(f'.{n}({n})')
L.append(f'    {T} #(.MLAT({MLAT}), .ALAT({ALAT}), .LDCS({LDCS})) u (' + ', '.join(conn) + ');')
L.append('endmodule')
(out / 'dutw.sv').write_text('\n'.join(L) + '\n')
spec = dict(ref=T + '__ref', dut=T + '__dutw', ports=ports, clocks=clocks, resets=resets, reset_cycles=12, warmup=200,
            cycles=CYC, stim={}, hold={'lane0_lane_id': LID}, shift=shift)
json.dump(spec, open(out / 'spec.json', 'w'), indent=1)
json.dump(dict(MLAT=MLAT, ALAT=ALAT, LDCS=LDCS, DM=DM, DA=DA, MUT=MUT, in_delay=d, out_shift=shift), open(out / 'map.json', 'w'), indent=1)
print('in_delay', {k: v for k, v in d.items() if v}, 'out_shift', kout)
