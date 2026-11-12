#!/usr/bin/env python3
"""move_taps.py IN_PLAN OUT_PLAN TYPE name=x,y ... : set clock.added_taps xy of TYPE (positions only)."""
import json, sys
P = json.load(open(sys.argv[1])); t = P["partition_types"][sys.argv[3]]
mv = dict((a.split("=")[0], [float(v) for v in a.split("=")[1].split(",")]) for a in sys.argv[4:])
for tp in t["clock"].get("added_taps") or []:
    if tp["name"] in mv:
        print(tp["name"], tp["xy"], "->", mv[tp["name"]]); tp["xy"] = mv.pop(tp["name"])
assert not mv, mv
json.dump(P, open(sys.argv[2], "w"))
