"""R25 (COORD GEOM-24 PASS-COND): locate every same-net (VSS) drawn-shield pair with an across-axis gap 0 < g < 0.5 um
(NC-QC-R24c vss_notch class; the minimum-spacing ones are 0.04) (+1e-6) and along-overlap > 0 in mesh.json (same shield geometry as wide_vss_check.py: off 1.14, half width 0.32),
then count DRT markers (drc/box_*.rpt) whose bbox touches a gap box (+0.02 um).  Gate: 0 marked gaps, else the fallback is
ONE shared shield between the two clock nets.  usage: r25_samenet_gaps.py MESH.json [DRC_DIR] OUT.json"""
import json, re, sys, collections
from pathlib import Path
mesh = sys.argv[1]; drc = Path(sys.argv[2]) if len(sys.argv) > 3 else None; out = sys.argv[-1]
m = json.load(open(mesh)); OFF, SW2 = 1.14, 0.32
sh = collections.defaultdict(list)
for w in m["fixed_wires"]:
    n = len(w["segs"])
    for (L, x0, y0, x1, y1), mo, e in zip(w["segs"], w.get("shield_modes") or ["drawn"] * n, w.get("shield_ext") or [1.46] * n):
        e = 1.46 if e is None else e
        c, a0, a1 = (y0, min(x0, x1), max(x0, x1)) if L == "M8" else (x0, min(y0, y1), max(y0, y1))
        if mo == "drawn":
            for s in (-1, 1):
                sh[L].append((c + s * OFF - SW2, c + s * OFF + SW2, a0 - e, a1 + e, w["name"]))
gaps = []
for L, S in sh.items():
    S.sort()
    for i, a in enumerate(S):
        for b in S[i + 1:]:
            if b[0] > a[1] + 0.5:
                break
            g = b[0] - a[1]
            if 1e-6 < g < 0.5 - 1e-6:
                lo, hi = max(a[2], b[2]), min(a[3], b[3])
                if hi > lo:
                    box = (a[1], lo, b[0], hi) if L == "M9" else (lo, a[1], hi, b[0])   # (x0,y0,x1,y1)
                    gaps.append(dict(layer=L, gap=round(g, 4), box=[round(v, 4) for v in box], nets=sorted({a[4], b[4]})))
# end-to-end gaps: overlapping across-span, along-axis gap <= 0.04 (shield of one leg ends 0.04 short of another's)
for L, S in sh.items():
    for i, a in enumerate(S):
        for b in S[i + 1:]:
            if b[0] > a[1] - 1e-6:
                break
            if min(a[1], b[1]) - max(a[0], b[0]) <= 1e-6:
                continue
            for p_, q_ in ((a, b), (b, a)):
                g = q_[2] - p_[3]
                if 1e-6 < g <= 0.04 + 1e-6:
                    c0, c1 = max(a[0], b[0]), min(a[1], b[1])
                    box = (c0, p_[3], c1, q_[2]) if L == "M9" else (p_[3], c0, q_[2], c1)
                    gaps.append(dict(layer=L, kind="end", gap=round(g, 4), box=[round(v, 4) for v in box], nets=sorted({a[4], b[4]})))
res = dict(rule=__doc__.split("\n")[0], gaps=len(gaps), gap_hist=sorted(collections.Counter(g["gap"] for g in gaps).items()), by_layer_kind=dict(collections.Counter(g["layer"] + ":" + g.get("kind", "side") for g in gaps)))
if drc:
    mk = set()
    for p in sorted(drc.glob("box_*.rpt")):
        for mm in re.finditer(r"violation type: (.*)\n\s*srcs: (.*)\n\s*bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)", p.read_text()):
            mk.add((mm.group(1).strip(), mm.group(7), tuple(float(mm.group(i)) for i in range(3, 7))))
    hit = []
    for g in gaps:
        x0, y0, x1, y1 = g["box"]
        for t, L, b in mk:
            if L == g["layer"] and b[0] <= x1 + 0.02 and b[2] >= x0 - 0.02 and b[1] <= y1 + 0.02 and b[3] >= y0 - 0.02:
                hit.append(dict(g, marker=t, bbox=b)); break
    res.update(drc_markers=len(mk), marked_gaps=len(hit), sample=hit[:10],
               verdict="PASS (0 marked same-net 0.04 gaps)" if not hit else "FAIL -> shared-shield fallback")
res["gap_list"] = gaps
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("gap_list", "sample")}))
