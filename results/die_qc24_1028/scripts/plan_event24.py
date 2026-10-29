#!/usr/bin/env python3
"""DIE-QC-24 plan event ev_qc24 = ev_qc23pg (ad01d656b2b5) - the 12 sl_*_st_a__flt__0 fault hops (COORD 10-28 21:24/21:4x).
The release QC RTL collects the st_a station fault inside the slice (u_r0.fault -> u_ctl.stn_fault -> any_fault -> status
st / ag_own; rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv); the bound fw leaf has no flt_st_a_i pin.  Same edit as the generator
(physical/die_plan/qwen_compute/gen_plan.py FAULT_LOCAL_SLICE) and as the TOK-QC-2 recorded delta (mk_ca_event.py), so plan
and bind come from one RTL lineage.  Ports, lanes, latency lanes, the two u_pstn buses and every clock reference go.
usage: plan_event24.py IN OUT"""
import json, re, sys, hashlib
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
P = json.loads(src.read_text())
DROP = [x["id"] for x in P["ports"] if re.fullmatch(r"sl_[EW]\d_st_a__flt__0", x["id"])
        and x["dst"]["bus"] == "flt_st_a_i" and x["src"]["bus"] == "flt_o"]
assert len(DROP) == 12, DROP
P["ports"] = [x for x in P["ports"] if x["id"] not in DROP]
P["lanes"] = [l for l in P["lanes"] if not set(l["ports"]) & set(DROP)]
tp = {x["name"]: x["type"] for x in P["partitions"]}
for part, bus in [(re.sub("st_a__flt__0", "fw", d), "flt_st_a_i") for d in DROP] + \
                 [(re.sub("__flt__0", "", d), "flt_o") for d in DROP]:
    t = P["partition_types"][tp[part]]
    t["buses"] = [b for b in t["buses"] if b["name"] != bus]
for k in {re.sub(r"__0$", "", d) for d in DROP}:
    P["latency"]["lanes"].pop(k, None)
def _prune(o):
    if isinstance(o, list):
        o[:] = [x for x in o if not (isinstance(x, dict) and any(str(x.get("id", "")).endswith(d) for d in DROP))]
        for x in o:
            _prune(x)
    elif isinstance(o, dict):
        for x in o.values():
            _prune(x)
_prune(P["clock"])
s = json.dumps(P)
assert not any(d in s for d in DROP), "dropped port still referenced"
left = s.count("flt_st_a_i")
dst.write_text(json.dumps(P, indent=1) + "\n")
print("ev_qc24", hashlib.sha256(dst.read_bytes()).hexdigest()[:12], "from", hashlib.sha256(src.read_bytes()).hexdigest()[:12],
      "dropped", len(DROP), "ports_left", len(P["ports"]), "flt_st_a_i refs left", left)
