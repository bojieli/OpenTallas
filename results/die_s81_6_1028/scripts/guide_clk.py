#!/usr/bin/env python3
"""DIE-S81-6 (COORD ASK-2 condition): clock-net wire from GRT guides vs the CTS tree estimate, and clock guide segments on
M4-M7 longer than one GCell (= beyond the pin/leaf via stack).  usage: guide_clk.py route.guide tree.json"""
import json, sys, collections
g, tj = sys.argv[1], sys.argv[2]
DBU = 1000.0
wire = collections.Counter(); low = []; nets = 0; cur = None; gc = None
lowlen = collections.Counter()
with open(g) as f:
    for ln in f:
        s = ln.strip()
        if not s:
            continue
        if s == "(":
            continue
        if s == ")":
            cur = None; continue
        x = s.split()
        if len(x) == 1:
            cur = x[0] if x[0].startswith("ck_") else None
            nets += cur is not None
            continue
        if cur is None:
            continue
        x0, y0, x1, y1 = (int(v) / DBU for v in x[:4]); L = x[4]
        w, h = x1 - x0, y1 - y0
        gcl = min(w, h)
        gc = gc or gcl
        seg = max(w, h) - gcl
        wire[L] += seg
        if L in ("M4", "M5", "M6", "M7") and seg > 1e-3:
            lowlen[cur] += seg
            low.append((cur, L, round(seg, 1)))
t = json.load(open(tj))
cts = t["meta"]["wire_um"]
tot = sum(wire.values())
print(json.dumps(dict(clock_nets=nets, gcell_um=gc, guide_wire_um={k: round(v) for k, v in sorted(wire.items())},
                      guide_total_um=round(tot), cts_wire_um=round(cts), ratio=round(tot / cts, 4),
                      m4_m7_segments_beyond_gcell=len(low), m4_m7_nets=len(lowlen),
                      m4_m7_um=round(sum(lowlen.values()), 1), worst_m4_m7=sorted(lowlen.items(), key=lambda z: -z[1])[:8])))
