#!/usr/bin/env python3
"""QC-MEM9 11-08 plan event: bind the eight QC SU lanes to the EXTRA9 memory-transport head.

Adds memory_read_extra=9 to the bound_group of every hard core of qfd_qc_su_lane_w_l0..7 (bound_groups.materialize ->
qc_su_lane_cut.cut -> rtl/physical/qfd_qc_su_lane_w_l*.sv, head rtl/physical/qfd_dv_lane_h_su_mem9.sv).  No pin, outline,
macro, lane or latency field changes; the 9 extra edges sit inside the core head (parent request 5 + answer 4).
    qc_su_mem9_event.py PLAN.json OUT.json [--extra 9]   -> prints {n_groups, modules, sha256}
"""
import argparse, hashlib, json, re
from pathlib import Path

MODS = {f"qfd_qc_su_lane_w_l{l}" for l in range(8)}
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("plan", type=Path); ap.add_argument("out", type=Path); ap.add_argument("--extra", type=int, default=9)
a = ap.parse_args()
if a.out.exists():
    raise SystemExit(f"refusing to overwrite {a.out}")
d = json.loads(a.plan.read_text())
n, mods = 0, set()
for tn, t in d["partition_types"].items():
    for h in t.get("hard_cores") or []:
        if h.get("module") in MODS:
            bg = h.get("bound_group")
            if not bg or bg.get("kind") != "exact_post_bind_group":
                raise SystemExit(f"{tn}/{h['inst']}: expected an exact post-bind group")
            if bg.get("memory_alignment") != 3 or bg.get("kv_wr_pipe") != 1:
                raise SystemExit(f"{tn}/{h['inst']}: unexpected head contract")
            bg["memory_read_extra"] = a.extra
            n += 1; mods.add(h["module"])
if mods != MODS:
    raise SystemExit(f"modules touched {sorted(mods)} != the eight lanes")
out = json.dumps(d, indent=1) + "\n"
a.out.write_text(out)
print(json.dumps(dict(n_groups=n, modules=sorted(mods), extra=a.extra, sha256=hashlib.sha256(out.encode()).hexdigest())))
