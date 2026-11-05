#!/usr/bin/env python3
"""rootmac.py PLAN_DIR: plan rects of the two TKM root buffer macros (no placed evidence at this outline). Central column, three equal bands, replace (plan tree is hard-linked)."""
import json,os,sys
from pathlib import Path
f=Path(sys.argv[1])/'core_macros.json'; d=json.loads(f.read_text()); W,H=319.68,345.6; w,h=174.744,70.488
x=round((W-w)/2/0.216)*0.216; b=(H-2*h)/3; ys=[round(b/0.27)*0.27,round((2*b+h)/0.27)*0.27]
M=[{"name":f"u_x.u.u_buffer.g_bm[{i}].u_b","master":"ot_sram_1r1w_1024x256_m2_r2c2","rect_um":[round(x,3),round(y,3),round(x+w,3),round(y+h,3)]} for i,y in enumerate(ys)]
d["cores"]["ot_hgi_coll_tkm_m_tp192__root"]={"status":"KNOWN","outline_um":[W,H],"basis":"plan_part19","macros":M,"sources":[],"recipe_macros":["ot_sram_1r1w_1024x256_m2_r2c2"]}
t=f.with_suffix('.tmp'); t.write_text(json.dumps(d,indent=1)+"\n"); os.replace(t,f); print(M)
