#!/usr/bin/env python3
"""DIE-QC-45: edges_raw.txt (edge_readout.tcl) -> trial_tap_arrivals input (T port late early slew / N cell late early,
source RISE edge, polarity-resolved) + a polarity / master census.
Polarity per pin: the source-rise-derived transition is the EARLIER of the two absolute arrivals (the source fall
launches at T/2 = 416.5 ps; |rise-fall propagation difference| << T/2 is asserted per pin).  Taps must be true
polarity (rise-derived = pin rise); an odd tap is counted and fails the export.
usage: mk_edges.py EDGES_RAW OUT_ARR OUT_CENSUS_JSON"""
import sys, json, collections
src, out, cen = sys.argv[1:4]
H = 833.0 / 2
C = collections.Counter(); odd_cells = 0; odd_taps = []; amb = []; rows = []; na = 0
for ln in open(src):
    f = ln.split()
    if not f:
        continue
    if f[0] == "C":
        if f[3] == "NA":
            na += 1; continue
        C[f[2]] += 1
        rmx, rmn, fmx, fmn = map(float, f[3:7])
        if abs(abs(rmx - fmx) - H) > H * 0.6:
            amb.append(f[1])
        if fmx < rmx:          # odd: source rise appears as Y fall
            odd_cells += 1; rmx, rmn = fmx, fmn
        rows.append(f"N {f[1][3:]} {rmx} {rmn}")
    elif f[0] == "T":
        if f[2] == "NA":
            na += 1; continue
        rmx, rmn, fmx, fmn, sl = map(float, f[2:7])
        if fmx < rmx:
            odd_taps.append(f[1])
        if abs(abs(rmx - fmx) - H) > H * 0.6:
            amb.append(f[1])
        rows.append(f"T {f[1]} {rmx} {rmn} {sl}")
open(out, "w").write("\n".join(rows) + "\n")
r = dict(src=src, masters=dict(C), cells_odd_parity=odd_cells, taps_odd=len(odd_taps), odd_tap_examples=odd_taps[:5],
         ambiguous_edge_pins=len(amb), ambiguous_examples=amb[:5], na=na, rows=len(rows))
json.dump(r, open(cen, "w"), indent=1); print(json.dumps(r))
sys.exit(1 if odd_taps or amb else 0)
