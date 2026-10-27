"""QUAD-7: snap changed hard-core origins to the 8.64-um lattice; move their station endpoints with them."""
import json,sys,re,math
from pathlib import Path
d=Path(sys.argv[1]); p=json.loads((d/"die_plan.json").read_text()); n=0; ep=0
for tn,t in p["partition_types"].items():
    for c in t.get("hard_cores",[]):
        if "measured-content outline TRIAL" not in c.get("note",""): continue
        o=c["origin_um"]; s=[round(round(v/8.64)*8.64,6) for v in o]
        dx,dy=s[0]-o[0],s[1]-o[1]
        if abs(dx)<1e-6 and abs(dy)<1e-6: continue
        x0,y0=o; x1,y1=x0+c["outline_um"][0],y0+c["outline_um"][1]
        base=re.sub(r"__q\d+$","",c["inst"])
        for e in t.get("internal_stations",[]):
            for side,key in (("capture","to_um"),("launch","from_um")):
                s_=str(e.get(side,""))
                if "." not in s_ or s_.split(".")[0] not in (c["inst"],base): continue
                q=e[key]
                if x0-.1<=q[0]<=x1+.1 and y0-.1<=q[1]<=y1+.1:
                    e[key]=[round(q[0]+dx,3),round(q[1]+dy,3)]; ep+=1
        c["origin_um"]=s; c["note"]+=f"; QUAD-7 origin snapped to 8.64 lattice ({dx:+.3f},{dy:+.3f})"; n+=1
(d/"die_plan.json").write_text(json.dumps(p,indent=1)+"\n"); print("cores snapped",n,"endpoints moved",ep)
