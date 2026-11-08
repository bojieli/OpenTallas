#!/usr/bin/env python3
"""Opt-in KSH F3 only. Same-edge retained local FIFO control, PIN delta0 vs F2."""
import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'physical/die_plan/hbm_arch_cores'
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('gen_core_kit_hbm',HERE/'gen_core_kit_hbm.py')
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
files=['rtl/hbm_accel/loader/service_native/'+x for x in ['ot_hbm_svc_vmks_f3.sv','ot_hbm_svc_vmks_forms.sv','ot_hbm_svc_async_fifo.sv','ot_hbm_svc_pc_ctrl_leaf.sv','ot_hbm_svc_ring_h9b_ff.sv','ot_hbm_svc_vm_kshare_splitstrap.sv']]+['rtl/lib/ot_reset_sync.sv']
rec=G.load_recipes();patch={}
for k in ['ot_hbm_svc_vm_kshare_splitstrap__v700685','ot_hbm_svc_vm_kshare_splitstrap__v8e478a']:
 r=dict(rec[k]);r.update(top='ot_hbm_svc_vm_kshare_splitstrap_f3',files=files,params=dict(MUT=0,KRL1=1,GUARD=3),read_at_commit=False)
 r['source']='CODEX KSH F3: exact same-edge private local FIFO online/reset class, PIN delta0 relative F2; source in current committed own tree'
 patch[k]=r
G.main(recipe_overrides=patch)
