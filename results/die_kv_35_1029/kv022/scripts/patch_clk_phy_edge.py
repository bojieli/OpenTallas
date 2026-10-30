import json, sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
p = json.load(open(src))
ent = {"port": "clk_clk_phy", "tap_um": [1898.656, 354.0], "period_mult": 1,
       "source": "hub_C pll.pll_phy (asbuilt sources: pll_phy -> domain clk_phy; bound-top spine clk_clk_phy)",
       "note": "KV-022 COORD 10-29 14:37 (DIE-KV-35): x6 PHY clock -> serdes .clk_phy (u_fdi_cdc phy side 5259 FF + macro clk pin (1866.24,354.0)); E-rim interior M7 pin at the macro clk pin row; kit clock at the die period (PLL model 1043 ps: 833 is tighter, not relaxed), synchronous with clk per schema (QC clk_serdes form)"}
delta = []
for tn in ("kv3_sys_SD", "kv3_sys_SD_v1"):
    ec = p["partition_types"][tn]["clock"]["edge_clocks"]
    assert all(e["port"] != ent["port"] for e in ec)
    ec.append(ent)
    delta.append({"op": "add", "path": f"/partition_types/{tn}/clock/edge_clocks/-", "value": ent})
json.dump(p, open(dst, "w"), indent=1)
json.dump(dict(src=src, src_sha256=hashlib.sha256(open(src,"rb").read()).hexdigest(), dst=dst,
               dst_sha256=hashlib.sha256(open(dst,"rb").read()).hexdigest(), patch=delta), open(dst.replace(".json","_delta.json"), "w"), indent=1)
print("ok", len(delta))
