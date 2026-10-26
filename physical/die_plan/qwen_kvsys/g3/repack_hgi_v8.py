#!/usr/bin/env python3
"""Rebalance kv3_hgi_v8 FT4/17/26/27 across existing free channels; pins/counts/cycles unchanged."""
from pathlib import Path
import sys,json
W=Path(__file__).resolve().parents[4]
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(W/"tools/die_plan"),str(W/"physical/die_plan/qwen_kvsys/g3")]
import schema as S,ft_bit_sites_chan as C
p=Path(sys.argv[1]).resolve();raw=S.load(p);P=S.Plan(raw,p);tn="kv3_hgi_v8";t=raw["partition_types"][tn]
chosen={"ft4","ft17","ft26","ft27"};old=t["ft_slots"];saved=json.loads(json.dumps(old))
base_init=C.StripSites.__init__
def init(self,*args):
 base_init(self,*args)
 for s in old:
  if s["name"] in chosen:continue
  for stage in s.get("bit_sites_um",[]):
   for x,y in stage:self.used.add((round((x-self.x0)/C.F.COL_UM),round((y-self.y0)/C.F.ROW)))
C.StripSites.__init__=init
pick=C.ChanJogs.pick
def pick2(self,axis,lo,hi,n,shift):
 v={1045:285.0,553:1285.0,1057:925.0}.get(n)
 if v is None:return pick(self,axis,lo,hi,n,shift)
 assert any(a<v<b for a,b in self.iv[axis]),(axis,v,self.iv)
 return v,min(C.F.STAGGER_UM,80/max(1,n)),"explicit"
C.ChanJogs.pick=pick2
br=C.F.bit_routes
def route(a,b,fin,fout,rank,n,sgn,jog):
 if n==523 and fin=="E" and fout=="N":
  x=925+(rank-(n-1)/2)*0.096;y=1285+(rank-(n-1)/2)*0.096
  return [a,(x,a[1]),(x,y),(b[0],y),b]
 return br(a,b,fin,fout,rank,n,sgn,jog)
C.F.bit_routes=route
t["ft_slots"]=[s for s in old if s["name"] in chosen]
r=C.run(raw,P,tn,png=str(out/"review.png"))
new={s["name"]:s for s in t["ft_slots"]};t["ft_slots"]=[new.get(s["name"],s) for s in saved]
a=C.audit(raw,P,tn)
print(json.dumps({"run":r,"audit":a},default=str))
(out/"report.json").write_text(json.dumps({"run":r,"audit":a},indent=1)+"\n")
if a["over"] or a["in_core"]:raise SystemExit("FAIL reach/core")
(out/"plan.json").write_text(json.dumps(raw,indent=1)+"\n")
