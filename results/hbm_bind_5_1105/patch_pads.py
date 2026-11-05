#!/usr/bin/env python3
"""Replace top inputs native_required__<node>__pad_[kb] of the spliced netlist with the plan strap constants (pad_straps.py).  usage: patch_pads.py IN.json OUT.json PADS.json RECEIPT"""
import json, re, sys
J = json.load(open(sys.argv[1])); pads = json.load(open(sys.argv[3]))["pads"]
tops = [n for n, m in J["modules"].items() if m.get("attributes", {}).get("top")] or ["hbm_current_native_top"]
M = J["modules"]["hbm_current_native_top"] if "hbm_current_native_top" in J["modules"] else J["modules"][tops[0]]
sub = {}; done = []
for name, p in list(M["ports"].items()):
    m = re.match(r"native_required__(.+)__pad_([kb])$", name)
    if not m: continue
    v = pads[m.group(1)]["pad_" + m.group(2)]
    for i, b in enumerate(p["bits"]): sub[b] = str((v >> i) & 1)
    del M["ports"][name]; M["netnames"].pop(name, None); done.append(name)
n = 0
for c in M["cells"].values():
    for pn, bits in c["connections"].items():
        for i, b in enumerate(bits):
            if b in sub: bits[i] = sub[b]; n += 1
json.dump(J, open(sys.argv[2], "w"))
json.dump(dict(ports=len(done), bits=len(sub), sinks=n, unmatched_nodes=sorted(set(pads) - {re.sub(r"__pad_.$", "", d.replace("native_required__", "")) for d in done})), open(sys.argv[4], "w"), indent=1)
print("pads ports", len(done), "bits", len(sub), "sinks", n)
