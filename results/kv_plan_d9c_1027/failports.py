"""map failed d9c slots (ledger) to the hub_Wi-face ports at the failing hop ends -> print port ids to keep"""
import json, sys
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
f=sys.argv[2]; raw=json.load(open(f)); P=S.Plan(raw,Path(f)); L=json.load(open(sys.argv[3]))
win=set(w["port"] for w in json.load(open(sys.argv[4]))["windows"])
out=set()
for fl in L["failed"]:
    part,sn,k=fl["part"],fl["slot"],fl["stations"]
    for q,pr in P.ports.items():
        if (pr["dst"]["part"],pr["dst"]["bus"])==(part,sn+"_i") or (pr["src"]["part"],pr["src"]["bus"])==(part,sn+"_o"):
            if q in win: out.add(q)
print(" ".join(sorted(out)))
