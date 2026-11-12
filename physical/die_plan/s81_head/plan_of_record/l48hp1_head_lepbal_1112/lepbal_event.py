#!/usr/bin/env python3
"""HEAD-LEP0N-BAL 11-12: plan event l48hp1_head_lepbal_1112 = fix2 (HEAD-94) + hd_lep0N per-port clock-arrival windows from the
paper check of the lep0N region-tree balance form (die clock config region.actual_max_region lep0N:UM, ot_clk / die_trial
--region-dme-actual-max-region; every other region byte-identical).
 usage: lepbal_event.py FIX2_PLAN.json[.gz] OUT.json KITWIN.json
per_port_ps[hd_lep0N][port] = min(per_type 200, need + 10), need = measured kit need (TT+FF, ceil 1 ps) on the balanced tree.
Fails closed if any hd_lep0N port needs more than its type window (the form did not balance).  Only hd_lep0N changes."""
import gzip, json, sys
from pathlib import Path
src = Path(sys.argv[1]); raw = gzip.open(src).read() if src.suffix == ".gz" else src.read_bytes()
P = json.loads(raw)
need = json.load(open(sys.argv[3]))["per_port_ps"]["hd_lep0N"]
TW = P["clock"]["tap_window"]
W = float(TW["per_type_ps"]["hd_lep0N"])
over = {p: v for p, v in need.items() if v > W}
if over:
    sys.exit(f"FAIL: hd_lep0N ports over the {W} ps type window on the balanced tree: {over}")
if TW["per_port_ps"].get("hd_lep0N"):
    sys.exit("FAIL: base plan already has hd_lep0N per_port_ps (unexpected base)")
TW["per_port_ps"]["hd_lep0N"] = {p: min(W, float(v) + 10.0) for p, v in sorted(need.items())}
TW["note"] = TW["note"] + (" | HEAD-LEP0N-BAL 11-12: hd_lep0N per_port_ps = need+10 capped at per_type 200 from the lep0N "
                           "region-tree balance paper check (region.actual_max_region lep0N)")
Path(sys.argv[2]).write_text(json.dumps(P, indent=1) + "\n")
v = TW["per_port_ps"]["hd_lep0N"]
print(f"hd_lep0N per_port_ps set on {len(v)} ports, max {max(v.values())}, min {min(v.values())}, max need {max(need.values())}")
