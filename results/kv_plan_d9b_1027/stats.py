import json,sys,collections
from pathlib import Path
sys.path.insert(0,sys.argv[1]+"/tools/die_plan"); import schema as S
for f in sys.argv[2:]:
    P=S.Plan(S.load(f),Path(f)); over=0; bits=0; tot=0
    for pid,pr in P.ports.items():
        if "hub_Wi" not in (pr["src"]["part"],pr["dst"]["part"]): continue
        ft=any(pr[k]["part"]!="@die" and P.buses(pr[k]["part"]).get(pr[k]["bus"],{}).get("slot") for k in ("src","dst"))
        n=S.port_pins_count(pr)
        if not ft or n<16: continue
        tot+=1
        d=max((b1-b0)/max(w[1]-w[0],.05) for b0,b1,w in S.port_segments(pr))
        if d>8+1e-6: over+=1; bits+=n
    print(f, "hub_Wi FT ports(>=16b):",tot,">8 b/um:",over,"bits",bits)
L=json.load(open("ledger_d9b.json")); print("stuck",collections.Counter((x["type"],x["why"]) for x in L["stuck"]))
print("slit stuck", [(x["slot"],x["station"],x["bbox"]) for x in L["stuck"] if x["why"]=="slit"])
print("reshaped",[(x["slot"],x["station"],x["reshaped"]) for x in L["stations"]+L["repair"] if "reshaped" in x])
print("kept_by_reach",len(L["kept_by_reach"]))
