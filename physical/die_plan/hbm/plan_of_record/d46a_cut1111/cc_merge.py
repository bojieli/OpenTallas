"""hbm-channels-1111 core_conns: traced sidecar (core_conns_batch, no --base) merged per core with the base sidecar.
The bound-netlist trace wires only 281/2553 cores (cores behind split hierarchies trace as {} = glue escape), which
drops real core<->core wiring that the base sidecar carries (e.g. q_b112 SFU lanes).  Per core: traced entry when it
has wiring; otherwise the base entry with every ref that is not valid in this plan removed (stale bus/core names).
  cc_merge.py PLAN TRACED BASE OUT  -> OUT, OUT.merge_receipt.json"""
import json, sys, collections
P = json.load(open(sys.argv[1]))["partition_types"]; tr = json.load(open(sys.argv[2])); ba = json.load(open(sys.argv[3]))
out, rec = {}, {}
for t, ty in P.items():
    if not ty.get("hard_cores"): continue
    buses = {b["name"] for b in ty.get("buses", [])}; cores = [h["inst"] for h in ty["hard_cores"]]
    def ok(r):
        k, _, n = r.partition(":")
        if k == "bus": return n in buses
        if k == "core": return any(n == c or n.startswith(c + ".") for c in cores)
        return True
    o, c = {}, collections.Counter()
    for inst in cores:
        tv = tr.get(t, {}).get(inst) or {}
        if tv:
            o[inst] = tv; c["traced"] += 1; continue
        bv = ba.get(t, {}).get(inst) or {}
        kept = {p: [r for r in v if ok(r)] for p, v in bv.items()}
        dropped = sum(len(v) for v in bv.values()) - sum(len(v) for v in kept.values())
        kept = {p: v for p, v in kept.items() if v}
        o[inst] = kept; c["base" if kept else "empty"] += 1; c["stale_refs_dropped"] += dropped
    out[t] = o; rec[t] = dict(c)
json.dump(out, open(sys.argv[4], "w"), indent=1, sort_keys=True)
tot = collections.Counter()
for v in rec.values(): tot.update(v)
json.dump(dict(plan=sys.argv[1], traced=sys.argv[2], base=sys.argv[3], totals=dict(tot), types=rec), open(sys.argv[4] + ".merge_receipt.json", "w"), indent=1)
print(dict(tot))
