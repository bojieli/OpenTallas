"""12.14b estimate: FT bits crossing vertical cuts in hub_Wi horizontal bands (chain hop segments, L-shaped H-first)
vs layer-summed H capacity per gcell row from the coupon congestion.rpt (capacity field)."""
import json, sys, re, collections
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
f=sys.argv[2]; raw=json.load(open(f)); P=S.Plan(raw,Path(f)); ty=raw["partition_types"]["kv3_hub_Wi"]
rpt=open(sys.argv[3]).read().split("violation type: ")[1:]
capH=collections.Counter(int(re.search(r"capacity:(\d+)",e).group(1)) for e in rpt if e.startswith("Horizontal"))
print("2D H capacity per gcell seen in overflow gcells:",capH.most_common(4))
bands={"bottom y<121":(0,121),"middle y613-855":(613,855),"top y1555-1676":(1555,1676)}
for x in (450,600,750,900):
    out={}
    for bn,(y0,y1) in bands.items():
        tot=0;who=[]
        for s in ty["ft_slots"]:
            regs=s.get("regs_um") or []
            for a,b in zip(regs,regs[1:]):
                if min(a[0],b[0])<x<max(a[0],b[0]):
                    yh=a[1]  # H-first L: horizontal leg at the earlier register's y
                    if y0<=yh<=y1: tot+=s["width"]+1;who.append(s["name"])
        out[bn]=(tot,round(tot/((y1-y0)/10.8),1))
    print("cut x=%d"%x,{k:f"{v[0]} b, {v[1]} b/gcell-row" for k,v in out.items()})
