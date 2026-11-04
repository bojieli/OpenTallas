import json,sys
sys.argv=["x","physical/die_plan/s81/plan_h2_2249.json","../ds53-eg-tmp/plan_n.json"]
p=json.load(open(sys.argv[1]))
def mv(tn,sl,oldx,nx):
    t=p["partition_types"][tn]; s=[q for q in t["ft_slots"] if q["name"]==sl][0]
    for j,st in enumerate(s["bit_sites_um"]):
        if st[0][0]==oldx:
            s["bit_sites_um"][j]=[[nx,y] for x,y in st]; s["regs_um"][j+1]=[nx,s["regs_um"][j+1][1]]; print(tn,sl,j,oldx,"->",nx); return
    raise SystemExit((tn,sl,oldx))
mv("dsdv_slice_c3x_C__t1","ft1",872.64,900.018)
mv("dsdv_slice_c1x_C__t6","ft2",1175.04,1164.996)
mv("dsdv_slice_c1x_C__t6","ft1",1183.68,1164.996)
json.dump(p,open(sys.argv[2],"w"))
