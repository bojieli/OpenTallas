#!/usr/bin/env python3
"""DIE-HBM-19: carry the bind-time plan declarations of HBM-BIND-2/3 plan0 (per-type dead_inputs = u_qlate rst_n proof,
top-level asbuilt pointer) onto a plan of record (d16k). Nothing else changes. usage: mk_bindplan.py SRC_PLAN_DIR PLAN0 OUT_DIR [--no-asbuilt]  (--no-asbuilt: plan-of-record form, G0 schema has no
`asbuilt` key; bind then takes the manifest from --asbuilt)"""
import json, os, sys, shutil, hashlib
src, plan0, out = sys.argv[1:4]
a = json.load(open(plan0)); b = json.load(open(os.path.join(src, "die_plan.json")))
n = 0
for t, v in a["partition_types"].items():
    if v.get("dead_inputs"):
        bt = b["partition_types"][t]
        assert bt.get("dead_inputs") in (None, v["dead_inputs"]), t
        bt["dead_inputs"] = v["dead_inputs"]; n += 1
if "--no-asbuilt" not in sys.argv:
    b["asbuilt"] = a["asbuilt"]
b["note"] = b.get("note", "") + " | DIE-HBM-19 bind view: + plan0 per-type dead_inputs (%d types, HBM-BIND-2 u_qlate) + asbuilt pointer" % n if "--no-asbuilt" not in sys.argv else " | DIE-HBM-19: + plan0 per-type dead_inputs (%d types, HBM-BIND-2 u_qlate, HBM-027)" % n
if os.path.exists(out): shutil.rmtree(out)
os.makedirs(out)
for f in os.listdir(src):
    if f != "die_plan.json":
        s = os.path.join(src, f)
        (shutil.copytree(s, os.path.join(out, f), copy_function=os.link) if os.path.isdir(s) else os.link(s, os.path.join(out, f)))
t = json.dumps(b, indent=1); open(os.path.join(out, "die_plan.json"), "w").write(t)
print("types", n, "sha", hashlib.sha256(t.encode()).hexdigest()[:12])
