#!/usr/bin/env python3
"""DIE-HBM-82-EP6 estimate: wbq_sw 86.4 -> NEWW wide (grown WEST, E/N/S/interior pins keep their absolute site), aq_tree13 aqhi
moved west to keep the 8.64 gap (rounded up to the 8.64 lattice); station chains are re-planned after (station_resite + hyb + ft_nudge).
usage: mk_mv.py PLANDIR [NEWW]   (unpacked d44v copy; edited in place)"""
import json, sys
from pathlib import Path
D = Path(sys.argv[1]); NEWW = float(sys.argv[2]) if len(sys.argv) > 2 else 155.52; G = 8.64
p = json.loads((D / "die_plan.json").read_text()); ce = json.loads((D / "clock_entries.json").read_text())
OLDF = "cores/ot_wbq_sw__86.4x544.32__d44v_split.json"; NEWF = f"cores/ot_wbq_sw__{NEWW:g}x544.32__d44v_split.json"
dx = NEWW - 86.4; log = []
pins = json.loads((D / OLDF).read_text())
for q in pins:
    if q["x"] > 0.2: q["x"] = round(q["x"] + dx, 3)
(D / NEWF).write_text(json.dumps(pins))
for tn, t in p["partition_types"].items():
    hc = t.get("hard_cores", [])
    for sw in [c for c in hc if c["module"] == "ot_wbq_sw"]:
        x0, y0 = sw["origin_um"]; nx0 = round(x0 - dx, 3); y1 = y0 + sw["outline_um"][1]
        sw["origin_um"] = [nx0, y0]; sw["outline_um"] = [NEWW, sw["outline_um"][1]]; sw["pins_file"] = NEWF
        e = ce.get(tn, {}).get(sw["inst"])
        if e:
            e["xy_um"][0] = round(e["xy_um"][0] + dx, 3); e["island_um"][0] += dx; e["island_um"][2] += dx
            for k in e.get("clock_pin_sites_um", {}): e["clock_pin_sites_um"][k][0] = round(e["clock_pin_sites_um"][k][0] + dx, 3)
        for c in hc:
            if c is sw: continue
            a = c["origin_um"]; r = [a[0], a[1], a[0] + c["outline_um"][0], a[1] + c["outline_um"][1]]
            if r[0] < x0 and r[2] > nx0 - G and r[1] < y1 + G and r[3] > y0 - G:
                sh = round(-(-(r[2] - (nx0 - G)) // G) * G, 3); c["origin_um"] = [round(a[0] - sh, 3), a[1]]; log.append((tn, c["inst"], -sh))
                for s in t.get("contents", []):
                    if s.get("inst") == c["inst"] and "origin_um" in s: s["origin_um"] = list(c["origin_um"])
        n = 0
        for s in t.get("internal_stations", []):
            for q in s.get("regs_um", []):
                if nx0 - 0.001 <= q[0] <= x0 + 0.001 and y0 <= q[1] <= y1: n += 1   # left for ft_nudge
        log.append((tn, sw["inst"], "sw", nx0, "regs inside new strip (ft_nudge)", n))
(D / "die_plan.json").write_text(json.dumps(p)); (D / "clock_entries.json").write_text(json.dumps(ce))
for l in log: print(*l)
