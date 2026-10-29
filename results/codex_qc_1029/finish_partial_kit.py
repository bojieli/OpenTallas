#!/usr/bin/env python3
"""Finish only the STA wrapper/manifest after a completed clock build.

QC baseline26 completed every expensive artifact before missing native core
pin tables stopped the final die-top wrapper. Reuse those artifacts; require
the template's exact same plan and unchanged non-clock generation settings.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

parser = argparse.ArgumentParser(description=__doc__)
for option in ("kit", "template", "plan", "tools"):
    parser.add_argument("--"+option, type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.tools))
import schema as S
import gen_rtl
import die_trial as DT

meta = json.loads(args.template.read_text())
plan_sha = hashlib.sha256(args.plan.read_bytes()).hexdigest()
if meta["plan_sha256"] != plan_sha:
    raise ValueError("partial kit and template must use the identical plan")
tree = json.loads((args.kit/"clock/tree.json").read_text())
old_clock = meta["clock_tree"]
for key in ("leaf_um", "rep_um", "tree_form", "clock_cell", "clock_rc", "tap_load_ff", "taps"):
    if old_clock.get(key) != tree["meta"].get(key):
        raise ValueError(f"non-calibration clock setting differs: {key}")
physical = S.Plan(S.load(args.plan), args.plan)
modules = DT.standin_module_names(physical)
for tn, module in modules.items():
    artifact = args.kit/"sta/parts"/module/"6_final.v"
    if not artifact.is_file() or f"module {module} (" not in artifact.read_text():
        raise ValueError(f"missing completed stand-in: {tn}")
for filename in ("clock/ctree.v", "clock/ctree.tcl", "grt/route.v", "grt/grt.tcl", "grt/obs.tcl"):
    if not (args.kit/filename).is_file():
        raise ValueError(f"missing completed artifact: {filename}")
v = DT.retarget_shared_modules(physical, gen_rtl.die_top(physical, gen_rtl.bus_epochs(physical), {}), modules)
plain = "\n".join(re.sub(r"^endmodule\s*:.*$", "endmodule", line)
                  for line in v.splitlines() if not line.startswith("`"))
(args.kit/"sta/die_top.v").write_text(plain+"\n")
meta = copy.deepcopy(meta)
meta["plan"] = str(args.plan)
meta["clock_tree"] = tree["meta"]
_, band_rects = DT.band_region_adjust(physical, meta["grt"]["adjust"]["M4"])
obstructions = sum(line.startswith("create_obstruction ")
                   for line in (args.kit/"grt/obs.tcl").read_text().splitlines())
reserve_count = obstructions-len(DT.pg_stripes(physical))-len(DT.band_share_obs(physical,band_rects))
if reserve_count < 0:
    raise ValueError("negative clock reservation inventory")
meta["grt"]["clock_reserve_rects"] = reserve_count
meta["resume"] = dict(reason="native pin tables missing at final STA-wrapper step; physical artifacts preserved",
                      template=str(args.template), same_plan_sha256=plan_sha,
                      completed_clock_sha256=hashlib.sha256((args.kit/"clock/tree.json").read_bytes()).hexdigest(),
                      clock_rebuilt=False, sta_wrapper_finished=True)
for filename in ("run_clock.sh", "run_grt.sh", "run_psm.sh"):
    (args.kit/filename).chmod(0o755)
(args.kit/"kit.json").write_text(json.dumps(meta, indent=1)+"\n")
print("QC_PARTIAL_KIT_FINISHED", tree["meta"]["taps"], "taps; clock generation not repeated")
