import json,sys
A=json.load(open(sys.argv[1]));B=json.load(open(sys.argv[2]))
def chain(t,s):
    W,H=t["outline_um"]; r=s.get("regs_um") or []
    a,b=s["out_window_um"]; m=(a+b)/2; f=s["out_face"]
    end={"E":[W,m],"W":[0,m],"N":[m,H],"S":[m,0]}[f]
    pts=r+[end]; return [abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(pts,pts[1:])]
import re
for tn in [t for t in sorted(A["partition_types"]) if re.match(r"^(sle|slw)_sc_",t)]:
    ta,tb=A["partition_types"][tn],B["partition_types"][tn]
    for sa,sb in zip(ta["ft_slots"],tb["ft_slots"]):
        ha,hb=chain(ta,sa),chain(tb,sb)
        if max(hb)>405: print(tn,sa["name"],[round(x) for x in ha],"->",[round(x) for x in hb], [[round(v) for v in p] for p in sb["regs_um"]])
