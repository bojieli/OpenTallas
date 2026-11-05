#!/usr/bin/env python3
"""FUSED tnode pad straps from plan stations (ot_hnx_fused_tree.sv header: pad the earlier child by the difference of the two round trips; pad_b 1 pads child b).
usage: pad_straps.py PLAN OUT.json. Round trip of a child = down stations + up stations + child's own aligned round trip; lanes and same-level node logic cancel."""
import json, sys
P = json.load(open(sys.argv[1])); T = P["partition_types"]; parts = {p["name"]: p for p in P["partitions"]}
out = {}; maxk = 0; miss = []
for side, part in (("nw", "NW_hub"), ("ne", "NE_hub")):
    ist = T[parts[part]["type"]]["internal_stations"]
    st = {}
    for s in ist:
        st.setdefault((s["launch"].split(".")[0], s["capture"].split(".")[0]), []).append(len(s.get("regs_um", [])))
    def n(a, b):
        v = st.get((a, b))
        if v is None: return 0, False
        return max(v), True
    def link(parent, child):
        d, f1 = n(parent, child); u, f2 = n(child, parent)
        if not f2 and child.endswith("__c"): u, f2 = n(child[:-3], parent)      # lane up bus launches from the lane wrapper name
        if not f1 and not f2: miss.append((side, parent, child))
        return d + u
    kids = {}
    for h in (0, 1):
        n3, l, r = f"u_mu_fused_n3_q{h}", f"u_mu_fused_n2L_q{h}", f"u_mu_fused_n2R_q{h}"
        kids[n3] = (l, r); kids[l] = (f"u_mu_fused_n1_q{h}_0", f"u_mu_fused_n1_q{h}_1"); kids[r] = (f"u_mu_fused_n1_q{h}_2", f"u_mu_fused_n1_q{h}_3")
        for g in range(4):
            kids[f"u_mu_fused_n1_q{h}_{g}"] = (f"u_mu_fused_{8*h+2*g}__c", f"u_mu_fused_{8*h+2*g+1}__c")
    kids["u_mu_fused_n4"] = ("u_mu_fused_n3_q0", "u_mu_fused_n3_q1")
    def R(x):
        if x not in kids: return 0
        a, b = kids[x]; ta, tb = link(x, a) + R(a), link(x, b) + R(b)
        d = ta - tb
        out[f"{x}_{side}"] = dict(pad_k=abs(d), pad_b=int(d > 0), ta=ta, tb=tb)
        return max(ta, tb)
    R("u_mu_fused_n4")
print("nodes", len(out), "max pad", max(v["pad_k"] for v in out.values()), "no-station links", len(miss), miss[:6])
for k, v in sorted(out.items())[:8]: print(k, v)
json.dump(dict(pads=out, no_station_links=miss), open(sys.argv[2], "w"), indent=1)
