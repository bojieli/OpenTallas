#!/usr/bin/env python3
"""DIE-QC-49/gen47: edges_raw.txt (grt_src.tcl, GRT-routed RC) -> OT_EDGES v1 arrivals for main trial_tap_arrivals.py.
Same polarity rule as DIE-QC-45 mk_edges.py (source-rise-derived transition = the EARLIER absolute arrival; the source
fall launches at T/2). Adds the measured source-fall rows (F/M = fall-derived arrival - T/2), FLOW-ONEMODEL-2.
usage: mk_edges47.py EDGES_RAW OUT_ARR OUT_CENSUS_JSON"""
import sys, json, collections
src, out, cen = sys.argv[1:4]
H = 833.0 / 2
C = collections.Counter(); odd_cells = 0; odd_taps = []; amb = []; rows = []; frows = []; na = 0
slews = []
for ln in open(src):
    f = ln.split()
    if not f:
        continue
    if f[0] == "C":
        if f[3] == "NA":
            na += 1; continue
        C[f[2]] += 1
        rmx, rmn, fmx, fmn = map(float, f[3:7]); slews += [float(f[7]), float(f[8])]
        if abs(abs(rmx - fmx) - H) > H * 0.6:
            amb.append(f[1])
        if fmx < rmx:
            odd_cells += 1; rmx, rmn, fmx, fmn = fmx, fmn, rmx, rmn
        rows.append(f"N {f[1][3:]} {rmx} {rmn}"); frows.append(f"M {f[1][3:]} {fmx - H} {fmn - H}")
    elif f[0] == "T":
        if f[2] == "NA":
            na += 1; continue
        rmx, rmn, fmx, fmn, sl = map(float, f[2:7])
        if fmx < rmx:
            odd_taps.append(f[1])
        if abs(abs(rmx - fmx) - H) > H * 0.6:
            amb.append(f[1])
        rows.append(f"T {f[1]} {rmx} {rmn} {sl}"); frows.append(f"F {f[1]} {fmx - H} {fmn - H}")
open(out, "w").write("# OT_EDGES v1 T/N=source rise F/M=source fall (late early), polarity-resolved\n" + "\n".join(rows + frows) + "\n")
r = dict(src=src, masters=dict(C), cells_odd_parity=odd_cells, taps_odd=len(odd_taps), odd_tap_examples=odd_taps[:5],
         ambiguous_edge_pins=len(amb), ambiguous_examples=amb[:5], na=na, rows=len(rows), cell_slew_max_ps=max(slews))
json.dump(r, open(cen, "w"), indent=1); print(json.dumps(r))
sys.exit(1 if odd_taps or amb else 0)
