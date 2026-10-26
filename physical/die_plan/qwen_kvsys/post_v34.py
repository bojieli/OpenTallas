#!/usr/bin/env python3
"""KV-P3b 10-23: v3.4 census = v3.2 rows/map + COORD R5 bit-level tap-tree audit inputs.

    python3 post_v34.py DIE_PLAN.json CENSUS_MAP_IN CENSUS_MAP_OUT     (rewrites DIE_PLAN.json in place)

census[0].bitcon = census/bitcon_rtl6.json.gz (as-built rtl6 e33504a6f bit pairs, KV bind/bitcon.py); tree lanes come
from the plan's 'tap_tree <src>.<port>' lane notes; bit_rules split the destinations the plan splits by bit:
the quadrant HBM PHY (phy_<Q> port <x><n> -> slice phy_<Q>_<n//4>) and the x12 host SerDes (tx_flit[521:0] -> sys_SW,
[1042:522] -> sys_SE; every other SerDes port -> both halves)."""
import json
import sys

plan, mi, mo = sys.argv[1:4]
P = json.load(open(plan))
M = json.load(open(mi))
rules = []
for q in ("WS", "WN", "ES", "EN"):
    for k in range(8):
        rules.append(dict(inst=f"phy_{q}", port="(pi|po|fh|rh)(" + "|".join(str(4 * k + i) for i in range(4)) + ")",
                          part=f"phy_{q}_{k}"))
rules += [dict(inst="serdes_host", port="tx_flit", lo=0, hi=521, part="sys_SW"),
          dict(inst="serdes_host", port="tx_flit", lo=522, hi=1042, part="sys_SE"),
          dict(inst="serdes_host", port="(?!tx_flit$).*", part="sys_SW"),
          dict(inst="serdes_host", port="(?!tx_flit$).*", part="sys_SE")]
M["bit_rules"] = rules
json.dump(M, open(mo, "w"), indent=1)
c = P["census"][0]
c["map"] = "census/census_map_v34.json"
c["bitcon"] = "census/bitcon_rtl6.json.gz"
c["note"] += "; v3.4: bitcon + bit_rules = R5 bit-level tap-tree audit (taptree_audit_v32.py pattern)"
json.dump(P, open(plan, "w"), indent=1)
