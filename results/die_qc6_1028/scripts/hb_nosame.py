#!/usr/bin/env python3
"""DIE-QC-6 INFO: main hold_buffer_model (unchanged) on the intra HB record with the c_* SAME-CORE pairs removed (two die
taps of one A0 core = in-core paths that the adopted A0 centre entry (COORD 03:35) moves into the core's own CTS/hold).
usage: TOOLS PKL PLAN"""
import sys, json, pickle
sys.path.insert(0, sys.argv[1])
import die_sta_related as R
S = pickle.load(open(sys.argv[2], "rb"))
p = json.load(open(sys.argv[3]))
PT = p["partition_types"]
PT = PT if isinstance(PT, dict) else {x["name"]: x for x in PT}
ty = {x["name"]: x["type"] for x in p["partitions"]}


def core_of(port):
    part, _, t = port[2:].partition("__clk")
    t = t.lstrip("_") or "t0"
    if not part.startswith("c_") or not t.startswith("t"):
        return None
    r = PT[ty[part]]["clock"]["taps"][int(t[1:])]
    return (part, r["name"].split(".")[0]) if r["kind"] == "core" else None


call = S["calls"][0]
def same(k):
    a, b = core_of(k[0]), core_of(k[1])
    return a is not None and a == b
for name, drop in (("all", False), ("no_same_core", True)):
    tt = {k: v for k, v in call["tt"].items() if not (drop and same(k))}
    ff = {k: v for k, v in call["ff"].items() if not (drop and same(k))}
    r = R.hold_buffer_model(tt, ff, bits=call["bits"], hb=call["hb"], part_bits=call["part_bits"])
    print(name, "records", len(ff), json.dumps({k: v for k, v in r.items() if not isinstance(v, (list, dict))})[:600])
