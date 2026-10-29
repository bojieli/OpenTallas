#!/usr/bin/env python3
"""DIE-S81-4: OWNER 12.15 (coord 10475553e) spice-scaled die clock for the die STA gate: every clock-network arrival of a
die_sta_related proof (tap late/early, tree-node late/early, CPPR node range) x S (TT 1.0485, FF 1.0552); slews kept.
    spice_scale_proof.py IN_DIR OUT_DIR TT=1.0485,FF=1.0552"""
import json, shutil, sys
from pathlib import Path
src, dst, sc = Path(sys.argv[1]), Path(sys.argv[2]), dict(kv.split("=") for kv in sys.argv[3].split(","))
dst.mkdir(parents=True, exist_ok=True)
for f in src.iterdir():
    if not f.name.startswith("tap_arrivals_"):
        shutil.copy(f, dst / f.name)
for C, s in sc.items():
    s = float(s)
    d = json.loads((src / f"tap_arrivals_{C}.json").read_text())
    for k in ("node_late_ps", "node_early_ps", "cppr_node_range_ps"):
        d[k] = {n: v * s for n, v in d[k].items()}
    for t in d["taps"]:
        t["late_ps"] *= s
        t["early_ps"] *= s
    d["spice_scale"] = s
    (dst / f"tap_arrivals_{C}.json").write_text(json.dumps(d))
    print(C, "scaled", s, len(d["taps"]))
