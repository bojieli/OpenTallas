#!/usr/bin/env python3
"""QC-S28-BIND: list every file a plan names (sink_bins_file repo-relative; pins_file/census/etc plan-folder first) and whether it
resolves in TREE.  usage: refs.py PLAN TREE [PLANDIR_IN_TREE]"""
import json, sys, os, collections
P = json.load(open(sys.argv[1])); T = sys.argv[2]
PD = sys.argv[3] if len(sys.argv) > 3 else "physical/die_plan/qwen_compute/plan_of_record"
refs = collections.defaultdict(set)
def walk(o, k=""):
    if isinstance(o, dict):
        for kk, v in o.items(): walk(v, kk)
    elif isinstance(o, list):
        for v in o: walk(v, k)
    elif isinstance(o, str) and k in ("sink_bins_file", "pins_file", "rows", "map", "bitcon", "proof", "file", "path", "bins_file", "street_rule_bins_file"):
        refs[k].add(o)
walk(P)
miss = 0
for k, s in sorted(refs.items()):
    for r in sorted(s):
        c = [os.path.join(T, PD, r), os.path.join(T, r)]
        ok = [x for x in c if os.path.exists(x)]
        if not ok:
            miss += 1; print("MISSING", k, r)
    print("key", k, len(s), "refs")
print("missing", miss)
