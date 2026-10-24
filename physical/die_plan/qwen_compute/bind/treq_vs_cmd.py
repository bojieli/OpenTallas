#!/usr/bin/env python3
"""BINDER3: per-hop landed depth of the treq lanes vs their cmd twins (QC-P5-TIE, COORD 18:4x) from a bind's
bus_groups.json.  hop = (source leaf -> sink leaf); offset = landed(treq) - landed(cmd) on that hop (compiler term:
treq arrives that many edges later (negative = earlier) than cmd at each slice's u_fdn; the leaf-internal fdn->fup
treq vs cmd stage difference is a leaf property, recorded by QC-P5-TIE).
    treq_vs_cmd.py BIND_DIR OUT.json"""
import json
import sys
bg = json.load(open(f"{sys.argv[1]}/bus_groups.json"))
hops = {}
for g in bg["landing"]:
    for m in g["members"]:
        if m["sink_port"] in ("treq_i", "cmd_i"):
            src = m["source"].rpartition(".")[0]
            k = (src, g["sink"])
            hops.setdefault(k, {}).setdefault(m["sink_port"], set()).add((m["bound_stages"], m["landed_stages"], m["lane"]))
rows = []
for (s, d), v in sorted(hops.items()):
    if "treq_i" not in v:
        continue
    t, c = sorted(v["treq_i"]), sorted(v.get("cmd_i", []))
    rows.append(dict(src=s, sink=d, treq=[dict(bound=a, landed=b, lane=l) for a, b, l in t],
                     cmd=[dict(bound=a, landed=b, lane=l) for a, b, l in c],
                     offset=(max(x[1] for x in t) - max(x[1] for x in c)) if c else None))
json.dump(dict(schema="opentallas.binder.treq_vs_cmd.v1", bind=sys.argv[1], hops=rows), open(sys.argv[2], "w"), indent=1)
for r in rows:
    print(r["src"], "->", r["sink"], "treq", [x["landed"] for x in r["treq"]], "cmd", [x["landed"] for x in r["cmd"]], "offset", r["offset"])
