#!/usr/bin/env python3
"""DIE-HBM-53: recipes_b2 rows for the q3 coll cores (vm/edge/body) from probe recipes q3/rec_<module>.json."""
import json, sys
from pathlib import Path
HERE, Q = Path(sys.argv[1]), Path(sys.argv[2])
B2 = json.load(open(HERE / "recipes_b2.json"))
t = (HERE / "recipes_b2.json").read_text().rstrip(); assert t.endswith("}")
add = {}
for m in ("ot_hfd_coll_q3_vm_core", "ot_hfd_coll_q3_edge_core", "ot_hfd_coll_q3_body_core"):
    assert m not in B2, m
    add[m] = json.load(open(Q / f"rec_{m}.json"))
    t = t[:-1].rstrip() + ",\n " + json.dumps(m) + ": " + json.dumps(add[m], indent=1).replace("\n", "\n ") + "\n}"
t += "\n"
assert json.loads(t) == dict(B2, **add)
(HERE / "recipes_b2.json").write_text(t); print("added", list(add))
