#!/usr/bin/env python3
"""TOK-DS-2: Verilator filelist for the whole-die bound top: bind.f (full files) + asbuilt source pool as -v libraries."""
import json, sys, os
asb, bindf, wt, out = sys.argv[1:5]
a = json.load(open(asb))
full = [l.strip() for l in open(bindf) if l.strip()]
have = set(full)
libs = []
for f in a.get("prefer", []) + a["files"]:
    p = os.path.join(wt, f)
    if p.endswith("_bb.v"):
        q = p[:-5] + ".v"
        if os.path.exists(q): p = q
    if p.endswith(".svh") or p.endswith(".vh"): continue
    if p in have or p in libs: continue
    if not os.path.exists(p): print("MISSING", p, file=sys.stderr); continue
    libs.append(p)
dirs = sorted({os.path.dirname(f) for f in full + libs})
with open(out, "w") as fh:
    for d in dirs: fh.write("+incdir+" + d + "\n")
    for f in full: fh.write(f + "\n")
    for f in libs: fh.write("-v " + f + "\n")
print(len(full), "full", len(libs), "lib")
