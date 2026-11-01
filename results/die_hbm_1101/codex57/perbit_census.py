import sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1101/tools/die_plan")
import schema as S
from gen_phys import type_pins
raw=json.load(open(sys.argv[1]));p=S.Plan(raw,None);out=[]
for tn,t in p.types.items():
 ss=[s for s in t.get("ft_slots",[]) if s.get("bit_sites_um")]
 if not ss:continue
 pins={(b,i):(x,y) for b,i,l,x,y,f in type_pins(p,tn)}
 for s in ss:
  n=s["width"]+1;A=np.array([pins[(s["name"]+"_i",i)] for i in range(n)]);B=np.array([pins[(s["name"]+"_o",i)] for i in range(n)]);half=np.array(s["bit_site_cell_um"])/2
  stages=[A]+[np.array(q)+half for q in s["bit_sites_um"]]+[B]
  hops=[abs(b-a).sum(axis=1) for a,b in zip(stages,stages[1:])]
  mx=[float(x.max()) for x in hops];bad=sum(int((x>405+1e-6).sum()) for x in hops)
  if bad:out.append(dict(type=tn,slot=s["name"],stations=s["stations"],width=s["width"],max_hops_um=mx,bad_bit_hops=bad))
json.dump(out,open(sys.argv[2],"w"),indent=2)
for x in out:print(x)
print("badslots",len(out),"badhops",sum(x["bad_bit_hops"] for x in out))
