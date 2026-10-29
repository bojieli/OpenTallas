import json, sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
p = json.load(open(src))
pad = {"name": "clk_clk_phy", "dir": "in", "width": 1, "clock": True,
       "note": "KV-022 COORD 10-29 14:37 (DIE-KV-35): PHY reference clock from hub_C PLL pll_phy (asbuilt sources: pll_phy -> domain clk_phy, bound-top spine clk_clk_phy) into serdes macro .clk_phy; HEAD-BIND-4 type-pad form (as hd_serdes pma_rck), no boundary flop, PHY-side timing"}
delta = []
for tn in ("kv3_sys_SD", "kv3_sys_SD_v1"):
    t = p["partition_types"][tn]
    assert "pads" not in t, tn
    t["pads"] = [pad]
    delta.append({"op": "add", "path": f"/partition_types/{tn}/pads", "value": [pad]})
json.dump(p, open(dst, "w"), indent=1)
json.dump(dict(src=src, src_sha256=hashlib.sha256(open(src,"rb").read()).hexdigest(), dst=dst,
               dst_sha256=hashlib.sha256(open(dst,"rb").read()).hexdigest(), patch=delta), open(dst.replace(".json","_delta.json"), "w"), indent=1)
print("ok", len(delta))
