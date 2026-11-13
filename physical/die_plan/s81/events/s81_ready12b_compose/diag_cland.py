#!/usr/bin/env python3
"""diag_cland.py PLAN SIDECAR: mirror clock_landing_verify._check_all line 299 statically -- for every landing table
port row, does collector.types[dst type].local_sources hold an entry named the port's dst bus?  (No instance needed:
the StopIteration only depends on table + plan.)"""
import collections
import json
import sys

P = json.load(open(sys.argv[1]))
T = json.load(open(sys.argv[2]))
ports = {p["id"]: p for p in P["ports"]}
parts = {p["name"]: p for p in P["partitions"]}
types = T["collector"]["types"]
miss = []
for r in T["ports"]:
    pr = ports.get(r["port"])
    if pr is None:
        miss.append(dict(port=r["port"], why="port not in plan"))
        continue
    bus, dst = pr["dst"]["bus"], r["dst"]
    dtype = parts[dst]["type"] if dst in parts else None
    info = types.get(dtype)
    if info is None:
        miss.append(dict(port=r["port"], dst=dst, type=dtype, bus=bus, why="dst type not in collector.types"))
        continue
    names = [x["name"] for x in info.get("local_sources", [])]
    if bus not in names:
        miss.append(dict(port=r["port"], dst=dst, type=dtype, bus=bus, plan_dst=pr["dst"],
                         local_sources=names, why="bus not in local_sources"))
print("rows", len(T["ports"]), "unmatched", len(miss))
print(collections.Counter(m["why"] for m in miss))
for m in miss[:12]:
    print(json.dumps(m)[:600])
