import sys,json,collections
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2]))
rows=[]
for pid,pr in P.ports.items():
    ft=any(pr[k]["part"]!="@die" and P.buses(pr[k]["part"]).get(pr[k]["bus"],{}).get("slot") for k in ("src","dst"))
    if not ft: continue
    cs=[c for _,_,c in P.port_pins(pid)]; n=len(cs); span=max(cs)-min(cs) if n>1 else 0
    if n<16: continue
    d=n/max(span,0.05)
    if d>8.0+1e-6: rows.append((round(d,2),pid,pr["src"]["part"],pr["dst"]["part"],n,round(span,1),bool(pr.get("_geom_from")),P.parts[pr["src"]["part"]]["type"] if pr["src"]["part"]!="@die" else "@die"))
rows.sort(reverse=True)
print("FT ports >8 b/um:",len(rows))
for r in rows: print(r)
