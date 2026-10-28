import json,gzip,collections,sys
p=json.load(gzip.open(sys.argv[1]))
pt=p["partition_types"]
def xf(o,orient,W,H,r):
    x0,y0,x1,y1=r
    if orient in("MY","R180"): x0,x1=W-x1,W-x0
    if orient in("MX","R180"): y0,y1=H-y1,H-y0
    return [o[0]+x0,o[1]+y0,o[0]+x1,o[1]+y1]
out=[];parts=[]
for q in p["partitions"]:
    t=pt[q["type"]]; W,H=t["outline_um"]; o=q["origin_um"]
    pr=[o[0],o[1],o[0]+W,o[1]+H]; parts.append(dict(name=q["name"],type=q["type"],module=t["module"],rect=pr))
    seen=set()
    for key in ("hard_cores","contents"):
        for c in t.get(key,[]):
            if c.get("origin_um") is None or c.get("outline_um") is None: continue
            if c["inst"] in seen: continue
            seen.add(c["inst"])
            r=[c["origin_um"][0],c["origin_um"][1],c["origin_um"][0]+c["outline_um"][0],c["origin_um"][1]+c["outline_um"][1]]
            out.append(dict(part=q["name"],ptype=q["type"],inst=c["inst"],module=c["module"],src=key,rect=xf(o,q.get("orient","R0"),W,H,r)))
json.dump(dict(parts=parts,cores=out),open(sys.argv[2],"w"))
m=collections.defaultdict(lambda:[0,0.0])
for c in out:
    r=c["rect"]; m[c["module"]][0]+=1; m[c["module"]][1]+=(r[2]-r[0])*(r[3]-r[1])/1e6
die=p["die"]["outline_um"]; pa=sum((x["rect"][2]-x["rect"][0])*(x["rect"][3]-x["rect"][1]) for x in parts)/1e6
print("die mm2",die[0]*die[1]/1e6,"parts mm2",round(pa,2),"cores mm2",round(sum(v[1] for v in m.values()),2))
for k,v in sorted(m.items(),key=lambda x:-x[1][1]): print(f"{k:40s} {v[0]:5d} {v[1]:8.3f}")
