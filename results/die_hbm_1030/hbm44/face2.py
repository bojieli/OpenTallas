# list all windows on type face within [lo,hi]
import json,sys
p=json.load(open(sys.argv[1])); T=p["partition_types"]
def wins(t):
    out=[]
    for kind in ("buses","ft_slots","spare_slots"):
        for s in t.get(kind,[]):
            if "face" in s and "window_um" in s: out.append((s["face"],s["window_um"],s.get("layers"),s["name"]))
            for io in ("in","out"):
                if s.get(io+"_face") and s.get(io+"_window_um"): out.append((s[io+"_face"],s[io+"_window_um"],s.get(io+"_layers"),s["name"]+"."+io))
    return out
for spec in sys.argv[2:]:
    tn,f,lo,hi=spec.split(":"); lo=float(lo); hi=float(hi)
    print(tn,f,T[tn]["outline_um"],sorted([(round(w[1][0],2),round(w[1][1],2),w[2],w[3]) for w in wins(T[tn]) if w[0]==f and w[1][1]>=lo and w[1][0]<=hi]))
