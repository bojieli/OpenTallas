#!/usr/bin/env python3
"""Copy a route's physical.json / corner_sta.json into routes/<label>/ and print the sign-off numbers."""
import json, shutil, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
for n in ("physical.json", "corner_sta.json", "exit"):
    if (src / n).exists():
        shutil.copy(src / n, dst / n)
c = json.loads((src / "corner_sta.json").read_text())
p = json.loads((src / "physical.json").read_text())
pr = p.get("place_and_route", {})
area = None
for k in ("cell_area_um2", "design_area_um2", "area_um2"):
    if k in pr: area = pr[k]
ss, ff = c["setup_ss"], c["hold_ff"]
print(json.dumps({"label": dst.name, "closes_signoff": c.get("closes_signoff"),
                  "ss_r2r_ps": ss["worst_reg_to_reg_slack_ps"], "ss_worst_ps": ss["worst_slack_ps"],
                  "ss_in_ps": ss.get("worst_input_to_reg_slack_ps"), "ss_out_ps": ss.get("worst_output_port_slack_ps"),
                  "ff_hold_ps": ff["worst_slack_ps"], "area": area, "status": p.get("status")}))
