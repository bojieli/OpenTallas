"""DIE-KV-4: METHODOLOGY 12.15a strap kit list for the KV count-aligned crossings (no TYPE_SPLIT).
Per receiving partition TYPE: one kit, ring DEPTH per bus = max over the type's instances; per-instance constants
(ring K, origin PAD / EDGE_FALL) become strap_* pins tied at the parent; LEC per master against every constant variant
used (variant = the tuple of strap values of one instance).  Also writes the TYPE_SPLIT list (dropped by OWNER) for the record.
strap_list.py CA_JSON PLAN REGIONS OUT_JSON"""
import json, sys
from collections import defaultdict
ca, plan, regf, outf = sys.argv[1:5]
ca = json.load(open(ca)); plan = json.load(open(plan)); part_region = json.load(open(regf))["part_region"]
ports = {p["id"]: p for p in plan["ports"]}
ptype = {p["name"]: p["type"] for p in plan["partitions"]}
region_part = defaultdict(list)
for p, r in part_region.items():
    region_part[r].append(p)
origin = {g["region"]: g["start_from"] for g in ca["regions"]}
per_inst = defaultdict(dict)    # part -> {bus: (K, DEPTH)}
for c in ca["crossings"]:
    p = ports[c["port"]]
    dp, db = p["dst"]["part"], p["dst"]["bus"]
    per_inst[dp][db] = (c["K"], c["depth"])
types = defaultdict(list)
for part in ptype:
    if part in per_inst or any(part in v for v in region_part.values()):
        types[ptype[part]].append(part)
out = {}
for tn, parts in sorted(types.items()):
    buses = sorted({b for q in parts for b in per_inst.get(q, {})})
    if not buses:
        continue
    depth = {b: max(per_inst[q][b][1] for q in parts if b in per_inst.get(q, {})) for b in buses}
    var = {}
    for q in parts:
        reg = part_region[q]
        o = origin.get(reg) or {}
        is_origin_part = sorted(region_part[reg])[0] == q  # origin sits in one partition of the region (ca-origin relay)
        sig = (tuple(per_inst.get(q, {}).get(b, (None,))[0] for b in buses),
               (o.get("rtl", {}).get("PAD"), o.get("rtl", {}).get("EDGE_FALL")) if o and is_origin_part else None)
        var.setdefault(json.dumps(sig), []).append(q)
    out[tn] = dict(instances=len(parts), ca_buses=len(buses), depth_max={str(k): sum(1 for v in depth.values() if v == k) for k in (4, 8)},
                   strap_pins=dict(K=len(buses), K_bits=len(buses) * 5, origin=["strap_cland_pad", "strap_cland_edge_fall"]),
                   lec_variants=len(var), type_split_variants=len(var),
                   variants=[dict(instances=v) for v in var.values()])
summ = dict(types=len(out), strap_kits=len(out), lec_runs=sum(t["lec_variants"] for t in out.values()),
            type_split_kits_dropped=sum(t["type_split_variants"] for t in out.values()),
            d8_buses=sum(t["depth_max"].get("8", 0) for t in out.values()),
            note="strap form (OWNER 12.15a): one kit per type, DEPTH per bus = max over instances, K/PAD/EDGE_FALL strap_* tied "
                 "at the parent (1.8: declared, quasi-static false_path, TIEHI/TIELO at the pin, LEC per used variant). K width "
                 "5 bits signed per ring is an ESTIMATE (K range in this plan); K frame = region (multi-partition regions take the "
                 "ca-origin partition-frame offset at bind, UNCHECKED here)")
json.dump(dict(summary=summ, types=out), open(outf, "w"), indent=1)
print(json.dumps(summ))
for tn, t in sorted(out.items(), key=lambda kv: -kv[1]["lec_variants"])[:12]:
    print(tn, {k: t[k] for k in ("instances", "ca_buses", "depth_max", "lec_variants")})
