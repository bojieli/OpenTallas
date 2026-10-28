#!/usr/bin/env python3
"""DIE-QC-2: trunk nets for the R35 16w NDR = every clock edge whose PARENT node is a slice-spine node (top spine,
slice column, and the leg from a column node to its first local node). Writes ndr.tcl (create_ndr + assign_ndr on the
combo net names ck_<net>). usage: ndr_nets.py TREE_JSON CTREE_V OUT_TCL"""
import json, re, sys
t = json.load(open(sys.argv[1])); N = t["nodes"]
spine = {int(k) for k, n in N.items() if n.get("spine")} | {0}
v = open(sys.argv[2]).read()
nets = set()
for m in re.finditer(r"BUFx\w+\s+(\w+)\s*\(\.A\((\w+)\),\s*\.Y\((\w+)\)\);", v):
    inst, a, y = m.groups()
    mb = re.fullmatch(r"b(\d+)", inst); mr = re.fullmatch(r"r(\d+)_(\d+)", inst)
    if mb and int(mb.group(1)) in spine:
        nets.add(y)                      # node output net: drives its kids legs (first segment)
    elif mr:
        nid = int(mr.group(1)); par = N[str(nid)]["parent"]
        if par is not None and par in spine:
            nets.add(y)                  # repeater chain on an edge hanging from a spine node
L = ["create_ndr -name ot16w -width {M8 0.64 M9 0.64} -spacing {M8 0.5 M9 0.5}"]
L += [f"assign_ndr -ndr ot16w -net ck_{n}" for n in sorted(nets)]
open(sys.argv[3], "w").write("\n".join(L) + "\n")
print("spine nodes", len(spine), "ndr nets", len(nets))
