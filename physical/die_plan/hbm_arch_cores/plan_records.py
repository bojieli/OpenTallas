#!/usr/bin/env python3
"""ELEM-HBM: plan-stage review records (review_record.py) for kits listed as view names on stdin, from review_core.py
stats (--review DIR) and the kit freeze (--kits DIR).  Verdict PASS-COND = place only."""
import argparse, json, re, subprocess, sys
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("--kits", required=True); ap.add_argument("--review", required=True)
a = ap.parse_args()
H = Path(__file__).resolve().parent
for view in sys.stdin.read().split():
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", view)
    kd = Path(a.kits) / safe.replace("_" + view.split("@")[1], "") if False else Path(a.kits) / (view.split("@")[0] + "_" + view.split("@")[1])
    fz = json.load(open(kd / "freeze.json")); rd = Path(a.review) / safe
    s = json.load(open(rd / "stats.json"))
    mt = max(max(x["max_per_track"].values()) for x in s["faces"].values())
    faces = ",".join(f"{f}:{x['pins']}" for f, x in sorted(s["faces"].items()))
    away = [c for c in s["partner_checks"] if c["cos"] is not None and c["cos"] < 0]
    r = (f"plan-stage (B2l, GEOM-REVIEW die PASS-COND e1c50d83cff2): {s['outline_um'][0]}x{s['outline_um'][1]} um, {s['pins']} pins, "
         f"faces {faces}; worst {mt} pins/track per layer (<=0.6 OK), pins on lattice. Context {s['partition']}/{s['inst']}: "
         f"{s['connected_buses']}/{s['buses']} buses with partners; {s['bits_facing_away']} of {s['connected_bits']} connected bits "
         "leave a face pointing away from the nearest partner" + (f" (e.g. {', '.join(sorted({c['bus'] for c in away})[:4])})" if away else "")
         + f"; {s['bits_beyond_local_reach']} bits > 365 um to the nearest partner (plan stations). Macros: "
         + (str(fz.get("macros")) if fz.get("macros") else "none") + ". Fill/density/face-flop distance/clock judged at the placed stage.")
    fx = "Place only; route + signoff after the placed-stage review." + (" Facing-away buses reported to HBM-ARCH." if away else "")
    p = subprocess.run([sys.executable, str(H / "review_record.py"), str(kd), "plan", "PASS-COND", r, fx, "--pics",
                        f"{rd}/plan.png,{rd}/context.png"], capture_output=True, text=True)
    print(p.returncode, view)
