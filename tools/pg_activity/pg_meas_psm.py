#!/usr/bin/env python3
"""PG-ACTIVITY-KVHBM (10-27): PDNSim window kits (BUMP-SURVEY bs_psm.py / INFRA-FIRST-HEAD-5 window_kit pad model, VDD+VSS)
with (a) a measured-activity power map (--loads [[rect, W/mm2]...] or --power {types: {type: W/mm2}}) and (b) an opt-in
EDGE-FILL C4 lattice (--edge-margin M): per axis n = floor((L - 2M)/pitch) + 1 bumps, centred, pitch unchanged, so a die
whose centred lattice leaves > pitch/2 + M at the edge gets one more bump column/row (HBM B2r2 W: 167 -> 168 columns,
first column 147.12 -> 72.12 um from the die edge).  Default (no --edge-margin) = die_trial.bump_grid byte-identical.
usage: pg_meas_psm.py SRC PLAN OUT --cand LAB:W8@P8:W9@P9 --pad 70 --window NAME=x0,y0,x1,y1 [--loads J | --power J]
       [--edge-margin 60] [--bump 150]"""
import argparse, json, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--cand", action="append", required=True); ap.add_argument("--pad", type=float, action="append", required=True)
ap.add_argument("--window", action="append", required=True); ap.add_argument("--bump", type=float, default=150.0)
ap.add_argument("--tile", type=float, default=43.2)
ap.add_argument("--loads"); ap.add_argument("--power"); ap.add_argument("--edge-margin", type=float)
a = ap.parse_args()
sys.path.insert(0, str(Path(a.src) / "tools" / "die_plan"))
import infra_pg as G, schema as S, die_trial as D
if a.edge_margin is not None:
    M = a.edge_margin
    def bump_grid(P, io, pitch=150.0, size=60.0):
        keep = [c["rect_um"] for c in P.die.get("channels", [])] + [w["rect_um"] for w in io]
        nx, ny = int((P.W - 2 * M) // pitch) + 1, int((P.H - 2 * M) // pitch) + 1
        x0, y0 = (P.W - (nx - 1) * pitch) / 2, (P.H - (ny - 1) * pitch) / 2
        out = []
        for i in range(nx):
            for j in range(ny):
                x, y = x0 + i * pitch, y0 + j * pitch
                if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in keep):
                    continue
                out.append(("VDD" if (i + j) % 2 == 0 else "VSS", round(x, 3), round(y, 3)))
        return out
    D.bump_grid = bump_grid
raw = json.loads(Path(a.plan).read_text())
raw["die"]["pg"] = {k: v for k, v in raw["die"]["pg"].items() if k != "domains"}
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
nd = out / "plan_nodomains.json"; nd.write_text(json.dumps(raw))
P = S.Plan(S.load(str(nd)), nd)
power = json.loads(Path(a.power).read_text()) if a.power else None
loads = [(r, d) for r, d in json.loads(Path(a.loads).read_text())] if a.loads else None
if a.edge_margin is not None:
    b = D.bump_grid(P, [], pitch=a.bump)
    xs = sorted({x for _, x, _ in b}); ys = sorted({y for _, _, y in b})
    print("EDGE-FILL lattice", len(xs), "x", len(ys), "first/last col", xs[0], round(P.W - xs[-1], 3), "row", ys[0], round(P.H - ys[-1], 3))
for spec in a.cand:
    lab, g8, g9 = spec.split(":")
    w8, p8 = map(float, g8.split("@")); w9, p9 = map(float, g9.split("@"))
    g = [dict(layer="M8", width_um=w8, pitch_um=p8, offset_um=round(p8 / 2, 4), nets=["VDD", "VSS"]),
         dict(layer="M9", width_um=w9, pitch_um=p9, offset_um=round(p9 / 2, 4), nets=["VDD", "VSS"])]
    pg = dict(grid=g, regions=[], core_w_mm2=None, bump_pitch_um=a.bump, vdd=0.7, budget_mv=35.0)
    for pad in a.pad:
        for win in a.window:
            name, r = win.split("="); rect = [float(v) for v in r.split(",")]
            lab2 = f"{lab}_p{pad:g}_{name}"
            m = G.window_kit(P, nd.parent, pg, out / lab2, lab2, rect, tile=a.tile, power=power, pad_um=pad,
                             nets=("VDD", "VSS"), loads=loads)
            m.update(plan=str(nd.resolve()), plan_src=str(Path(a.plan).resolve()), tracks=G.tracks_of(P, g),
                     power_src=str(Path(a.loads or a.power).resolve()) if (a.loads or a.power) else None,
                     edge_margin_um=a.edge_margin)
            (out / lab2 / "irwin.json").write_text(json.dumps(m, indent=1) + "\n")
            print(lab2, m["window_um"], m["power_w"], "W", m["bumps"], "bumps", "est", m["est_worst_mv"], "mV", m["tracks"])
