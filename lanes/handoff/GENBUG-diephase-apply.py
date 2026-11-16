#!/usr/bin/env python3
"""GENBUG-IMPL r227: die-wide die-phase face-pin keys into dies.<die>.die_gen_env of autopilot/kit_wave.json.
usage: diephase_apply.py DIE [--apply]   (DIE = s81 | s81_head); default is a dry run printing the diff.
Same-commit rule (COORD r227): run --apply in the commit of the fresh gen (G3b adoption for s81, NF13 for s81_head);
the rewrite keeps kit_wave.json byte format (indent=1, ensure_ascii).  die_gen_env changes re-arm failed rows (FLOW-FLOW class 5),
so auto_rearm must be off at that point.  Item-level item_env of the same keys is left as is (it wins and is identical)."""
import json, sys
K = {"OT_PG_DIE_PHASE": "1", "OT_PG_TRACK_TRUTH": "1", "OT_PG_TRACK_TRUTH_WIDE_SPACING": "1",
     "OT_PG_CELL_KEEPOUT": "0", "OT_PG_PIN_CHECK": "warn"}
die = sys.argv[1]; path = "autopilot/kit_wave.json"
s = open(path).read(); d = json.loads(s)
assert json.dumps(d, indent=1, ensure_ascii=True) == s, "kit_wave.json format changed; refusing"
g = d["dies"][die].setdefault("die_gen_env", {})
new = {k: v for k, v in K.items() if g.get(k) != v}
print(f"{die}: die_gen_env +{len(new)} keys {new}")
if "--apply" in sys.argv:
    d["dies"][die]["die_gen_env_prev_diephase"] = dict(g)
    g.update(K)
    open(path, "w").write(json.dumps(d, indent=1, ensure_ascii=True))
    print("applied")
