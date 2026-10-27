import json,sys
d=sys.argv[1]; apply=len(sys.argv)>2 and sys.argv[2]=="apply"
p=json.load(open(d+"/die_plan.json"))
ent=json.load(open(d+"/clock_entries.json"))
MOD="ot_hbm_idx_vm_query_static_n12"; DH=30.24
log=[]
for tn,ty in p["partition_types"].items():
    W,H=ty["outline_um"]
    cs=ty.get("hard_cores",[])
    for c in cs:
        if c["module"]!=MOD: continue
        best=None; cand=[]
        for s in (0,-7.56,-15.12,-22.68,-30.24):
            x0,y0=c["origin_um"][0],c["origin_um"][1]+s
            a=(x0,y0,x0+c["outline_um"][0],y0+c["outline_um"][1])
            if a[1]<0 or a[3]>H or a[2]>W: continue
            mg=1e9
            for b in cs:
                if b is c: continue
                bb=(b["origin_um"][0],b["origin_um"][1],b["origin_um"][0]+b["outline_um"][0],b["origin_um"][1]+b["outline_um"][1])
                gx=max(bb[0]-a[2],a[0]-bb[2]); gy=max(bb[1]-a[3],a[1]-bb[3])
                g=max(gx,gy)
                mg=min(mg,g)
            # also stations/ft regs inside? ignored here (G0 checks)
            cand.append((s,round(mg,3)))
            if best is None or mg>best[1]: best=(s,round(mg,3))
        log.append((tn,c["inst"],c["origin_um"],best,cand[:1]))
        g0=[x for x in cand if x[0]==0]
        if apply and best[0]!=0 and (not g0 or g0[0][1]<10.8):
            c["origin_um"]=[c["origin_um"][0],round(c["origin_um"][1]+best[0],6)]
            c["note"]=c.get("note","")+f"; QUAD-7 grow-down {best[0]} um to keep neighbour channel"
for l in log: print(l)
if apply:
    json.dump(p,open(d+"/die_plan.json","w"),indent=1); open(d+"/die_plan.json","a").write("\n")
