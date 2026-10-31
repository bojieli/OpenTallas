# DIE-HBM-44: list slot data + face occupancy (read-only)
import json,sys
p=json.load(open(sys.argv[1])); T=p["partition_types"]
def wins(t):
    out=[]
    for kind in ("buses","ft_slots","spare_slots"):
        for s in t.get(kind,[]):
            if "face" in s and "window_um" in s: out.append((s["face"],s["window_um"],s.get("layers"),kind,s["name"]))
            for io in ("in","out"):
                if s.get(io+"_face") and s.get(io+"_window_um"): out.append((s[io+"_face"],s[io+"_window_um"],s.get(io+"_layers"),kind,s["name"]+"."+io))
    return out
for spec in sys.argv[2:]:
    tn,slot=spec.split(":")
    t=T[tn]
    s=[x for x in t["ft_slots"] if x["name"]==slot][0]
    print("==",tn,slot,{k:v for k,v in s.items()})
    for io in ("in","out"):
        f=s[io+"_face"]; w=s[io+"_window_um"]
        near=[x for x in wins(t) if x[0]==f and x[1][1]>w[0]-200 and x[1][0]<w[1]+200]
        print("  face",io,f,w,"neighbours:",sorted([(round(x[1][0],2),round(x[1][1],2),x[2],x[4]) for x in near]))
