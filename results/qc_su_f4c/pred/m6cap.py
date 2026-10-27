#!/usr/bin/env python3
"""QC-SU-F4C: die M6 capacity over the SU cores when the in-core tree nets route on M6 H / M5 V (PG-via-free feeds).
Per tree edge (root/island/B/repeater/leaf-driver, from the mscts spec) one L: |dx| on M6, |dy| on M5 (the leg's
horizontal part is the only M6 use; leaf nets stay <= M4).  M6 = horizontal, pitch 0.064 um (6_final.def TRACKS).
Reports per core: M6 track-um used / available, and the worst vertical cut (max # of M6 tree wires over one x =
tracks a die-level horizontal M6 route over the core loses at that x), for a 1-track and a 3-track (NDR 2W2S) wire.
PLAN GEOMETRY, UNCHECKED.  usage: m6cap.py SPEC.tcl CORE_W CORE_H [NAME]"""
import re, sys
spec, cw, ch = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
t = open(spec).read()
root = tuple(map(float, re.search(r"set ot_ms_root \{([\d.]+) ([\d.]+)\}", t).groups()))
xy = {"root": root}; par = {}
blk = t.split("set ot_ms_tree {", 1)[1].split("\n}", 1)[0]
for m in re.finditer(r"\{(\S+) (\S+) ([\d.]+) ([\d.]+) (\S+)\}", blk):
    xy[m.group(1)] = (float(m.group(3)), float(m.group(4))); par[m.group(1)] = m.group(2)
lv = t.split("set ot_ms_leaves {", 1)[1].split("\n}\nset", 1)[0]
for m in re.finditer(r"^\s*\{(\S+) (\S+) \{([\d.]+) ([\d.]+)\}", lv, re.M):
    xy[m.group(1)] = (float(m.group(3)), float(m.group(4))); par[m.group(1)] = m.group(2)
segs = [(min(xy[n][0], xy[p][0]), max(xy[n][0], xy[p][0])) for n, p in par.items()]
h = sum(b - a for a, b in segs); v = sum(abs(xy[n][1] - xy[p][1]) for n, p in par.items())
PITCH = 0.064; ntr = int(ch / PITCH); cap = ntr * cw
xs = sorted({round(a, 3) for a, _ in segs} | {round(b, 3) for _, b in segs})
cut = max(sum(1 for a, b in segs if a <= x + 1e-6 and b >= x + 1e-6 and b - a > 1e-6) for x in xs)
print(dict(spec=spec, edges=len(par), m6_h_um=round(h, 1), m5_v_um=round(v, 1), m6_tracks_per_core=ntr,
           m6_track_um_core=round(cap), used_1trk_pct=round(100 * h / cap, 2), used_3trk_pct=round(300 * h / cap, 2),
           worst_cut_wires=cut, worst_cut_tracks_1trk=cut, worst_cut_tracks_3trk=3 * cut,
           worst_cut_pct_3trk=round(300 * cut / ntr, 2)))
