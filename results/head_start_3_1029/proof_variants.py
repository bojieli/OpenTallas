#!/usr/bin/env python3
"""HEAD-START-3 proof variants for the BUFx8 local clock entry (no BUFx8 row in SPICE_CLOCK_CAL_CELL -> spice_cell fails
closed).  BUF envelope = per corner/key the bounding factor over BUFx4/BUFx6f/BUFx24 (late MAX, early MIN), UNCHECKED proxy.
  k: component form for --sta-clock-cal spice_edge: each __st__ tap = node (inverter tree, spice_edge inv factor) + leg
     (node Y -> local BUF8 -> FF CLK) at the BUF envelope factor; stored pre-divided by the inv factor so that the gate's
     uniform spice_edge scaling yields node*f_inv + leg*f_buf exactly.
  s: literal spice_cell bound: __st__ clock_masters = CKINVDCx16 + BUFx4 + BUFx6f + BUFx24 (proxy set for BUFx8)."""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
import die_sta_related as D
src = Path(sys.argv[1]); base = Path(sys.argv[2])
BUFS = ("BUFx4_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R")
for v in ("k", "s"):
    out = base / f"proof_r1{v}"
    out.mkdir(exist_ok=True)
    for f in ("mesh.json", "droop_regions.json"):
        shutil.copy(src / f, out / f)
    for C in ("TT", "FF"):
        d = json.loads((src / f"tap_arrivals_{C}.json").read_text())
        fi, fie = D.SPICE_CLOCK_CAL_INV[C], D.SPICE_CLOCK_CAL_INV_EARLY[C]
        env = {k: (max if k.endswith("late") else min)(D.SPICE_CLOCK_CAL_CELL[b][C][k] for b in BUFS)
               for k in ("rise_late", "rise_early", "fall_late", "fall_early")}
        for t in d["taps"]:
            if not t["port"].startswith("__st__"):
                continue
            p = t["tree_path"]
            if v == "s":
                t["clock_masters"] = ["CKINVDCx16_ASAP7_75t_R", *BUFS]
                continue
            for key, nk, fk, fd in (("late_ps", "node_late_ps", "rise_late", fi), ("early_ps", "node_early_ps", "rise_early", fie),
                                    ("fall_late_ps", "node_fall_late_ps", "fall_late", fi),
                                    ("fall_early_ps", "node_fall_early_ps", "fall_early", fie)):
                n = float(d[nk][p]); leg = float(t[key]) - n
                t[key] = n + leg * env[fk] / fd
            t["component_cal"] = dict(note="node x inv spice_edge + leg x BUF envelope (BUFx8 proxy, UNCHECKED)", env=env)
        d["basis"] += f" | variant {v} (proof_variants.py)"
        (out / f"tap_arrivals_{C}.json").write_text(json.dumps(d, indent=0) + "\n")
    print(v, "ok")
