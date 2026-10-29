#!/usr/bin/env python3
"""KV-KITS-22 census: the 55 KV partition types without a kit view (DIE-KV-28 sta_E_edge missing_views) ->
family, instances, hard-core modules, which of them lack a signed view, and the first blocker.
usage: census.py PLAN_E27F SIGNED_MODULES(comma) MISSING_TYPES_FILE OUT_TSV"""
import json, sys, collections, hashlib
plan, signed, miss, out = sys.argv[1], set(sys.argv[2].split(",")), sys.argv[3], sys.argv[4]
P = json.load(open(plan))
T = P["partition_types"]
inst = collections.Counter(p["type"] for p in P["partitions"])
types = [l.strip() for l in open(miss) if l.strip()]
rows = []
for tn in types:
    t = T[tn]
    hc = collections.Counter(h["module"] for h in t.get("hard_cores", []))
    unsigned = sorted(m for m in hc if m not in signed)
    fam = tn.split("__")[0]
    fam = ("hgi" if fam.startswith("kv3_hgi") else "hg" if fam.startswith("kv3_hg") else "pc" if fam.startswith("kv3_pc")
           else "phy" if fam.startswith("kv3_phy") else "pv" if fam.startswith("kv3_pv") else fam.replace("kv3_", ""))
    if t.get("hard"):
        block = "HARD-MODEL type: gen_phys emits no kit for hard types (PHY blackbox + registered wrapper) -> ASK"
    elif unsigned:
        block = "core views missing: " + ",".join(unsigned)
    else:
        block = "NONE (no hard core) -> kit after event27f strict bind + provider import (DIE-KV-29)"
    rows.append((fam, tn, inst[tn], bool(t.get("hard")), "x".join(map(str, t["outline_um"])), len(hc),
                 ",".join(f"{m}x{n}" for m, n in sorted(hc.items())), block))
with open(out, "w") as f:
    f.write("#family\ttype\tinstances\thard\toutline_um\thard_core_types\thard_cores\tfirst_blocker\n")
    for r in sorted(rows):
        f.write("\t".join(map(str, r)) + "\n")
s = collections.Counter(r[7].split(":")[0] for r in rows)
print(json.dumps(dict(types=len(rows), plan_sha256=hashlib.sha256(open(plan, "rb").read()).hexdigest()[:12],
                      by_blocker=s, instances=sum(r[2] for r in rows))))
