#!/usr/bin/env python3
"""HBM-BIND-13 g3 manifest = HBM-BIND-12 g2 manifest + compose -> g3/compose.json (mk_compose_rst.py). Nothing else."""
import json, sys
src, dst, comp = sys.argv[1:4]
m = json.load(open(src))
assert m["compose"] == "/srv/opentallas-scratch2/claude/hbm-bind-12-1029/g2/compose.json", m["compose"]
m["compose"] = comp
m["note"] = ("HBM-BIND-13 g3: g2 + compose copy with the SU cuts merged bank_rst_n split into rst_n (banks), "
             "rst_lane_n[k] (lanes) and rst_bcast_n (ctl replica flops) per source/kit (mk_compose_rst.py) | " + m["note"])
json.dump(m, open(dst, "w"), indent=1)
