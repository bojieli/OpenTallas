#!/usr/bin/env python3
"""HBM-REFORM-B5 d44v part 33, after mk_split: tile S face in bit columns, rest N seam pins straight across the street.
    mk_p33.py PLAN_DIR q2n_seam.json
mk_split packs seam pins per peer in natural order into x 199-438 (mean seam dx 104 um over an 8.64 street).  The switch is bit sliced: source bit i of every
word reaches only bit i of the sinks, so every tile S pin goes to x ~ i / 545 of the width and its rest partner goes on the same x."""
import json, math, re, sys
from pathlib import Path
d, seam = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
PITCH, OFF, W, LO = 0.048, 0.024, 786.24, 1.0
trk = lambda v: round(OFF + round((v - OFF) / PITCH) * PITCH, 3)
ft = d / "cores/ot_q2nf_qout__786.24x112.32__d44v_split.json"; fr = d / "cores/ot_q2nf_rest__786.24x622.08__d44v_split.json"
T, R = json.loads(ft.read_text()), json.loads(fr.read_text())
def legal(items):
    items = sorted(items); hi = W - LO; s = 2 * PITCH
    assert (hi - LO) / s + 1 >= len(items), len(items)
    pos = []
    for w, _ in items:
        p = trk(min(max(w, LO), hi))
        if pos and p < pos[-1] + s - 1e-9: p = round(pos[-1] + s, 3)
        pos.append(p)
    for i in range(len(pos) - 1, -1, -1):
        lim = trk(hi) if i == len(pos) - 1 else round(pos[i + 1] - s, 3)
        if pos[i] > lim + 1e-9: pos[i] = lim
    return {k: p for (_, k), p in zip(items, pos)}
def bit(n):
    m = re.match(r"(captured|lk_d)\[(\d+)\]$", n)
    return int(m[2]) % 545 if m else None
S = [p for p in T if p["y"] < 0.2 and p["layer"] == "M5"]
want = []
for p in S:
    b = bit(p["name"])
    want.append(((b + 0.5) / 545 * W if b is not None else W / 2, p["name"]))
xt = legal(want)
for p in S: p["x"] = xt[p["name"]]
ft.write_text(json.dumps(T, indent=1) + "\n")
Ntop = max(p["y"] for p in R)
N = [p for p in R if p["y"] > Ntop - 0.2 and p["layer"] == "M5"]
inv = {r: t for t, r in seam.items()}
xr = legal([(xt[inv[p["name"]]] if p["name"] in inv else p["x"], p["name"]) for p in N])
for p in N: p["x"] = xr[p["name"]]
fr.write_text(json.dumps(R, indent=1) + "\n")
print("tile S", len(S), "rest N", len(N), "seam", len(seam))
