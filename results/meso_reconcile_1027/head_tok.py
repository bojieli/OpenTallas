#!/usr/bin/env python3
"""MESO-RECONCILE-1: HEAD lm_head pass added landing cycles with the reconciled count-aligned bind (vs old ring and the
MESO-INTEG-1 bind), via the shared tools/s81_head/fallback_land.head_pass on the part-granularity region table.
    head_tok.py PLAN.json REGIONS_part.json BIND.json [INTEG_BIND.json] [--base 9282 --window 10357]"""
import argparse
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo / "tools/die_plan"))
import importlib.util  # noqa: E402
import count_align_bind as CB  # noqa: E402
_spec = importlib.util.spec_from_file_location("s81_fallback_land", repo / "tools/s81_head/fallback_land.py")
FL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FL)

ap = argparse.ArgumentParser()
ap.add_argument("plan")
ap.add_argument("table")
ap.add_argument("bind")
ap.add_argument("integ_bind", nargs="?")
ap.add_argument("--base", type=int, default=9282, help="cycles/token without landings (LAND-HEAD 10-27 (1))")
ap.add_argument("--window", type=int, default=10357)
ap.add_argument("--out")
a = ap.parse_args()
plan, tab = json.load(open(a.plan)), json.load(open(a.table))
res = {}
for tag, bf in (("old_ring", None), ("reconciled", a.bind), ("integ1", a.integ_bind)):
    if tag != "old_ring" and not bf:
        continue
    t = tab if bf is None else CB.annotate_table(tab, json.load(open(bf)))
    h = FL.head_pass(plan, t)
    tot = h["total_added_cycles_per_head_pass"]
    res[tag] = dict(head_pass_crossings=h["head_pass_crossings"], path=h["path"], head_pass_added=h["added_cycles"],
                    gather_round_trip_added=h["gather_round_trip_added_cycles"], total_added=tot,
                    cycles_per_token=a.base + tot, window=a.window, slack=a.window - a.base - tot)
res["label"] = "UNCHECKED composition (base 9,282 cyc/token from LAND-HEAD 10-27); head_pass = shared fallback_land model"
print(json.dumps(res, indent=1))
if a.out:
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
