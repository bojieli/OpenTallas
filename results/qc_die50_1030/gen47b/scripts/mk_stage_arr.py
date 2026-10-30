#!/usr/bin/env python3
"""DIE-QC-50/gen47b: stage-clock-pin arrival rows for start_stage_emit proof from a MEASURED OT_EDGES v1 readout.
Each provider stage clock port t_st_*__clk is bound (bindings.json) to ck_<net> whose single driver is ck_<cell>/Y; its
arrival = that driver's measured N/M row (source rise/fall at the driver output pin) -> T/F rows for the port.
Basis caveat (written into the census): the readout must come from a DB in which the provider loads exist, otherwise the
leaf FF pin load + leaf wire are NOT included (driver-pin arrival on the pre-import tree).
Slew: max(rise,fall) output slew of the driver cell from the same run's edges_raw C row (conservative).
usage: mk_stage_arr.py ARR_IN STAGES BINDINGS ARR_OUT CENSUS EDGES_RAW"""
import json, sys
src, stages, binds, out, cen, raw = sys.argv[1:7]
SL = {}
for ln in open(raw):
    f = ln.split()
    if f and f[0] == 'C' and f[3] != 'NA': SL[f[1][3:]] = max(float(f[7]), float(f[8]))
N, M = {}, {}; lines = open(src).read().splitlines()
for ln in lines:
    f = ln.split()
    if f and f[0] in 'NM': (N if f[0] == 'N' else M)[f[1]] = f[2:4]
B = json.load(open(binds))['ports']; st = json.load(open(stages))['stages']; add = []; bad = []
for s in st:
    drv = B[s['clock_port']]['native_endpoints'][0]['inst']; cell = drv[3:]
    if cell != s.get('clock_source_cell', s['node_cell']): bad.append((s['id'], cell, s.get('clock_source_cell')))
    if cell not in N or cell not in M: bad.append((s['id'], cell, 'no measured row')); continue
    add += [f"T {s['clock_port']} {N[cell][0]} {N[cell][1]} {SL[cell]}", f"F {s['clock_port']} {M[cell][0]} {M[cell][1]}"]
if bad: raise SystemExit('HOLD %d %s' % (len(bad), bad[:5]))
open(out, 'w').write('\n'.join(lines + add) + '\n')
r = dict(src=src, edges_raw=raw, max_stage_slew_ps=max(SL[B[x['clock_port']]['native_endpoints'][0]['inst'][3:]] for x in st), stages=len(st), rows_added=len(add)); json.dump(r, open(cen, 'w')); print(json.dumps(r))
