import json,sys,collections,math,re
from pathlib import Path
d=Path(sys.argv[1]); p=json.loads((d/"die_plan.json").read_text())
MODS=sys.argv[2].split(",")
def tr(o,W,H,x,y): return {"R0":(x,y),"MY":(W-x,y),"MX":(x,H-y),"R180":(W-x,H-y)}[o or "R0"]
res=collections.Counter(); dist=[]
for tn,t in p["partition_types"].items():
    cs={}
    for c in t.get("hard_cores",[]):
        if not any(m in c["module"] for m in MODS): continue
        W,H=c["outline_um"]; ox,oy=c["origin_um"]; g=collections.defaultdict(list)
        for q in json.loads((d/c["pins_file"]).read_text()):
            x,y=tr(c.get("orient"),W,H,q["x"],q["y"]); g[q["name"].split("[")[0]].append((ox+x,oy+y))
        cs[c["inst"]]=g
    for e in t.get("internal_stations",[]):
        for side,key in (("capture","to_um"),("launch","from_um")):
            s=str(e.get(side,""))
            if "." not in s: continue
            inst,port=s.split(".",1)
            ks=[k for k in cs if k==inst or re.sub(r"__q\d+$","",k)==inst]
            if not ks: continue
            dm=min(math.dist(q,e[key]) for k in ks for q in cs[k].get(port,[(1e9,1e9)]))
            res["on_pin" if dm<1 else ("lt20" if dm<20 else "far")]+=1; dist.append(dm)
print(dict(res), "max", round(max(dist),1))
