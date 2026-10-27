#!/usr/bin/env python3
"""HBM-MU-QUAD-3 compose: planS2 bundle + unified quad hub types (NW/NE) + SPANNING die growth (hbm_r11_delta.grow_die_span:
every partition that spans the growth line grows with it, so the hub-row columns NW/NE_io, b0xx and the root keep abutting
the shifted rows above) -> planU3.  Usage: compose3.py TOOLS planS2_dir NW.json NE.json out_dir"""
import json, sys, shutil, hashlib, pathlib
tools, s2, nw, ne, out = sys.argv[1:6]
sys.path.insert(0, tools); import hbm_r11_delta as R11
out = pathlib.Path(out)
if out.exists(): raise SystemExit("exists")
shutil.copytree(s2, out, ignore=shutil.ignore_patterns("die_plan.json", "die_plan.sha256", "gates*"))
P = json.load(open(pathlib.Path(s2) / "die_plan.json"))
H_old = P["partition_types"]["q_hub_nw"]["outline_um"][1]
for tn, f in (("q_hub_nw", nw), ("q_hub_ne", ne)):
    t = json.load(open(f)); old = P["partition_types"][tn]
    assert old["outline_um"][0] == t["outline_um"][0]
    P["partition_types"][tn] = t
H_new = P["partition_types"]["q_hub_nw"]["outline_um"][1]
P["station_model_keys"] = True   # opt-in: R8-R13 internal-station model keys (schema.STATION_MODEL_PROPS)
rep = R11.grow_die_span(P, ["NW_hub", "NE_hub"], H_old, H_new)
s = json.dumps(P, indent=1) + "\n"
(out / "die_plan.json").write_text(s)
(out / "die_plan.sha256").write_text(hashlib.sha256(s.encode()).hexdigest() + "  die_plan.json\n")
(out / "compose_report.json").write_text(json.dumps(dict(H_old=H_old, H_new=H_new, growth=rep), indent=1) + "\n")
d = P["die"]["outline_um"]
print(json.dumps(dict(sha=hashlib.sha256(s.encode()).hexdigest()[:12], die=d, area_mm2=round(d[0] * d[1] / 1e6, 3), dH=rep["dH_um"], ys=rep["insertion_y_um"],
      grown=rep["grown_types"], span=len(rep["spanning_partitions"]), moved=rep["moved_partitions"], win=rep["windows_moved"], hubwin=rep["hub_windows_moved"],
      added_regs=rep["added_regs"], fails=len(rep["restation_fails"]))))
