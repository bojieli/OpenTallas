#!/usr/bin/env python3
"""HBM-BIND-12 g2 manifest = HBM-BIND-11 g1 manifest + compose -> g2/compose.json (mk_compose_lid9.py). Nothing else."""
import json, sys
src, dst, comp = sys.argv[1:4]
m = json.load(open(src))
assert m["compose"] == "/srv/opentallas-scratch2/claude/hbm-bind-7-1029/c1/compose.json", m["compose"]
m["compose"] = comp
m["note"] = ("HBM-BIND-12 g2: g1 + compose copy with the 44 SU 4-lane cuts (lanes_plain*, Q2/Q3 lanes* except lanes8_11) "
             "exposing lane_lane_id[8:0] = lane_id[10:2] of the 4 lanes (plan canon kit pin), lane_id[1:0] kept as the "
             "as-built literals inside (mk_compose_lid9.py) | " + m["note"])
json.dump(m, open(dst, "w"), indent=1)
