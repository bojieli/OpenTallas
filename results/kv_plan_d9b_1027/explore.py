import sys,json,collections
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2]))
ninst=collections.Counter(p["type"] for p in P.parts.values())
t=P.types["kv3_hub_Wi"]; print("hub_Wi outline",t["outline_um"], "rect", P.rect("hub_Wi"), "orient", P.parts["hub_Wi"].get("orient"))
for c in t["hard_cores"]: print(" core",c["module"],c["origin_um"],c["outline_um"])
for s in t.get("ft_slots",[]):
    bs=s.get("bit_sites_um",[])
    print(" slot",s["name"],s["in_face"],s["out_face"],s["width"],"st",s.get("stations"),"bbox",[ (round(min(p[0] for p in st),1),round(min(p[1] for p in st),1),round(max(p[0] for p in st),1),round(max(p[1] for p in st),1)) for st in bs])
print("ports touching hub_Wi (>=16 b):")
for pid,pr in P.ports.items():
    a,b=pr["src"]["part"],pr["dst"]["part"]
    if "hub_Wi" not in (a,b): continue
    cs=[c for _,_,c in P.port_pins(pid)]; n=len(cs); span=max(cs)-min(cs) if n>1 else 0
    ft=any(pr[k]["part"]!="@die" and P.buses(pr[k]["part"]).get(pr[k]["bus"],{}).get("slot") for k in ("src","dst"))
    other=b if a=="hub_Wi" else a
    ot=P.parts[other]["type"] if other!="@die" else "@die"
    d=n/max(span,0.05)
    if n>=16: print(f"  {pid} {a}->{b} face {pr['face']} n {n} span {span:.1f} {d:.2f} b/um ft={ft} other {ot} x{ninst.get(ot)} segs={bool(pr.get('segments'))} win {pr.get('window_um')}")
