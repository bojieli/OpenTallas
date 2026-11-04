#!/usr/bin/env python3
"""DIE-QC-70 11-04: coll_ucie fully fixed macro contract. The PHY is 777.6 wide in a 777.6 core and the type has one macro at its plan
site; the placer's MPL-0006 fit check reads 777.65 with halo, and there is nothing for it to place. Opt-in stage on main (f91f720f21,
its test fixture is this type). usage (repo root): delta_ucie_fixed.py PLAN"""
import json
import sys
from pathlib import Path

P = sys.argv[1]
t = Path(P).read_text()
p = json.loads(t)
sp = next(s for s in ((", ", ": "), (",", ":")) if json.dumps(p, separators=s) + "\n" == t)
p["partition_types"]["coll_ucie"]["fully_fixed_macros"] = True
Path(P).write_text(json.dumps(p, separators=sp) + "\n")
