#!/usr/bin/env python3
"""QC-PG-3: A0-window class superposition on the QC-PG-MAP decks (claude/qc-pg-map-1027@91e2ffb77a kits).
Generalises QC-PG-2 su8_superpose2.py: any kit tag (grid/bump/window), classes S (signed cores at own vectorless),
A (A0 tiles at 1 W/mm2), F (flattened partition logic at 1 W/mm2); U8 used only if present and su8_W given.
upper(node) = S + (su8_W/0.0337 - 1)*U8 + bgA*A + bgF*F, VDD drop + VSS bounce co-located per load block, 450-um
edge band of the window excluded (as su8_superpose2).  window: all | nosu8 | a0 (blocks whose centre is inside an A0 rect)
Usage: a0_superpose.py KITROOT TAG CORES_JSON BG_A BG_F [window] [su8_W]"""
import csv, json, re, sys
from pathlib import Path
base = Path(sys.argv[1]); tag = sys.argv[2]; cores = json.loads(Path(sys.argv[3]).read_text())["cores"]
bgA, bgF = float(sys.argv[4]), float(sys.argv[5]); win = sys.argv[6] if len(sys.argv) > 6 else "all"
su8W = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0337
raw = {}
for cls in ("S", "U8", "A", "F"):
    d = base / cls / tag / "psm"
    if not (d / "ir_VDD.csv").exists():
        continue
    raw[cls] = {}
    for net in ("VDD", "VSS"):
        vals = {}
        for row in csv.DictReader((d / f"ir_{net}.csv").open()):
            v = float(row["Voltage"]); mv = (v if net == "VSS" else .7 - v) * 1000
            k = row["Instance"]; vals[k] = max(vals.get(k, -1e9), mv)
        raw[cls][net] = vals
irw = json.loads((base / "A" / tag / "irwin.json").read_text())
ox, oy = irw["window_um"][0], irw["window_um"][1]
d = base / "A" / tag / "psm"
s = (d / "psm.tcl").read_text()
pl = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(r"^ot_pl (\S+) (\S+) (\S+)", s, re.M)}
size = float(re.search(r"SIZE (\S+) BY", (d / "irblk.lef").read_text())[1])
width = max(x for x, y in pl.values()) + size
su = [c for c in cores if c["module"] == "qfd_dv_s5_su8_rst3"]
a0 = [c for c in cores if "a0" in c["module"]]
scale = su8W / .0337
def inside(rs, gx, gy): return any(c["rect"][0] <= gx <= c["rect"][2] and c["rect"][1] <= gy <= c["rect"][3] for c in rs)
vals = []
for k, (x, y) in pl.items():
    cx, cy = x + size / 2, y + size / 2
    if not (450 <= cx <= width - 450 and 450 <= cy <= width - 450): continue
    gx, gy = cx + ox, cy + oy
    if win == "nosu8" and inside(su, gx, gy): continue
    if win == "a0" and not inside(a0, gx, gy): continue
    up = {}
    for n in ("VDD", "VSS"):
        v = bgA * raw["A"][n][k] + bgF * raw["F"][n][k]
        if "S" in raw: v += raw["S"][n][k]
        if "U8" in raw: v += (scale - 1) * raw["U8"][n][k]
        up[n] = v
    parts = {c: round(sum(raw[c][n][k] for n in ("VDD", "VSS")), 3) for c in raw}
    vals.append((up["VDD"] + up["VSS"], k, up, parts))
upper, node, up, parts = max(vals, key=lambda t: t[0])
print(json.dumps(dict(tag=tag, window=win, bgA=bgA, bgF=bgF, su8_W=su8W, upper_mV=round(upper, 3), VDD=round(up["VDD"], 3),
                      VSS=round(up["VSS"], 3), node=node, unit_responses_mV=parts, classes=sorted(raw), blocks=len(vals))))
