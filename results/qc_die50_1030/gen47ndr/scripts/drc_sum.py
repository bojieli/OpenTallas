#!/usr/bin/env python3
"""DIE-QC-50/gen47ndr: count a DRT -output_drc report by violation type and layer. usage: drc_sum.py drc.rpt"""
import collections, json, re, sys
C = collections.Counter(); n = 0; v = None
for ln in open(sys.argv[1]):
    m = re.match(r"\s*violation type:\s*(.+)", ln)
    if m: v = m.group(1).strip(); continue
    m = re.search(r"on Layer (\S+)", ln) or re.match(r"\s*layer\s*:\s*(\S+)", ln)
    if m and v: C[(v, m.group(1))] += 1; n += 1; v = None
print(json.dumps(dict(total=n, by_type_layer={f"{a}|{b}": c for (a, b), c in C.most_common()}), indent=1))
