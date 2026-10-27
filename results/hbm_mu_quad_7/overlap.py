import json,sys
p=json.load(open(sys.argv[1]+"/die_plan.json"))
focus=set(sys.argv[2].split(",")) if len(sys.argv)>2 else None
for tn in ("q_hub_nw","q_hub_ne","q_su00"):
    ty=p["partition_types"][tn]
    W,H=ty.get("outline_um",[None,None])
    cs=ty.get("hard_cores",[])
    R=[(c["inst"],c["origin_um"][0],c["origin_um"][1],c["origin_um"][0]+c["outline_um"][0],c["origin_um"][1]+c["outline_um"][1]) for c in cs]
    print(tn,"outline",W,H,"cores",len(R))
    for a in R:
        if focus and not any(f in a[0] for f in focus): continue
        out = W and (a[1]<0 or a[2]<0 or a[3]>W+1e-6 or a[4]>H+1e-6)
        gaps=[]
        for b in R:
            if b is a: continue
            ox=min(a[3],b[3])-max(a[1],b[1]); oy=min(a[4],b[4])-max(a[2],b[2])
            if ox>-4.32 and oy>-4.32: gaps.append((b[0],round(ox,3),round(oy,3)))
        print(" ",a[0],[round(v,3) for v in a[1:]],"OUT" if out else "", gaps)
