"""HBM-MU-QUAD-8 (GEOM-REVIEW-30 12:10 FAIL fix): the 3 resized content-trial types kept their OLD core-frame clock entry.
Re-site the 12.8a centre entry island to the new outline centre on the 4.32 lattice (nearest lattice point; ties -> lower),
clear of the type's macros (core_macros.json; wr_q lanes4 SRAM u_fcore.u_tab y<=58.4), every instance (NW + NE)."""
import json,sys,math
from pathlib import Path
d=Path(sys.argv[1]); e=json.loads((d/"clock_entries.json").read_text()); p=json.loads((d/"die_plan.json").read_text())
cm=json.loads((d/"core_macros.json").read_text())["cores"]
OUT={m:None for m in ("ot_hgi_coll_inj_idx_join_rg","ot_hbm_sm_vm_wr_q_t_lanes4","ot_hbm_idx_vm_query_static_n12")}
for t in p["partition_types"].values():
    for c in t.get("hard_cores",[]):
        if c["module"] in OUT: OUT[c["module"]]=c["outline_um"]
snap=lambda v:math.floor(v/4.32+0.5-1e-9)*4.32 if abs(v/4.32-round(v/4.32))>1e-6 else round(v/4.32)*4.32
snapdown=lambda v:round(math.floor(v/4.32+1e-9)*4.32,3) if abs((v/4.32)%1-0.5)<1e-6 else round(round(v/4.32)*4.32,3)
n=0
for tn,dd in e.items():
    for inst,v in dd.items():
        m=v.get("module")
        if m not in OUT: continue
        W,H=OUT[m]; x,y=snapdown(W/2),snapdown(H/2)
        isl=[round(x-4.32,3),round(y-4.32,3),round(x+4.32,3),round(y+4.32,3)]
        for mc in (cm.get(m) or {}).get("macros",[]):
            r=mc["rect_um"]; assert not (isl[0]<r[2] and r[0]<isl[2] and isl[1]<r[3] and r[1]<isl[3]),(m,mc)
        print(tn,inst,m,v["xy_um"],"->",[x,y]); v["xy_um"]=[x,y]; v["island_um"]=isl
        v["source"]+=f"; QUAD-8 re-sited to the {W}x{H} content-outline centre (GEOM-30 12:10)"; n+=1
(d/"clock_entries.json").write_text(json.dumps(e,indent=1)+"\n"); print("entries re-sited",n)
