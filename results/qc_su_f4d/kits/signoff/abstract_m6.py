#!/usr/bin/env python3
"""QC-SU-F4D abstract M6 OBS per shape (COORD RULING QC-SU-F4C (2)): ORFS generate_abstract writes
write_abstract_lef -bloat_occupied_layers, i.e. a FULL-LAYER M6 OBS as soon as the tree uses M6, which would block every
die-level M6 route over the core.  This replaces ONLY the M6 OBS of that LEF by the per-shape M6 OBS of a non-bloated
abstract of the same 6_final.odb (written by abstract_m6.tcl); M1-M5 OBS, pins and macro data stay byte-identical.
usage: abstract_m6.py BLOATED.lef PERSHAPE.lef OUT.lef REPORT.json"""
import json, re, sys
bl, ps, out, rep = sys.argv[1:5]
def obs_split(t):
    i = t.index("  OBS"); j = t.index("  END", i)
    return t[:i], t[i:j], t[j:]
def layers(obs):
    blocks, cur = {}, None
    for ln in obs.splitlines()[1:]:
        m = re.match(r"\s+LAYER (\S+) ;", ln)
        if m: cur = m.group(1); blocks.setdefault(cur, []); continue
        if cur: blocks[cur].append(ln)
    return blocks
tb, tp = open(bl).read(), open(ps).read()
h, ob, tail = obs_split(tb); _, op, _ = obs_split(tp)
B, P = layers(ob), layers(op)
B["M6"] = P.get("M6", [])
txt = "  OBS\n" + "".join(f"      LAYER {l} ;\n" + "".join(x + "\n" for x in v) for l, v in B.items() if v)
open(out, "w").write(h + txt + tail)
r = dict(bloated=bl, pershape=ps, out=out, m6_rects_bloated=sum(1 for x in layers(ob).get("M6", []) if "RECT" in x),
         m6_rects_out=sum(1 for x in B["M6"] if "RECT" in x), layers=sorted(B))
json.dump(r, open(rep, "w"), indent=1); print("ABSTRACT_M6", r)
