#!/usr/bin/env python3
"""DIE-HBM-25 g4 manifest = HBM-BIND-13 g3 manifest + compose -> g4/compose.json (mk_compose_pretree_rst.py). Nothing else."""
import json, sys
src, dst, comp = sys.argv[1:4]
m = json.load(open(src))
assert m["compose"] == "/srv/opentallas-scratch2/claude/hbm-bind-13-1029/g3/compose.json", m["compose"]
m["compose"] = comp
m["note"] = ("DIE-HBM-25 g4: g3 + compose copy with the 8 SU pretree cuts' pretree_rst_n renamed rst_n "
             "(one terminal u_pt.rst_n each; HBM-046 (A), mk_compose_pretree_rst.py) | " + m["note"])
json.dump(m, open(dst, "w"), indent=1)
