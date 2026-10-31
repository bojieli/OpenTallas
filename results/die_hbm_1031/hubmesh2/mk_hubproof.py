#!/usr/bin/env python3
"""HBM-HUBMESH-2 (1): hub-only die_sta_related proof from a hub mesh sign-off (explicit_mesh_signoff mc JSON).

    mk_hubproof.py MC_TT.json REC.json PART ORIGIN_X ORIGIN_Y OUT_DIR [--ff-scale 0.8666]

Taps = the mesh loads, renamed to the die tap ports (L_clk -> t_<part>__clk, L_clk_tN -> t_<part>__clk_tN,
K_clk_cN -> t_<part>__clk_cN).  Arrival = the routed (GRT-RC) nominal mesh arrival of the mc record ('routed'), late =
early (nominal 12.24c, no OCV, no mesh CPPR credit: one cppr node = the hub region root with range 0).  FF = TT x
--ff-scale (no FF mesh run exists on GRT; default = the measured FF/TT late ratio of the same hub taps on the DIE-HBM-45
B routed die tree, UNCHECKED for a BUFx24 mesh).  Diagnostic, not counted.
"""
import json, re, sys
from pathlib import Path

a = sys.argv[1:]
ffs = 0.8666
if "--ff-scale" in a:
    i = a.index("--ff-scale"); ffs = float(a[i + 1]); del a[i:i + 2]
mc, rec, part, ox, oy, out = json.load(open(a[0])), json.load(open(a[1])), a[2], float(a[3]), float(a[4]), Path(a[5])
out.mkdir(parents=True, exist_ok=True)
xy = {t["port"]: t["xy"] for t in rec["taps"]}
kind = {t["port"]: t["kind"] for t in rec["taps"]}


def die_port(p):
    if p == "L_clk":
        return f"t_{part}__clk"
    m = re.fullmatch(r"L_clk_(t\d+)", p) or re.fullmatch(r"K_clk_(c\d+)", p)
    if not m:
        raise SystemExit(f"unmapped load {p}")
    return f"t_{part}__clk_{m.group(1)}"


for corner, f in (("TT", 1.0), ("FF", ffs)):
    taps = []
    for p, v in zip(mc["loads"], mc["routed"]):
        v = float(v) * f
        taps.append(dict(port=die_port(p), part=part, late_ps=v, early_ps=v, slew_ps=20.0, cppr_node=part,
                         stages_from_root=0, xy_um=[ox + xy[p][0], oy + xy[p][1]], mesh_load=p, kind=kind[p]))
    json.dump(dict(corner=corner, basis=f"HBM-HUBMESH-2 hub-only proof from {a[0]} (GRT-RC nominal mesh arrivals"
                   + ("" if corner == "TT" else f" x FF/TT {ffs} UNCHECKED") + ")",
                   cppr_node_range_ps={part: 0.0}, node_late_ps={part: 0.0}, node_early_ps={part: 0.0}, taps=taps),
              open(out / f"tap_arrivals_{corner}.json", "w"), indent=0)
print(len(taps), "taps ->", out)
