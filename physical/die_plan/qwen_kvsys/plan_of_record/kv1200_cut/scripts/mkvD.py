#!/usr/bin/env python3
"""DIE-KV-98: final cut plan vD from vA (5091ada3): kv3_sys_c = kvr2 + ONLY contents[u_bound.u_dcal.u_profile] origin from kvfix1
(ROM -0.864 um, cures DRT-0255 clknet_1_0__leaf_clk_t27; the PHY-macro shifts of kvfix1 break the strict bind reset relay), kv3_hg = kvr2 geometry
(VIS-TRIAGE-KVHEAD hg delta dropped: OT_CLAND band ft1_i no legal site). usage: mkvD.py VA KVR2 KVFIX1 OUT"""
import json, sys
a, b, k, out = sys.argv[1:5]
p = json.load(open(a)); r = json.load(open(b)); f = json.load(open(k))
pt = p["partition_types"]
pt["kv3_hg"] = r["partition_types"]["kv3_hg"]
c = r["partition_types"]["kv3_sys_c"]; pt["kv3_sys_c"] = c
i = [h["inst"] if "inst" in h else h.get("name") for h in c["contents"]].index("u_bound.u_dcal.u_profile")
c["contents"][i]["origin_um"] = f["partition_types"]["kv3_sys_c"]["contents"][i]["origin_um"]
json.dump(p, open(out, "w"), indent=1); open(out, "a").write("\n")
