#!/usr/bin/env python3
"""DIE-HBM-30 item 1: HBM-055 residual -> move the 8 scorer row regs still mapped to b103
($procdff 71685/71686/71687/71692/71712/71740/71745/71750, NE/NW halves) to b101 next to the score register.
usage: scorer_regs.py SRC_MAP OUT_MAP"""
import json, re, sys
M = json.load(open(sys.argv[1])); pm = M["parts"]
ids = {71685, 71686, 71687, 71692, 71712, 71740, 71745, 71750}
mv = []
for h in ("NW", "NE"):
    pre = f"hb_idx__s_{h}.scorer."
    for k in pm:
        m = re.search(r"\$(\d+)$", k)
        if k.startswith(pre) and m and int(m.group(1)) in ids and pm[k] == f"{h}_b103":
            mv.append((k, pm[k], f"{h}_b101")); pm[k] = f"{h}_b101"
assert len(mv) == 16, len(mv)
M["note"] = "DIE-HBM-30 scorer residual regs b103->b101 | " + M["note"]
json.dump(M, open(sys.argv[2], "w"))
print(len(mv)); [print(" ", a, b, "->", c) for a, b, c in mv]
