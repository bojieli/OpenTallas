#!/usr/bin/env python3
"""DIE-HBM-17: move the sfustore_hw V1 (362.88x388.8, 3x6 SRAM grid, 21.6 um streets) plan clock entry off g_bank[1]
to the core centre (181.44,194.4) in the row3/row4 horizontal street; island [177.12,190.08,185.76,198.72] is clear of
every macro + 4.32 halo (rows y 140.448-181.512 and 203.112-244.176). Usage: entry_fix.py PLAN_DIR (edits in place,
breaking hard links)."""
import json, os, sys
d = sys.argv[1]
ce = json.load(open(d + "/clock_entries.json"))
for t in ("q_hub_nw", "q_hub_ne"):
    e = ce[t]["u_sfus_Q"]
    e["source"] += " | DIE-HBM-17 SFUSTORE V1: entry %s over g_bank[1] -> core centre in row3/row4 street" % e["xy_um"]
    e["xy_um"] = [181.44, 194.4]; e["island_um"] = [177.12, 190.08, 185.76, 198.72]
os.unlink(d + "/clock_entries.json"); json.dump(ce, open(d + "/clock_entries.json", "w"), indent=1)
e = json.load(open(d + "/entries.json"))
e["ot_hbm_su_static_sfustore_hw"] = {"source": "DIE-HBM-17: SFUSTORE V1 core centre in the row3/row4 street", "xy": [181.44, 194.4]}
os.unlink(d + "/entries.json"); json.dump(e, open(d + "/entries.json", "w"), indent=1)
