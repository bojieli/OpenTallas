#!/usr/bin/env python3
"""HBM-COMPOSE: delta from a full out-plan, restricted to named types (partition_types.<T>); reports any other diff.
usage: typedelta.py BASE_DIR OUTPLAN_JSON NAME OUT TYPE[,TYPE]"""
import json, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C
base, outp, name, out, types = sys.argv[1:6]
types = types.split(",")
a = json.load(open(os.path.join(base, "die_plan.json"))); b = json.load(open(outp))
allops = []
C.jdiff({k: a[k] for k in b if k in a}, b, [], allops)
mine = [o for o in allops if o[0][:2] in [["partition_types", t] for t in types]]
other = [o for o in allops if o not in mine]
cls = collections.Counter()
for p, op, v in mine:
    k = next((e for e in reversed(p) if isinstance(e, str)), "?")
    top = p[2] if len(p) > 2 else "?"
    cls[(top, k)] += 1
d = {"name": name, "source": os.path.abspath(outp), "source_sha256": C.sha(outp), "base": os.path.abspath(base),
     "files": {"die_plan.json": {"kind": "json", "ops": mine}}, "bookkeeping_not_applied": [],
     "outplan_other_diffs": len(other), "missing_top_keys_in_outplan": sorted(set(a) - set(b))}
json.dump(d, open(out, "w"), indent=1)
print(name, "ops", len(mine), "other diffs in outplan", len(other), "missing top keys", d["missing_top_keys_in_outplan"])
for (t, k), n in sorted(cls.items()): print("  ", t, k, n)
for o in other[:10]: print("  OTHER", o[0], o[1], str(o[2])[:120])
