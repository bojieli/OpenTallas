#!/usr/bin/env python3
"""S81 plan size (DIE-S81-54/EG 11-04; 49.96 MB against the 50 MB merge-lane line): write each collector_tree.relays row of
every partition type on one line.  Whitespace only; parsed plan equal is asserted.  python3 compact_relays.py <in> <out>"""
import json, re, sys
src, out = sys.argv[1:]
txt = open(src).read(); plan = json.loads(txt)
dec = json.JSONDecoder(); res = []; last = 0; n = 0
for m in re.finditer(r'(?m)^( +)"relays": \[', txt):
    i = m.end() - 1
    v, e = dec.raw_decode(txt, i)
    pad = m.group(1) + " "
    body = "[]" if not v else "[\n" + ",\n".join(pad + json.dumps(r, separators=(",", ":")) for r in v) + "\n" + m.group(1) + "]"
    res += [txt[last:i], body]; last = e; n += 1
res.append(txt[last:]); new = "".join(res)
assert json.loads(new) == plan, "whitespace edit changed the plan"
open(out, "w").write(new); print("compact_relays OK", n, len(txt), "->", len(new))
