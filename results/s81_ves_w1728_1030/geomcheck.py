import json,sys,collections
P=json.load(open(sys.argv[1]));pt=P["partition_types"];newW=172.8;H=345.6
rows=[];orients=collections.Counter()
def box(c,w=None,shift=0):
    ox,oy=c["origin_um"];dx,dy=c.get("track_offset_um",[0,0]);cw,ch=c["outline_um"]
    if w: cw=w
    return (ox+dx+shift,oy+dy,ox+dx+shift+cw,oy+dy+ch)
for tn,t in pt.items():
    hc=t.get("hard_cores") or []
    v=[c for c in hc if c["module"]=="ot_s81sl_ve_s"]
    if not v: continue
    v=v[0];orients[v.get("orient","R0")]+=1
    sh=-8.64 if v.get("orient","R0") in ("MY","R180") else 0; nb=box(v,newW,sh);W,Hh=t["outline_um"]
    others=[c for c in hc if c is not v]+[c for c in t.get("contents",[]) if "origin_um" in c and "outline_um" in c]
    mingap=1e9;worst=None;ov=[]
    for c in others:
        b=box(c)
        gx=max(b[0]-nb[2],nb[0]-b[2]);gy=max(b[1]-nb[3],nb[1]-b[3])
        if gx<-1e-6 and gy<-1e-6: ov.append(c["inst"])
        g=max(gx,gy)
        if g<mingap: mingap=g;worst=c["inst"]
    inside=nb[0]>=-1e-6 and nb[1]>=-1e-6 and nb[2]<=W+1e-6 and nb[3]<=Hh+1e-6
    taps=[tp for tp in t.get("clock",{}).get("taps",[]) if "ve" in json.dumps(tp)]
    rows.append(dict(type=tn,orient=v.get("orient","R0"),new_box=[round(x,3) for x in nb],inside=inside,overlaps=ov,min_gap_um=round(mingap,3),nearest=worst,ve_taps=len(taps)))
print(json.dumps(dict(types=len(rows),orients=orients,overlap_types=[r["type"] for r in rows if r["overlaps"]],outside=[r["type"] for r in rows if not r["inside"]],min_gap=min(r["min_gap_um"] for r in rows),gap_hist=collections.Counter(r["min_gap_um"] for r in rows))))
json.dump(rows,open("parent_geom.json","w"),indent=1)
