#!/usr/bin/env python3
"""HBM-XLP10: replace the DS SM.MATVEC shape cycles of the RATE8 census input m_all.json by a measured units file.
   compose.py m_all.json units.json NAME out.json  (shapes absent from units keep m_all's value)"""
import json, sys
m, u, name, out = sys.argv[1:5]
M = json.load(open(m)); U = json.load(open(u))
ms = M["designs"]["ds_ar"]["SM.MATVEC"]["shapes"]; us = U["designs"]["ds_ar"]["SM.MATVEC"]["shapes"]
n = 0
for k, v in us.items():
    if v.get("cycles") is None or k not in ms:
        continue
    print(f"{ms[k].get('cycles')} -> {v['cycles']}  {k[:90]}")
    ms[k] = dict(ms[k], cycles=v["cycles"], job=v.get("job"), notes=(v.get("notes", "") + f"; HBM-XLP10 {name}"))
    n += 1
M["designs"]["ds_ar"]["SM.MATVEC"]["xmode"] = name
M["designs"]["ds_ar"]["SM.MATVEC"]["grade"] = "measured-newest-bench-passing-not-bound (HBM-XLP10 " + name + ")"
json.dump(M, open(out, "w"), indent=1)
print("replaced", n, "of", len(ms))
