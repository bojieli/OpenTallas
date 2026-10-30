#!/usr/bin/env python3
"""DIE-HBM-29 HBM-055 glue step 2 (from the full per-bit UNPLANNED list of b29b, probe_bind.py): the row-0 E glue that
still sat in b103 (row-0 output regs ov/ok/os/ofl $procdff 71718/71719/71720/71725, 71735, row-0 ready/fault logic
$54936-$54943, row-0 idx adders/or $54947-$54951) and the row-1 idx adders/or ($55003-$55007, so row 1 returns
meta 24 b instead of 4x20 b) and the ev[1]!=ev[0] compare ($54895) -> b101 next to the score register.
usage: hbm055_glue2.py SRC_MAP OUT_MAP"""
import json, re, sys
M = json.load(open(sys.argv[1])); pm = M["parts"]
ids = [71718, 71719, 71720, 71725, 71735] + list(range(54936, 54944)) + list(range(54947, 54952)) + \
      list(range(55003, 55008)) + [54895]
mv = []
for h in ("NW", "NE"):
    pre = f"hb_idx__s_{h}.scorer."
    for k in pm:
        if k.startswith(pre) and "gc[" not in k and "ge[" not in k:
            m = re.search(r"\$(\d+)$", k)
            if m and int(m.group(1)) in ids:
                mv.append((k, pm[k], f"{h}_b101")); pm[k] = f"{h}_b101"
M["note"] = "DIE-HBM-29 HBM-055 glue step 2 | " + M["note"]
json.dump(M, open(sys.argv[2], "w"))
print(len(mv)); [print(" ", a, b, "->", c) for a, b, c in mv[:40]]
