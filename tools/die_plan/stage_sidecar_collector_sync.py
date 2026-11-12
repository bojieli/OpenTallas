#!/usr/bin/env python3
"""stage_sidecar_collector_sync.py PLAN SIDECAR_IN SIDECAR_OUT RECEIPT [--expect N]

B3b (ready12b-A, COORD/GEN-CLASS-1 11-12): the landing sidecar's collector.types[tn].local_sources must name the
same buses as the plan's partition_types[tn].clock.landing_contract.collector_local_sources.  DIE-S81-85
S4N-FTLANE-1111 moved ft slot dn_s_4N_L0x2 from s_4N_L3 (t44cl) to s_5N_L1 (t52) in the plan only, so
clock_landing_verify finds no local source for port dn_s_4N_L0_1 (StopIteration / CLAND_SIDECAR_LOCAL_SOURCE_MISSING).

Sync, fail-closed:
  * only types whose local-source NAME sets differ change; their local_sources := the plan's list (verbatim);
  * mask.inputs follows when it held exactly the old name set (the collector's input list is the same set);
  * the per-type source count must equal the plan's afterwards;
  * every moved bus must be an input of the plan type: a `<slot>_i` of its ft_slots or a landing-contract pin;
  * a moved bus named in collector.edges / parts / any other collector entry outside .types refuses the stage;
  * --expect N: refuse unless exactly N types change.
Receipt: types changed, bus moves (from type -> to type), in/out sha256."""
import hashlib
import json
import sys


def names(lst):
    return sorted(x["name"] for x in lst or [])


def plan_inputs(pt):
    s = {"%s_i" % sl["name"] for sl in pt.get("ft_slots") or [] if sl.get("name")}
    lc = (pt.get("clock") or {}).get("landing_contract") or {}
    s |= {x["name"] for x in lc.get("collector_local_sources") or []}
    return s


def sync(P, S, expect=None):
    T = S["collector"]["types"]
    changed, moves = [], {}
    for tn, t in sorted(T.items()):
        pt = P["partition_types"].get(tn)
        if pt is None:
            continue
        pl = ((pt.get("clock") or {}).get("landing_contract") or {}).get("collector_local_sources") or []
        a, b = names(t.get("local_sources")), names(pl)
        if a == b:
            continue
        for bus in set(b) - set(a):
            moves.setdefault(bus, {})["to"] = tn
            if bus not in {"%s_i" % sl["name"] for sl in pt.get("ft_slots") or []}:
                raise SystemExit("SIDECAR-SYNC %s: added bus %s is not an ft slot input of the plan type" % (tn, bus))
        for bus in set(a) - set(b):
            moves.setdefault(bus, {})["from"] = tn
        m = t.get("mask") or {}
        mask_follow = sorted(m.get("inputs") or []) == a
        t["local_sources"] = json.loads(json.dumps(pl))
        if mask_follow:
            m["inputs"] = b
        if len(t["local_sources"]) != len(pl):
            raise SystemExit("SIDECAR-SYNC %s: source count %d != plan %d" % (tn, len(t["local_sources"]), len(pl)))
        changed.append(dict(type=tn, before=a, after=b, mask_inputs_followed=mask_follow))
    rest = json.dumps({k: v for k, v in S["collector"].items() if k != "types"})
    for bus in moves:
        if '"%s"' % bus in rest:
            raise SystemExit("SIDECAR-SYNC: moved bus %s is referenced outside collector.types" % bus)
    if expect is not None and len(changed) != expect:
        raise SystemExit("SIDECAR-SYNC: %d types would change, expected %d" % (len(changed), expect))
    return changed, moves


def main(a):
    plan, si, so, rc = a[:4]
    expect = int(a[a.index("--expect") + 1]) if "--expect" in a else None
    P = json.load(open(plan))
    raw = open(si, "rb").read()
    S = json.loads(raw)
    changed, moves = sync(P, S, expect)
    out = json.dumps(S, indent=1).encode() if changed else raw
    open(so, "wb").write(out)
    rec = dict(stage="sidecar_collector_sync", plan=plan, plan_sha256=hashlib.sha256(open(plan, "rb").read()).hexdigest(),
               in_file=si, in_sha256=hashlib.sha256(raw).hexdigest(), out_file=so,
               out_sha256=hashlib.sha256(out).hexdigest(), types_changed=changed, bus_moves=moves)
    json.dump(rec, open(rc, "w"), indent=1)
    print("SIDECAR-SYNC", si.rsplit("/", 1)[-1], "types", len(changed), "moves", moves,
          "out", rec["out_sha256"][:12])


if __name__ == "__main__":
    main(sys.argv[1:])
