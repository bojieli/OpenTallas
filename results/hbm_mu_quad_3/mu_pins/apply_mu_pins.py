#!/usr/bin/env python3
"""apply_mu_pins.py PLAN_DIR [--all-instances]: copy the MU template tables (mu_pins/cores) into PLAN_DIR/cores and set
pins_file on the q_hub_nw / q_hub_ne hard cores of those modules whose pins_file is None (default) or, with
--all-instances, on every instance of the module (one table per module).  Idempotent; rewrites die_plan.sha256."""
import json, sys, shutil, hashlib
from pathlib import Path
here = Path(__file__).resolve().parent
plan = Path(sys.argv[1]); allinst = "--all-instances" in sys.argv
man = json.loads((here / "mu_pins_manifest.json").read_text())
(plan / "cores").mkdir(exist_ok=True)
P = json.loads((plan / "die_plan.json").read_text())
n = 0; left = []
for mod, m in man["modules"].items():
    shutil.copyfile(here / m["pins_file"], plan / m["pins_file"])
for tn in ("q_hub_nw", "q_hub_ne"):
    for h in P["partition_types"][tn]["hard_cores"]:
        m = man["modules"].get(h["module"])
        if m and (allinst or not h.get("pins_file")):
            if h.get("pins_file") != m["pins_file"]:
                h["pins_file"] = m["pins_file"]; n += 1
        elif not h.get("pins_file"):
            left.append(f"{tn}:{h['inst']}({h['module']})")
s = json.dumps(P, indent=1) + "\n"
(plan / "die_plan.json").write_text(s)
(plan / "die_plan.sha256").write_text(hashlib.sha256(s.encode()).hexdigest() + "  die_plan.json\n")
print(json.dumps(dict(set=n, still_none=left, blockers=man["blockers"])))
