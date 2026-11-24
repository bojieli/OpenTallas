#!/usr/bin/env python3
"""KV-DIE-SEAMHOLD row (11-23): source-synchronous ring-hold alignment for forwarded landing rings.
usage: python3 -I ROWS_KV-DIE-SEAMHOLD.py PLAN_IN PLAN_OUT ; env SEAMHOLD_VALUES=<json {receiver_type: sender_ps}>
Sets clock.ring_hold.sender_ps_types[receiver] = measured min over that receiver's ring senders of
m_FF = min(data - fclk_out) at the sender port, minus 20 ps margin (values computed by mkvalues.py, recorded in the json
with their evidence). Only receivers whose every ring sender is measured are listed. No clock, period, tree or RTL change.
Existing per-type entries are kept unless the json lowers them (never raises a value already in the plan)."""
import json, os, sys
pin, pout = sys.argv[1], sys.argv[2]
vals = json.load(open(os.environ["SEAMHOLD_VALUES"]))
P = json.load(open(pin))
rh = P["clock"]["ring_hold"]
per = rh.setdefault("sender_ps_types", {})
types = set(p["type"] for p in P["partitions"]) | set(P.get("partition_types", {}))
out = {}
for tn, v in sorted(vals["sender_ps_types"].items()):
    if tn not in types: sys.exit(f"SEAMHOLD: receiver type {tn} not in plan")
    v = float(v)
    if v > 0: sys.exit(f"SEAMHOLD: {tn} sender_ps {v} > 0 refused (class values are <= 0)")
    old = per.get(tn)
    new = v if old is None else min(float(old), v)
    per[tn] = new; out[tn] = (old, new)
# no extra key in clock.ring_hold (schema additionalProperties false); evidence lives in the values json + hub post
json.dump(P, open(pout, "w"), indent=1)
for tn, (o, n) in out.items(): print(f"SEAMHOLD {tn}: {o} -> {n}")
print(f"SEAMHOLD rows {len(out)}")
