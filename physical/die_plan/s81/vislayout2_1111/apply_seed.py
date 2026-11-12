#!/usr/bin/env python3
"""apply_seed.py PLAN SEED.json OUT : write seed origins/orients into the plan verbatim (scoring only, no legalise)."""
import json, sys
P = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
for tn, d in S.items():
    for h in P["partition_types"][tn]["hard_cores"]:
        if h["inst"] in d:
            h["origin_um"] = d[h["inst"]]["origin_um"]; h["orient"] = d[h["inst"]]["orient"]
json.dump(P, open(sys.argv[3], "w"), indent=1)
