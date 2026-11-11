#!/usr/bin/env python3
"""DIE-HBM-83-OPSG: new recipe keys ot_hgi_sfu_opsa_group0/1 + opsb_group __gp (OT_OPSG_GP, N32 banks). recipes_gp.py RECIPES_B2_JSON SRC_SHA"""
import json,sys
p,src=sys.argv[1:3]; raw=open(p).read(); d=json.loads(raw); assert json.dumps(d,indent=2,ensure_ascii=False)+"\n"==raw
D="rtl/hbm_accel/cores_split/reform_1105s/opstore/"
for k in ("ot_hgi_sfu_opsa_group0","ot_hgi_sfu_opsa_group1","ot_hgi_sfu_opsb_group"):
    b=d[k]; d[k+"__gp"]=dict(b,defines=["OT_OPSG_GP"],files=list(b["files"])+[D+"ot_hgi_su_lbank_n32.sv",D+"ot_hgi_su_lgroup2_gp.sv"],macros=["ot_sram_1r1w_2048x32_m8_r0c0_g32"],cts_delay_buffer_derate=0,util=0.40,
      source=b["source"]+"; DIE-HBM-83-OPSG part 57 hub form: N32 banks, macro-free logic hub, flop on every haul; PIN CYCLES rd +5, flt 0; lock-step bench results/die_hbm_1106/opsg_gp",source_commit=src)
open(p,"w").write(json.dumps(d,indent=2,ensure_ascii=False)+"\n"); print("recipes ->",src)
