#!/usr/bin/env python3
"""BUMP-SURVEY: PDNSim window kits with the INFRA-FIRST-HEAD-5 pad model (infra_pg.window_kit pad_um, VDD+VSS) on any die plan.
usage: bs_psm.py SRC PLAN OUT --cand LAB:W8@P8:W9@P9 --pad 70 --pad 75 --window NAME=x0,y0,x1,y1 [--core-w-mm2 D | --core-watts W] [--loads loads.json]
pg.domains are dropped (core-only window, as head_pg_sweep psm). Read-only on the plan."""
import argparse, json, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--cand", action="append", required=True); ap.add_argument("--pad", type=float, action="append", required=True)
ap.add_argument("--window", action="append", required=True); ap.add_argument("--bump", type=float, default=150.0)
ap.add_argument("--core-w-mm2", type=float); ap.add_argument("--core-watts", type=float); ap.add_argument("--tile", type=float, default=43.2)
ap.add_argument("--loads", help="json [[rect, W/mm2], ...] power map")
ap.add_argument("--power", help="infra_pg power json {core_w_mm2?, types: {type: W/mm2}}")
a = ap.parse_args()
sys.path.insert(0, str(Path(a.src) / "tools" / "die_plan"))
import infra_pg as G, schema as S
raw = json.loads(Path(a.plan).read_text())
raw["die"]["pg"] = {k: v for k, v in raw["die"]["pg"].items() if k != "domains"}
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
nd = out / "plan_nodomains.json"; nd.write_text(json.dumps(raw))
P = S.Plan(S.load(str(nd)), nd)
power = {"core_watts": a.core_watts} if a.core_watts is not None else (json.loads(Path(a.power).read_text()) if a.power else None)
loads = [(r, d) for r, d in json.loads(Path(a.loads).read_text())] if a.loads else None
for spec in a.cand:
    lab, g8, g9 = spec.split(":")
    w8, p8 = map(float, g8.split("@")); w9, p9 = map(float, g9.split("@"))
    g = [dict(layer="M8", width_um=w8, pitch_um=p8, offset_um=round(p8 / 2, 4), nets=["VDD", "VSS"]),
         dict(layer="M9", width_um=w9, pitch_um=p9, offset_um=round(p9 / 2, 4), nets=["VDD", "VSS"])]
    pg = dict(grid=g, regions=[], core_w_mm2=a.core_w_mm2, bump_pitch_um=a.bump, vdd=0.7, budget_mv=35.0)
    for pad in a.pad:
        for win in a.window:
            name, r = win.split("="); rect = [float(v) for v in r.split(",")]
            lab2 = f"{lab}_p{pad:g}_{name}"
            m = G.window_kit(P, nd.parent, pg, out / lab2, lab2, rect, tile=a.tile, power=power, core_w_mm2=a.core_w_mm2,
                             pad_um=pad, nets=("VDD", "VSS"), loads=loads)
            m["plan"] = str(nd.resolve()); m["plan_src"] = str(Path(a.plan).resolve()); m["tracks"] = G.tracks_of(P, g)
            (out / lab2 / "irwin.json").write_text(json.dumps(m, indent=1) + "\n")
            print(lab2, m["window_um"], m["power_w"], "W", m["bumps"], "bumps", "est", m["est_worst_mv"], "mV", m["tracks"])
