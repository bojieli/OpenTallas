#!/usr/bin/env python3
"""stage_native_fixed_sync.py PLAN OUT ASBUILT BIND_LATENCY RECEIPT [--base BASE_PLAN]

B4b (ready12b-A): REACH-FIX-2 adds source registers on native-station buses (internal_stations bus:<out> rows of
as-built internal_stations_types) but leaves lanes[].fixed_cycles at the old depth, so bind's native_istations
check fails ("fixed_cycles must equal source N + destination M").  Sync: for every plan lane with fixed_cycles whose
source type is a native-station type, fixed_cycles := max source regs + max destination regs (bind's own rule).
Lane topology (src/dst/bus_out/bus_in) from a bind_latency.json of the same partition graph.  With --base, a lane
is only changed if BASE satisfied the rule (so a pre-existing mismatch is reported, not hidden)."""
import json
import sys


def need(P, sel, L):
    pm = {p["name"]: p["type"] for p in P["partitions"]}
    st, dt = pm.get(L["src"]), pm.get(L["dst"])
    if st not in sel:
        return None
    src = [len(e["regs_um"]) for e in P["partition_types"][st].get("internal_stations") or []
           if e.get("conn") == "bus:" + L["bus_out"]]
    if not src:
        return None
    dst = [len(e["regs_um"]) for e in P["partition_types"].get(dt, {}).get("internal_stations") or []
           if e.get("conn") == "bus:" + L["bus_in"]]
    return max(src) + max(dst, default=0)


def main(a):
    plan, out, ab, bl, rcpt = a[:5]
    base = a[a.index("--base") + 1] if "--base" in a else None
    P = json.load(open(plan))
    sel = set(json.load(open(ab)).get("internal_stations_types") or [])
    topo = {b["lane"]: b for b in json.load(open(bl))["buses"] if b.get("lane")}
    B = json.load(open(base)) if base else None
    blanes = {x["id"]: x for x in B["lanes"]} if B else {}
    changed, kept_base_mismatch = [], []
    for L in P["lanes"]:
        if "fixed_cycles" not in L or L["id"] not in topo:
            continue
        n = need(P, sel, topo[L["id"]])
        if n is None or int(L["fixed_cycles"]) == n:
            continue
        if B is not None:
            nb = need(B, sel, topo[L["id"]])
            if nb is not None and int(blanes.get(L["id"], {}).get("fixed_cycles", -1)) != nb:
                kept_base_mismatch.append([L["id"], L["fixed_cycles"], n])
                continue
        changed.append([L["id"], topo[L["id"]]["src"], topo[L["id"]]["dst"], L["fixed_cycles"], n])
        L["fixed_cycles"] = n
    json.dump(P, open(out, "w"), indent=1)
    json.dump(dict(stage="native_fixed_sync", lanes_changed=changed, n=len(changed),
                   base_mismatch_kept=kept_base_mismatch), open(rcpt, "w"), indent=1)
    print("native_fixed_sync lanes", len(changed), "base-mismatch kept", len(kept_base_mismatch),
          [c[0] for c in changed][:20])


if __name__ == "__main__":
    main(sys.argv[1:])
