#!/usr/bin/env python3
"""DIE-HEAD-47 l47 = l46a plan of record (sha256 bd1dd9ff3e30) + VALUE-ONLY edit: clock.insertion_ff_ps 380 placeholder ->
0.76 x clock.insertion_ps (= 342.0) and its insertion_basis, on every HEAD type that still carries 380, except hd_lep0N
(signed ECO7, LEC running) and hd_serdes (Codex ECO1B in flight).  No pin / RTL / geometry / clock-tree change.
usage: make_l47.py L46A_SOURCE_PLAN OUT_SOURCE_PLAN"""
import json, sys, hashlib
src, dst = sys.argv[1:3]
raw = open(src).read(); p = json.loads(raw)
SKIP = {"hd_lep0N", "hd_serdes"}
BASIS = ("DIE-HEAD-47 l47: FF = 0.76 x TT plan (measured FF/TT 0.757-0.765: hd_spn_wshim_rx 321.29/419.73, hd_mesh_e "
         "342.67/452.60, hd_st_m 336.79/444.87 GRT pin-register means); replaces the parent_budget 380 placeholder")
ch = []
for tn, t in p["partition_types"].items():
    c = t.get("clock", {})
    if tn in SKIP or c.get("insertion_ff_ps") not in (380, 380.0): continue
    c["insertion_ff_ps"] = round(0.76 * float(c["insertion_ps"]), 1); c["insertion_basis"] = BASIS; ch.append(tn)
out = json.dumps(p, indent=1) + ("\n" if raw.endswith("\n") else "")
open(dst, "w").write(out)
print(len(ch), ch, hashlib.sha256(out.encode()).hexdigest())
