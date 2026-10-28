#!/usr/bin/env python3
"""DIE-QC-6 INFO: classify c_* intra pairs by what the plan tap feeds (plan clock.taps order = tap index tN):
same A0 core (two die taps of ONE core = an in-core path timed at die level), core-core, core-glue, glue-glue.
FF hold per pair from main's HB record pickle (gate model, budget register).  usage: PKL PLAN"""
import sys, json, pickle, collections
S = pickle.load(open(sys.argv[1], "rb"))
p = json.load(open(sys.argv[2]))
PT = p["partition_types"]
PT = PT if isinstance(PT, dict) else {x["name"]: x for x in PT}
ty = {x["name"]: x["type"] for x in p["partitions"]}


def feed(port):
    part, _, t = port[2:].partition("__clk")
    t = t.lstrip("_") or "t0"
    if not t.startswith("t"):
        return part, ("other", t)
    tl = PT[ty[part]]["clock"]["taps"]
    r = tl[int(t[1:])]
    return part, (r["kind"], r["name"].split(".")[0] if r["kind"] == "core" else r["name"])


agg = collections.defaultdict(list)
for key, v in S["calls"][0]["ff"].items():
    a, b, tag = key[:3]
    if not tag.startswith("c_"):
        continue
    (_, fa), (_, fb) = feed(a), feed(b)
    if fa[0] == "core" and fb[0] == "core":
        k = "same-core" if fa[1] == fb[1] else "core-core"
    elif "core" in (fa[0], fb[0]):
        k = "core-glue"
    else:
        k = "glue-glue"
    agg[k].append(v[1])
tot = sum(len(L) for L in agg.values())
for k, L in sorted(agg.items()):
    L.sort()
    print(f"{k:10s} pairs {len(L):6d} ({100*len(L)/tot:4.1f}%) worst {L[0]:7.1f} median {L[len(L)//2]:6.1f} neg {sum(1 for x in L if x < 0)} "
          f"<-100 {sum(1 for x in L if x < -100)}")
