#!/usr/bin/env python3
"""outline_sweep.py PLAN TREE TYPE KITDIR OUTJSON : one HEAD type -> outline emptiness + pin-distance row (HEAD-95 rp18 sweep).

logic span = weighted 1-99 % box of the type's sink bins (clock.sink_bins_file, measured flop sites) united with
every placed macro box (gen phys macro_place.tcl locations + LEF sizes from KITDIR); empty = 1 - span area / outline
area; pin distance = Manhattan distance from each I/O pin (KITDIR/TYPE/audit_pins.json) to the span box."""
import gzip, json, os, re, sys
from pathlib import Path

plan, tree, tn, kit, out = sys.argv[1:6]
P = json.load(open(plan)); t = P["partition_types"][tn]
W, H = t["outline_um"]
row = dict(type=tn, outline=[W, H])
# sinks
bf = (t.get("clock") or {}).get("sink_bins_file")
pts = []
if bf:
    f = Path(tree) / bf
    d = json.load(gzip.open(str(f) + ".gz")) if not f.exists() and Path(str(f) + ".gz").exists() else json.load(open(f))
    pts = [(b[0], b[1], b[2]) for b in d["bins"]]
elif (t.get("clock") or {}).get("sink_sites_um"):
    pts = [(s[0], s[1], s[2] if len(s) > 2 else 1) for s in t["clock"]["sink_sites_um"]]
row["sinks"] = sum(p[2] for p in pts)


def pct(vals, q):
    vals = sorted(vals); tot = sum(w for _, w in vals); acc = 0
    for v, w in vals:
        acc += w
        if acc >= q * tot:
            return v
    return vals[-1][0]


box = None
if pts:
    box = [pct([(p[0], p[2]) for p in pts], .01), pct([(p[1], p[2]) for p in pts], .01),
           pct([(p[0], p[2]) for p in pts], .99), pct([(p[1], p[2]) for p in pts], .99)]
# macros: macro_place.tcl + LEF SIZE in the kit
k = Path(kit) / tn
sizes = {}
for lef in list(Path(kit).rglob("*.lef")):
    txt = lef.read_text(errors="ignore")
    for m in re.finditer(r"MACRO\s+(\S+)(.*?)END\s+\1", txt, re.S):
        s = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", m.group(2))
        if s:
            sizes[m.group(1)] = (float(s.group(1)), float(s.group(2)))
mboxes = []
mp = k / "macro_place.tcl"
if mp.exists():
    # master per instance from the synth netlist is not available pre-synth; use the plan hard_cores / contents sizes
    pass
for h in (t.get("hard_cores") or []) + [c for c in (t.get("contents") or []) if isinstance(c, dict)]:
    o = h.get("origin_um") or h.get("at_um") or h.get("xy")
    sz = h.get("outline_um") or h.get("size_um") or sizes.get(h.get("master") or h.get("module") or "", None)
    if o and sz:
        rot = str(h.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90")
        w, hh = (sz[1], sz[0]) if rot else (sz[0], sz[1])
        mboxes.append([o[0], o[1], o[0] + w, o[1] + hh])
row["macros"] = len(mboxes)
for b in mboxes:
    box = b[:] if box is None else [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
row["span"] = [round(v, 1) for v in box] if box else None
if box:
    sa = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
    row["empty"] = round(1 - sa / (W * H), 3)
# pins
ap = k / "audit_pins.json"
far = []
if ap.exists() and box:
    for p in json.load(open(ap)):
        x, y = p["x"], p["y"]
        dx = max(box[0] - x, 0, x - box[2]); dy = max(box[1] - y, 0, y - box[3])
        if dx + dy > 100:
            far.append((p["bus"], p.get("bit"), p.get("face"), round(x, 1), round(y, 1), round(dx + dy, 1)))
    row["pins"] = len(json.load(open(ap)))
byb = {}
for b, bit, face, x, y, dist in far:
    e = byb.setdefault(b, [0, face, x, y, dist]); e[0] += 1; e[4] = max(e[4], dist)
row["far_pins"] = len(far)
row["far_buses"] = sorted(([b] + v for b, v in byb.items()), key=lambda r: -r[5])[:12]
json.dump(row, open(out, "w"))
print(json.dumps(row)[:400])
