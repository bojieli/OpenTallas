"""Static macro-fit check of the outline proposals: can the macros (with 4.32 um halo, 8.64 lattice) be stacked in
rows/columns inside the proposed outline, leaving free area for std cells at <= 0.6 fill? Grid packing (k columns x r rows)."""
import json,sys,math
P=json.load(open(sys.argv[1]))["proposals"]; H=4.32
out=[]
for p in P:
    W,Hh=p["outline_proposed_um"]; res=[]
    for m in p.get("macros",[]):
        w,h=m["um"]; n=m["n"]; best=None
        for rot in (False,True):
            mw,mh=(h,w) if rot else (w,h)
            cw,ch=mw+2*H,mh+2*H
            for cols in range(1,n+1):
                rows=math.ceil(n/cols)
                if cols*cw<=W+1e-6 and rows*ch<=Hh+1e-6:
                    best=dict(rot=rot,cols=cols,rows=rows,used=[round(cols*cw,2),round(rows*ch,2)]); break
            if best: break
        res.append(dict(macro=m["name"],n=n,fit=best))
    mac=sum(m["n"]*(m["um"][0]+2*H)*(m["um"][1]+2*H) for m in p.get("macros",[]))
    free=W*Hh-mac; fill=p["std_area_um2"]/free if free>0 else None
    out.append(dict(kit=p["kit"],outline=p["outline_proposed_um"],limit=p.get("limit"),pins=p["pins"],
                    perim_pin_cap=round(2*(W+Hh)/0.192),macros=res,all_fit=all(r["fit"] for r in res),
                    std_fill_of_free=round(fill,3) if fill else None))
json.dump(out,open(sys.argv[2],"w"),indent=1)
for o in out: print(o["kit"][:45],o["outline"],o["limit"],"macros_fit",o["all_fit"],[ (r["n"],r["fit"]) for r in o["macros"]],"fill",o["std_fill_of_free"],"pins",o["pins"],"/",o["perim_pin_cap"])
