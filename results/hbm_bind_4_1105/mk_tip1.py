#!/usr/bin/env python3
"""HBM-BIND-4 tip asbuilt step 1 (candidate, private tree). add_lat prefer -> tip file (XCUTS default 0, same function).
Bind-local NQ-capable ot_hbm_hc_root_static_s = gen_hc_tail_s.py's edits applied to tip ot_hbm_hc_root_static.sv (NQ since 9273690654);
the main _s predates NQ."""
import json,os,sys
T=sys.argv[1]; H=T+"/rtl/hbm_accel/generic/peers/static_hc/"
s=open(H+"ot_hbm_hc_root_static.sv").read()
for a,b in [('module ot_hbm_hc_root_static #(','module ot_hbm_hc_root_static_s #('),
 ('    parameter integer MUT  = 0,\n','    parameter integer MUT  = 0,\n    parameter integer SMUT = 0,                  // split bench mutant (tail_unit_s SMUT)\n'),
 ('ot_hbm_hc_tail_unit_static #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0)) u_t (','ot_hbm_hc_tail_unit_static_s #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0), .SMUT(SMUT)) u_t (')]:
    assert s.count(a)==1,a
    s=s.replace(a,b)
s="// HBM-BIND-4 11-05: gen_hc_tail_s.py twin edits on tip ot_hbm_hc_root_static.sv (NQ-capable). Candidate.\n"+s
L="physical/die_plan/hbm/bind/rtl/hb4/ot_hbm_hc_root_static_s.sv"
os.makedirs(os.path.dirname(T+"/"+L),exist_ok=True); open(T+"/"+L,"w").write(s)
P=T+"/physical/die_plan/hbm/bind/d44v/asbuilt.json"
a=json.load(open(P))
old="physical/die_plan/hbm/bind/r18h5_bundle/rtl/hdc/ot_hdc_fp32_add_lat.sv"
assert old in a["prefer"]
a["prefer"]=[("rtl/hdc/ot_hdc_fp32_add_lat.sv" if p==old else p) for p in a["prefer"]]+[L]
a["files"]=a["files"]+[L]
a["note"]="HBM-BIND-4 tip1: add_lat tip + NQ root_s | "+a["note"]
tmp=P+".tmp"; json.dump(a,open(tmp,"w"),indent=1); os.unlink(P); os.replace(tmp,P)
