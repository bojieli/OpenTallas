#!/usr/bin/env python3
"""contents entry u_fvp_Qk beside u_vmb_Qk_mu1 in both hub types. usage: plan_fvp.py IN OUT"""
import json, sys
P = json.load(open(sys.argv[1]))
ps = {p["name"]: p for p in P["partitions"]}
for h in ("NW_hub", "NE_hub"):
    t = P["partition_types"][ps[h]["type"]]; hc = {x["inst"]: x for x in t["hard_cores"]}
    for k in range(8):
        o = hc[f"u_vmb_Q{k}_mu1"]; x, y = o["origin_um"]; w, hh = o["outline_um"]
        t["contents"].append(dict(inst=f"u_fvp_Q{k}", module="ot_hnx_fused_vm_pair", status="new", cells=320, note="HBM-BIND-5 C2 option (a) candidate: lanes 2k,2k+1 on S bank group 0", origin_um=[x, round(y + hh, 2)], outline_um=[8.64, 8.64]))
json.dump(P, open(sys.argv[2], "w"), indent=1)
