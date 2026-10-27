# KV-KVSCTL-3: repo-relative core json for the landed qkd_kvs_ctl cut (no absolute worktree/scratch paths)
import json,sys,os,re
old=json.load(open("results/kv_cores_r2/kvsctl2/rtl/qkd_kvs_ctl_core.json"))
C="results/kv_cores_r2/kvsctl3/rtl/"
def rel(f):
    b=os.path.basename(f)
    if "/kvsctl-r2/rtl_ctl3/" in f: return C+b
    if f.endswith("/b32/rtl/bind_cells.sv"): return C+"bind_cells.sv"
    m=re.search(r"/wt/kvsctl-src/(.*)$",f)
    if m: return m.group(1)
    raise SystemExit("unmapped "+f)
j=dict(old)
j["files"]=[rel(f) for f in old["files"]]
for f in j["files"]: assert os.path.exists(f),f
j["bound"]="results/kv_cores_r2/kvsctl3/kit_rtl/kv3_hub_C/kv3_hub_C_part_bound.sv"
rep=dict(old["report"]); rep["pins_file"]="results/kv_core_slice_1/pd_slice_delta/cores/kvs_ctl_pins.json"
lr=[]
for e in rep.get("leaf_renamed",[]):
    e=dict(e); e["src"]=rel(e["src"])+"@41ac57c25f"; e["copy"]=C+os.path.basename(e["copy"])+" (KV-KVSCTL-3 landed edit of the copy)"; lr.append(e)
rep["leaf_renamed"]=lr
j["report"]=rep
j["landing"]={"rule":"COORD 2026-10-27 02:35 RULING KV kvs_ctl bb6d423642 (a)+(c)","plan":"results/kv_cores_r2/kvsctl2/landing_plan.json",
 "retime_0cyc":{"layer_o/layer_oe (o_hroot x4 + lp)":54,"auth pd_q/pe_q + bd_q/be_q":80,"i_hroot fault cf2 IN_LAND":32,"total":166},
 "plus1":{"dcfg age_vport/age_pv/age_attn/fused_program_capability":305,"boot__setup_ready":1},
 "sender_owner":{"embgw__bw[0]":"left through logic (use_b precompute); owner of the embgw sender lands it one edge earlier"},
 "reset_added":["u_lprg.w_data[31:0]","u_lprg.w_zero","u_lprg.w_one"],
 "token":"boot visibility +1 edge (setup_ready, sealed config); KV latency table unchanged"}
s=json.dumps(j,indent=1)
assert "/srv/" not in s and "/home/" not in s, [m for m in re.findall(r'"(/(?:srv|home)/[^"]*)"',s)][:5]
open(C+"qkd_kvs_ctl_core.json","w").write(s+"\n"); print(len(j["files"]),"files")
