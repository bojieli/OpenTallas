#!/usr/bin/env python3
"""S81 RF-EG (DIE-S81-54/EG 11-04): landed sidecar collector trees of the 16 C types follow the plan collector_tree:
core_resets (u_c.u_eg -> u_nh/u_nk/u_gg), n_clock_taps, n_reset_consumers.  Every other tree key must already match.
    python3 sync_sidecar_eg.py PLAN SIDECAR"""
import json, sys
pf, sf = sys.argv[1:]
plan = json.load(open(pf)); txt = open(sf).read(); side = json.loads(txt)
assert json.dumps(side, separators=(",", ":")) == txt, "sidecar is not in compact form"
KEYS = {"core_resets", "n_clock_taps", "n_reset_consumers"}; n = 0
for tn, t in plan["partition_types"].items():
    if not any(c["inst"] == "u_c.u_eg.u_gg" for c in t.get("hard_cores") or []): continue
    a = side["collector"]["types"][tn]["tree"]; b = t["clock"]["landing_contract"]["collector_tree"]
    assert {k for k in set(a) | set(b) if a.get(k) != b.get(k)} == KEYS, tn
    for k in KEYS: a[k] = b[k]
    n += 1
assert n == 16, n
open(sf, "w").write(json.dumps(side, separators=(",", ":"))); print("sync_sidecar_eg OK", n)
