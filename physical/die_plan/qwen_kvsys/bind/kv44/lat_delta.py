#!/usr/bin/env python3
"""KV-BIND 10-24: landed-latency deltas of the kv44 bound top vs kv41 (bound_pv) and kv42 (bound_kv42) per landing member
(sink leaf.port[bits] <- source @ as-built), grouped by (source leaf class, sink port) with bit counts.
    lat_delta.py KV44_BUS_GROUPS KV41_BUS_GROUPS(.gz) KV42_BUS_GROUPS(.gz) OUT.json"""
import collections, gzip, json, re, sys


def load(f):
    d = json.load(gzip.open(f) if f.endswith(".gz") else open(f))
    r = {}
    for g in d["landing"]:
        for m in g["members"]:
            k = f"{g['sink']}.{m['sink_port']}{json.dumps(m['sink_bits'])}<-{m['source']}@{m['asbuilt_stages']}"
            r[k] = dict(bound=m["bound_stages"], landed=m["landed_stages"], bits=sum(h - l + 1 for l, h in m["sink_bits"]),
                        sink=g["sink"], port=m["sink_port"], src=m["source"])
    return r


def cls(s):
    return re.sub(r"_(EN|ES|WN|WS)(_\d+)?", "_Q", re.sub(r"_\d+(?=__|$)", "_n", s))


def diff(a, b):
    out = collections.defaultdict(lambda: dict(members=0, bits=0, d_bound=collections.Counter(), d_landed=collections.Counter()))
    for k in a.keys() & b.keys():
        u, v = a[k], b[k]
        if (u["bound"], u["landed"]) == (v["bound"], v["landed"]):
            continue
        o = out[f"{cls(v['src'])} -> {cls(v['sink'])}.{v['port']}"]
        o["members"] += 1; o["bits"] += v["bits"]
        o["d_bound"][v["bound"] - u["bound"]] += 1; o["d_landed"][v["landed"] - u["landed"]] += 1
    gone = sorted(a.keys() - b.keys()); new = sorted(b.keys() - a.keys())
    return dict(common=len(a.keys() & b.keys()), changed=sum(o["members"] for o in out.values()),
                changed_bits=sum(o["bits"] for o in out.values()),
                removed=len(gone), added=len(new), removed_ex=gone[:4], added_ex=new[:4],
                added_landed=collections.Counter(b[k]["landed"] for k in new),
                groups={k: dict(members=o["members"], bits=o["bits"], d_bound=dict(o["d_bound"]), d_landed=dict(o["d_landed"]))
                        for k, o in sorted(out.items())})


k44, k41, k42 = load(sys.argv[1]), load(sys.argv[2]), load(sys.argv[3])
doc = dict(note=__doc__, vs_kv41=diff(k41, k44), vs_kv42=diff(k42, k44))
json.dump(doc, open(sys.argv[4], "w"), indent=1, default=dict)
for t in ("vs_kv41", "vs_kv42"):
    d = doc[t]
    print(t, {k: d[k] for k in ("common", "changed", "changed_bits", "removed", "added")})
    for g, o in d["groups"].items():
        print("  ", g, o)
