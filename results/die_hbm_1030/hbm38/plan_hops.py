#!/usr/bin/env python3
"""DIE-HBM-38: per-slot hop stats of a G2 partition probe on the PLANNED station targets (probe.tcl place_inst
locations, before detailed placement) vs the actual post-DPL dump (insts.tsv). usage: plan_hops.py PROBE_DIR TOOLS_DIR"""
import sys, re, json, tempfile, shutil, os
d, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
from proto_geometry import hop_stats
t = open(d + "/probe.tcl").read()
tmp = tempfile.mkdtemp()
for f in ("probe.tcl", "io.tcl"):
    os.symlink(os.path.abspath(d + "/" + f), tmp + "/" + f)
W, H = 1.08, 0.27   # DFFHQNx1 footprint (centre offset only)
with open(tmp + "/insts.tsv", "w") as fh:
    for m in re.finditer(r"place_inst -name (st_\S+) -location \{([\d.]+) ([\d.]+)\}", t):
        x, y = float(m[2]), float(m[3])
        fh.write(f"{m[1]}\tDFFHQNx1_ASAP7_75t_R\t{x}\t{y}\t{x+W}\t{y+H}\n")
pl = hop_stats(tmp)
out = {"planned": {k: pl.get(k) for k in ("max_hop_um", "over_reach", "over_reach_bits", "st_in_core_slots")}}
if os.path.exists(d + "/insts.tsv"):
    ac = hop_stats(d)
    out["actual"] = {k: ac.get(k) for k in ("max_hop_um", "over_reach", "over_reach_bits", "st_in_core_slots")}
shutil.rmtree(tmp)
print(json.dumps(out, indent=1))
