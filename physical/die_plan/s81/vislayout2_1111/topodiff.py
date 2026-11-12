#!/usr/bin/env python3
"""topodiff.py SRC PLAN TYPE BIND ASBUILT: which native_contract parts of PLAN differ from BIND/native_topology.json"""
import json, sys, os
from pathlib import Path
src, plan, tn, bind, asb = sys.argv[1:6]
sys.path.insert(0, src + "/tools/die_plan"); os.chdir(src)
import kit_topology as K
raw = json.loads(Path(plan).read_text())
new = K.native_contract(raw, asb, plan)
old = json.loads((Path(bind) / "native_topology.json").read_text())
print("asbuilt_sha", old.get("asbuilt_sha256", "")[:12])
for k in ("transport", "reset", "clock_table_sha256", "ownership"):
    print(k, "SAME" if old.get(k) == new.get(k) else "DIFF")
a, b = old.get("types", {}).get(tn), new["types"][tn]
print("type", "SAME" if a == b else "DIFF")
def walk(x, y, p):
    if type(x) != type(y): print(" ", p, str(x)[:100], "->", str(y)[:100]); return
    if isinstance(x, dict):
        for k in sorted(set(x) | set(y)): walk(x.get(k), y.get(k), p + "/" + str(k))
    elif isinstance(x, list):
        if len(x) != len(y): print(" ", p, "len", len(x), len(y))
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, "%s[%d]" % (p, i))
    elif x != y: print(" ", p, str(x)[:100], "->", str(y)[:100])
walk(a, b, "type")
if old.get("reset") != new.get("reset"): walk(old.get("reset"), new.get("reset"), "reset")
