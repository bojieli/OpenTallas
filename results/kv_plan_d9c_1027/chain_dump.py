import json, sys
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
f=sys.argv[2]; raw=json.load(open(f)); P=S.Plan(raw,Path(f))
ty=raw["partition_types"]["kv3_hub_Wi"]; W,H=ty["outline_um"]
print("hub_Wi outline",W,H,"rect",P.rect("hub_Wi"),"hub_C rect",P.rect("hub_C"))
cores=sorted(tuple(round(v,1) for v in bx) for bx in S.placed_macro_boxes(P.ptype("hub_Wi")).values())
print("cores",cores)
want=sys.argv[3].split(",")
for s in ty["ft_slots"]:
    if s["name"] not in want: continue
    regs=s.get("regs_um"); print(s["name"],"w",s["width"]+1,"in",s["in_face"],"out",s["out_face"],"stations",s.get("stations"))
    for j,r in enumerate(regs): print("   reg",j,r, "hop" , round(abs(r[0]-regs[j-1][0])+abs(r[1]-regs[j-1][1]),1) if j else "")
