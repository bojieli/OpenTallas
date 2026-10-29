#!/usr/bin/env python3
"""QC-PG-5: PDNSim window kits straight from a QC PLAN (die.pg.grid + die.pg.bumps incl. fields, per-bump pads) with the
QC-PG-MAP class load maps (linear superposition: one kit per class at its map; combine with a0_superpose.py).
usage: plan_psm.py SRC PLAN OUT --window NAME=x0,y0,x1,y1 --cls A=loads_A.json [--cls F=...] [--tile 43.2]"""
import argparse, json, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--window", action="append", required=True); ap.add_argument("--cls", action="append", required=True)
ap.add_argument("--tile", type=float, default=43.2); ap.add_argument("--tag", default="PL")
a = ap.parse_args()
sys.path.insert(0, str(Path(a.src) / "tools" / "die_plan"))
import infra_pg as G, schema as S, die_trial as D
raw = json.loads(Path(a.plan).read_text())
raw["die"]["pg"] = {k: v for k, v in raw["die"]["pg"].items() if k != "domains"}
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
nd = out / "plan_nodomains.json"; nd.write_text(json.dumps(raw))
P = S.Plan(S.load(str(nd)), nd)
cfg = D.bump_contract(P)
pg = dict(grid=P.die["pg"]["grid"], regions=[], bump_pitch_um=cfg["pitch_um"], vdd=0.7, budget_mv=35.0)
for c in a.cls:
    cls, lf = c.split("=")
    loads = [(r, d) for r, d in json.loads(Path(lf).read_text())]
    for win in a.window:
        name, r = win.split("="); rect = [float(v) for v in r.split(",")]
        lab = f"{a.tag}_{name}"
        m = G.window_kit(P, Path(a.plan).parent, pg, out / cls / lab, lab, rect, tile=a.tile, nets=("VDD", "VSS"), loads=loads)
        m["plan"] = str(nd.resolve()); m["plan_src"] = str(Path(a.plan).resolve()); m["tracks"] = G.tracks_of(P, pg["grid"])
        pads = {}
        for ln in (out / cls / lab / "psm" / "bumps.tcl").read_text().splitlines():
            if ln.startswith("ot_pad "):
                f = ln.split(); pads[f[5] if len(f) > 5 else "base"] = pads.get(f[5] if len(f) > 5 else "base", 0) + 1
        m["bump_pads"] = pads
        (out / cls / lab / "irwin.json").write_text(json.dumps(m, indent=1) + "\n")
        print(cls, lab, m["window_um"], m["power_w"], "W", m["bumps"], "bumps", pads, m["tracks"])
