#!/usr/bin/env python3
"""DIE-HBM-66 11-05 Sinkhorn port (part 16): recipes and rest wrappers for the row Sinkhorn tail. Idempotent; --check fails on drift.
ot_hbm_hc_root_static__tailx_sk_fsr replaces tailx_sk_step0 + tailx_sk_steady (one core per tail, step0 slot).
tailx_rest_fsr__v6bc7f2 / v4f4566: same pins as tailx_rest__*, rest core on the row calendar (wider age, CAP measured, no enable)."""
import json,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]; H=REPO/"physical/die_plan/hbm_arch_cores"; RP=H/"recipes_b2.json"
F="rtl/hbm_accel/cores_split/sk_fsr_1105/"
SRC="DIE-HBM-66 11-05 COORD ruling A: S81 row Sinkhorn on HBM tail; lockstep results/die_hbm_1105/sk_fsr (FSR_EQ PASS, mutants FAIL)."
def recipes(r):
    n={}
    n["ot_hbm_hc_root_static__tailx_sk_fsr"]=dict(defines=[],files=["rtl/hdc/v41/ot_hdc_sk_arith.sv","rtl/hdc/v41/ot_hdc_sk_recip_rom.sv","rtl/hdc/v41/ot_hdc_skf_predecode.sv","rtl/hdc/v41/ot_hdc_sinkhorn_fs.sv",F+"ot_hbm_hc_tail_sk_fsr.sv"],functional_type="hc_sk_fsr",macros=[],params={},source=SRC,top="ot_hbm_hc_tail_sk_fsr",synth_memory_max_bits=35328)
    for v in ("v6bc7f2","v4f4566"):
        o=dict(r[f"ot_hbm_hc_root_static__tailx_rest__{v}"])
        o["top"]="ot_hbm_hc_tail_rest_core_fsr"; o["source"]=SRC
        o["files"]=[x if not x.endswith("/ot_hbm_hc_tail_rest_core_ce.sv") else F+"ot_hbm_hc_tail_rest_core_fsr.sv" for x in o["files"]]
        n[f"ot_hbm_hc_root_static__tailx_rest_fsr__{v}"]=o
    return n
def wrap(v):
    t=(H/f"wrappers/ot_hbm_hc_root_static__tailx_rest__{v}.sv").read_text()
    a=f"module ot_hbm_hc_root_static__tailx_rest__{v} ("; b="ot_hbm_hc_tail_rest_core_ce #(.CAP(299)) u_core ("
    if t.count(a)!=1 or t.count(b)!=1: raise SystemExit("wrapper anchors "+v)
    return t.replace(a,f"module ot_hbm_hc_root_static__tailx_rest_fsr__{v} (").replace(b,"ot_hbm_hc_tail_rest_core_fsr u_core (")
r=json.loads(RP.read_text()); n=recipes(r); chk="--check" in sys.argv; bad=[]
for k,v in n.items():
    if r.get(k)!=v: bad.append(k)
    r[k]=v
for v in ("v6bc7f2","v4f4566"):
    p=H/f"wrappers/ot_hbm_hc_root_static__tailx_rest_fsr__{v}.sv"; t=wrap(v)
    if not p.exists() or p.read_text()!=t:
        bad.append(p.name)
        if not chk: p.write_text(t)
if chk:
    if bad: raise SystemExit("DRIFT "+str(bad))
    print("sk_fsr_recipes check PASS")
else:
    RP.write_text(json.dumps(r,indent=1)+"\n"); print("wrote",bad)
