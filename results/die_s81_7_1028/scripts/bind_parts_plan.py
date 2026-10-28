#!/usr/bin/env python3
"""DIE-S81-7: bind a count_align_plan --sta-proof plan document WITH per-partition origins/relays (the --parts ocv form
that --count-align-key region needs).  count_align_bind.py only takes --parts ocv with --from-ocv (which re-plans
without the STA hull), so this die-local wrapper reads the endpoints (src_part, dst_part) from the same lpo rows and
calls the main bind/verify/report unchanged.  usage: bind_parts_plan.py plan.json lpo.json --scale S --out bind.json"""
import json, sys, argparse
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-s81-7/tools/die_plan")
import count_align_bind as B
import count_align_plan as CAP
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("lpo"); ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--corner", default="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5")
ap.add_argument("--samples", type=int, default=2000); ap.add_argument("--out", required=True); a = ap.parse_args()
plan = json.load(open(a.plan)); rows = CAP.load_rows(a.lpo, a.corner, a.scale)
parts = {r["port"]: (r["src_part"], r["dst_part"]) for r in rows}
b = B.bind(plan, parts=parts); v = B.verify(b, a.samples); rep = B.report(b, v); rep["relay"] = B.relay_summary(b)
rep["plan_source"] = a.plan; b["report"] = rep
Path(a.out).write_text(json.dumps(b, indent=0) + "\n"); print(json.dumps(rep, indent=1)[:1500])
