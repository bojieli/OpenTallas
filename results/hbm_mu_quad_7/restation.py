"""QUAD-7: re-site internal-station endpoints (and the adjacent landing reg) of cores whose
outline/pin table changed (measured-content outline TRIAL) onto the new pin positions."""
import json,sys,collections,math,re
from pathlib import Path
d=Path(sys.argv[1]); p=json.loads((d/"die_plan.json").read_text())
ref=json.loads(Path(sys.argv[2]).read_text())
OLD={(tn,c["inst"]):(c["origin_um"],c["outline_um"]) for tn,t in ref["partition_types"].items() for c in t.get("hard_cores",[])}
def face(pt,o,w):
    x0,y0=o; x1,y1=x0+w[0],y0+w[1]
    dd=[abs(pt[0]-x0),abs(pt[0]-x1),abs(pt[1]-y0),abs(pt[1]-y1)]
    return "WESN"[dd.index(min(dd))]
def tr(o,W,H,x,y): return {"R0":(x,y),"MY":(W-x,y),"MX":(x,H-y),"R180":(W-x,H-y)}[o or "R0"]
rep=collections.Counter(); far=[]
for tn,t in p["partition_types"].items():
    chg={}
    for c in t.get("hard_cores",[]):
        if "measured-content outline TRIAL" not in c.get("note",""): continue
        W,H=c["outline_um"]; ox,oy=c["origin_um"]
        pins=json.loads((d/c["pins_file"]).read_text())
        g=collections.defaultdict(list)
        for q in pins:
            x,y=tr(c.get("orient"),W,H,q["x"],q["y"]); g[q["name"].split("[")[0]].append((ox+x,oy+y))
        chg[c["inst"]]=(c,dict(g))
    if not chg: continue
    for e in t.get("internal_stations",[]):
        for side,key,ri in (("capture","to_um",-1),("launch","from_um",0)):
            s=str(e.get(side,""))
            if "." not in s: continue
            inst,port=s.split(".",1)
            cands=[k for k in chg if k==inst or re.sub(r"__q\d+$","",k)==inst]
            if not cands: continue
            old=e[key]
            cands=[k for k in cands if port in chg[k][1]] or cands
            k=min(cands,key=lambda k:min((math.dist(q,old) for q in chg[k][1].get(port,[(1e9,1e9)]))))
            c,pm=chg[k]
            if port not in pm: rep["port_missing"]+=1; far.append((tn,inst,port)); continue
            of=face(old,*OLD[(tn,k)])
            same=[q for q in pm[port] if face(q,c["origin_um"],c["outline_um"])==of]
            if not same: rep["face_changed"]+=1
            new=[round(v,3) for v in min(same or pm[port],key=lambda q:math.dist(q,old))]
            if e["regs_um"]:
                r=e["regs_um"][ri]
                if math.dist(r,old)<60:
                    e["regs_um"][ri]=[round(r[0]-old[0]+new[0],3),round(r[1]-old[1]+new[1],3)]
                    rep["landing_reg_moved"]+=1
            e[key]=new; rep["endpoint_moved"]+=1
            e["note"]=e.get("note","")+"; QUAD-7 restation onto content-outline pins"
(d/"die_plan.json").write_text(json.dumps(p,indent=1)+"\n")
print(dict(rep)); print("missing",far[:10])
