#!/usr/bin/env python3
"""HBM-GAPS-4-Q3SPLIT d44v part 34 post-step (after mk_split.py): the ot_hfd_coll_q3_edge_link pin table in one band per tile.

mk_split.py places a shared replica table at the mean of the three links' parent pin sites; the three links sit at
different y in the old 1054-um table, so the mean says little.  This step re-sites the link's signal pins on the faces
mk_split chose (W = the rx/tx pin side, E = the flit side, asserted unchanged), inside the link's own tile:
  W lower half: phy_up, rx_pin_v, rx_pin_flit[0..611]      W upper half: tx_pin_v, tx_pin_flit[0..611]
  E lower half: rx_v, rx_flit[0..544], epoch_abort, retry_requested (faces rx_pin straight across: rx path)
  E upper half: wr_flit[0..544] and the controls (faces tx_pin: write -> SRAM -> tx path)
Each group is spread evenly over its half (core inset 4.32 kept clear), on M4 tracks (0.048 pitch, 0.024 offset),
in natural bit order, >= 2 tracks apart.  The clock pin (mk_split centre entry, spec clock_entry) is kept.
    mk_p34pins.py PLAN_DIR"""
import json, re, sys
from pathlib import Path
d = Path(sys.argv[1]); MOD = "ot_hfd_coll_q3_edge_link"
fs = sorted((d / "cores").glob(f"{MOD}__*__d44v_split.json")); assert len(fs) == 1, fs
f = fs[0]; W, H = map(float, re.search(r"__([\d.]+)x([\d.]+)__", f.name).groups())
P = json.loads(f.read_text()); E, PITCH, OFF, INS = 0.096, 0.048, 0.024, 4.32
nat = lambda n: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", n)]
base = lambda n: re.sub(r"\[\d+\]$", "", n)
face = lambda p: "W" if p["x"] < 1 else "E" if p["x"] > W - 1 else "C"
old = {p["name"]: face(p) for p in P}
G = {("W", 0): ["phy_up", "rx_pin_v", "rx_pin_flit"], ("W", 1): ["tx_pin_v", "tx_pin_flit"],
     ("E", 0): ["rx_v", "rx_flit", "epoch_abort", "retry_requested"]}
grp = {}
for p in P:
    if face(p) == "C":
        continue
    b = base(p["name"]); k = next((k for k, v in G.items() if b in v), None)
    if k is None:
        assert face(p) == "E", p; k = ("E", 1)
    assert k[0] == face(p), (p["name"], "face differs from mk_split", k, face(p))
    grp.setdefault(k, []).append(p)
trk = lambda v: round(OFF + round((v - OFF) / PITCH) * PITCH, 3)
mid = H / 2
for (fc, half), L in grp.items():
    order = {b: i for i, b in enumerate(G.get((fc, half), []))}
    L.sort(key=lambda p: (order.get(base(p["name"]), len(order)), base(p["name"]), nat(p["name"])))
    lo, hi = (INS + 1.0, mid - 1.0) if half == 0 else (mid + 1.0, H - INS - 1.0)
    step = (hi - lo) / max(len(L) - 1, 1)
    assert step >= 2 * PITCH, (fc, half, len(L), step)
    ys = [trk(lo + i * step) for i in range(len(L))]
    assert all(b - a >= 2 * PITCH - 1e-9 for a, b in zip(ys, ys[1:])), (fc, half)
    for p, y in zip(L, ys):
        p["y"] = y; p["x"] = E if fc == "W" else round(W - E, 3); p["layer"] = "M4"
assert {p["name"]: face(p) for p in P} == old
f.write_text(json.dumps(P) + "\n")
print(f.name, {f"{k[0]}{k[1]}": len(v) for k, v in sorted(grp.items())}, "clock", sum(1 for p in P if face(p) == "C"))
