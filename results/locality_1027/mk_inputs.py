#!/usr/bin/env python3
"""LOCALITY-SCORE-1: QC baseline region map = QC-SLICECLK-1 domains (12 slices c_S_* + sl_S_*, HUB = the west IO
strip / collective, io_serdes_2 merged into W5 by the hard-PHY rule)."""
import json, re, sys
p = json.load(open(sys.argv[1]))
out = {}
for q in p["partitions"]:
    n = q["name"]
    m = re.match(r"^(?:c|sl)_([WE]\d)_", n)
    out[n] = m.group(1) if m else ("W5" if n == "io_serdes_2" else "HUB")
json.dump(dict(part_region=out, note="QC-SLICECLK-1 slice domains (12 + HUB), rule in mk_inputs.py"),
          open(sys.argv[2], "w"), indent=0, sort_keys=True)
print(len(out), len(set(out.values())))
