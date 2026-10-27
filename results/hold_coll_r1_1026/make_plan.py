#!/usr/bin/env python3
"""HOLD-COLL-R1 10-26 canary plan: main QC die_plan.json + HOLD-REPAIR mesh20_flat plan_hold_demand fragment with
clock.hold_demand.ft_owner = "sender" (gen_phys.ft_hold_owner) + coll_ftc plan per-tap sizing (12.8 d1):
tap_max_sinks 1500 -> 600, tap_radius_um 250 -> 100.  Evidence (Codex HB4 GRT odb, placement-RC probe, TT): taps
<= ~600 sinks / <= ~120 um extent spread <= 13 ps; 1000-1500-sink taps over 120-270 um spread 30-104 ps; s0 face
banks 193.5-297.0 ps vs common 250.  Then:
  python3 -I tools/die_plan/gen.py phys physical/die_plan/qwen_compute/hcr1_mesh20_sender.json --out $D/gen_sender \
      --types coll_ftc --rtl-root $W --hold-ff-margin 5
  ot-run --mem 24 --threads 8 --dir $D -- bash $D/gen_sender/run_kit.sh $D/gen_sender/coll_ftc route 24 8"""
import json, sys
from pathlib import Path
W = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
P = json.loads((W / "physical/die_plan/qwen_compute/die_plan.json").read_text())
hd = json.loads((W / "results/hold_repair_1026/mesh20_flat/plan_hold_demand.json").read_text())
hd["ft_owner"] = "sender"
P["clock"]["io_hold"] = "plan_demand"
P["clock"]["hold_demand"] = hd
t = P["partition_types"]["coll_ftc"]
t["clock"]["tap_max_sinks"] = 600
t["clock"]["tap_radius_um"] = 100.0
t["note"] += (" | HOLD-COLL-R1 10-26 plan per-tap sizing (12.8 d1): taps <=600 sinks, radius 100 um (probe: <=600-sink "
              "compact taps spread <=13 ps TT; 1000-1500-sink taps 30-104 ps)")
(W / "physical/die_plan/qwen_compute/hcr1_mesh20_sender.json").write_text(json.dumps(P, indent=1))
