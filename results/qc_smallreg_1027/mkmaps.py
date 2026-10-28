#!/usr/bin/env python3
"""QC-SMALLREG-1: region maps derived from the DIE-QC-3 grp map (sl groups by shared bits, bbox <= c-part box).
row  = the two c partitions of one c row (x0/x1 halves, 2.47 x 2.61 mm, joined by the 00->10 / 11->01 ring links) merged;
quad = the 2x2 c block (bf/bn/tn/tf, 2.47 x 5.23 mm) merged.  sl + HUB as grp."""
import json, re, sys
D = sys.argv[1]
g = json.load(open(D + "/regions_grp_dieqc3.json"))
out = {"grp": dict(g), "row": {}, "quad": {}}
for p, r in g.items():
    m = re.match(r"c_([WE]\d)_(bf|bn|tn|tf)_(\d)(\d)$", p)
    if m:
        s, q, a, b = m.groups()
        out["row"][p] = f"crow_{s}_{q}_{b}"     # same second digit = same y row (00/10 one row, 01/11 the other)
        out["quad"][p] = f"cquad_{s}_{q}"
    else:
        out["row"][p] = r; out["quad"][p] = r
for k, m in out.items():
    json.dump(dict(part_region=m), open(f"{D}/regions_{k}.json", "w"), indent=0, sort_keys=True)
    print(k, len(set(m.values())))
