#!/usr/bin/env python3
"""PG-ACTIVITY-KVHBM 10-27: KV per-type W/mm2 on measured RTL activity from the KV-INFRA-R2 vectorless power model.
Measured cores: ratio r = measured / vectorless report_power on the SAME routed view (6_final odb+spef, TT RVT NLDM).
  head eighths (e0/e1/e2/e5/e6, all lane8+stin+stk): r_head (e1 measured); hg/hgi glue: r_head (UNCHECKED-ESTIMATE);
  kv3_pv_pair: r_pv; all other types (hub/pc/sys/hroot/astk/qkd_kvs_ctl, all <0.43 W/mm2): mean(r_head, r_pv) (UNCHECKED-ESTIMATE);
  die clock mesh (uniform W/mm2 already in the old types map) unchanged.
  kv_types_meas.py KV_POWER.json OLD_TYPES.json R_HEAD R_PV OUT_TYPES.json"""
import json, sys
P = json.load(open(sys.argv[1])); old = json.load(open(sys.argv[2]))["types"]; rh, rp = float(sys.argv[3]), float(sys.argv[4]); rm = (rh + rp) / 2
def r_core(c): return rh if c.startswith("kv3_head_eighth") else rp if c == "kv3_pv_pair" else rm
new, det = {}, {}
for t, d in P["types_detail"].items():
    if t not in old: continue
    mesh = old[t] - d["w_mm2"]
    hard = {c: n * P["hard_cores"][c]["W"] for c, n in d.get("measured", {}).items()}
    hW = sum(hard.values()); estW = d["W"] - hW - d["glue_W"]       # estimated cores (e6) = remainder
    heads = any(c.startswith("kv3_head_eighth") for c in hard)
    rg = rh if heads else (rp if "kv3_pv_pair" in hard else rm)
    W = sum(r_core(c) * w for c, w in hard.items()) + (rh if heads else rm) * estW + rg * d["glue_W"]
    new[t] = round(W / d["area_mm2"] + mesh, 4)
    det[t] = dict(old_w_mm2=old[t], new_w_mm2=new[t], old_W=d["W"], new_W=round(W, 4), hard_W=round(hW, 4), est_W=round(estW, 4),
                  glue_W=d["glue_W"], glue_ratio=rg, mesh_w_mm2=round(mesh, 4))
for t in old:
    if t not in new: new[t] = round(old[t] * rm, 4); det[t] = dict(old_w_mm2=old[t], new_w_mm2=new[t], note="no detail, scaled by mean ratio")
json.dump({"types": new}, open(sys.argv[5], "w"))
json.dump(det, open(sys.argv[5].replace(".json", "_detail.json"), "w"), indent=1)
print("ratios head %.4f pv %.4f other %.4f" % (rh, rp, rm))
for t in ("kv3_hg", "kv3_hgi", "kv3_pv", "kv3_pv_v7", "kv3_sys_SD", "kv3_pc", "kv3_hub_C", "kv3_hub_Eo"): print(t, old[t], "->", new[t])
