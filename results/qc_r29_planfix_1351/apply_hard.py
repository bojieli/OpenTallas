"""R29 FT geometry only: keep the existing stage count whenever legal."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools/die_plan"));sys.path.insert(0,str(ROOT))
import schema as S
from gen_phys import type_pins
from ft_knee_sites import allocate_bank_chain
from tools.die_trial.legal_sites import RowAllocator
CELL=np.array([1.404,.27])
src=ROOT/"physical/die_plan/qwen_compute/die_plan.json"
raw=json.load(open(src));P=S.Plan(raw,src);ledger=[]
for tn,ty in raw["partition_types"].items():
 base=tn.split("__")[0]
 wanted=set()
 if base in ("sle_su_c","slw_su_c"):wanted|={"cws2","x_su_l1_stm"}
 if base=="slw_su_l0":wanted.add("cws3")
 if base in ("sle_su_l0","sle_su_l1"):wanted.add("x_st_a_fe")
 if not wanted:continue
 w,h=ty["outline_um"]
 pins={(b,i):np.array([x,y]) for b,i,l,x,y,f in type_pins(P,tn)}
 boxes=list(S.placed_macro_boxes(ty,halo=4.32).values())
 boxes+=list(ty.get("clock",{}).get("die_islands_um",[]))
 al=RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=boxes,cell_size=tuple(CELL),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
 for slot in ty.get("ft_slots",[]):
  for bank in slot.get("bit_sites_um",[]):
   for x,y in bank:al.reserve_rectangle((x,y,x+CELL[0],y+CELL[1]))
 for slot in ty.get("ft_slots",[]):
  if slot["name"] not in wanted:continue
  n=slot["width"]+1
  a=np.array([pins[(slot["name"]+"_i",i)] for i in range(n)])
  b=np.array([pins[(slot["name"]+"_o",i)] for i in range(n)])
  old=slot["stations"]
  if slot["name"]=="cws2":
   original=np.array(slot["bit_sites_um"])
   chosen=None
   for step in range(0,65):
    banks=original.copy();banks[0,:,1]+=.27*step
    centres=banks+CELL/2
    chain=[a,*centres,b]
    hops=[float(np.abs(y-x).sum(axis=1).max()) for x,y in zip(chain,chain[1:])]
    if max(hops+[float(np.abs(centres[0]-a.mean(axis=0)).sum(axis=1).max())])<=404.25:
     chosen=(banks,hops,step);break
   if chosen is None:raise ValueError(tn+": no legal first-bank north translation")
   banks,hops,step=chosen
   for bank in banks:
    for x,y in bank:
     if any(x<q[2] and x+CELL[0]>q[0] and y<q[3] and y+CELL[1]>q[1] for q in boxes):
      raise ValueError(tn+": translated bank intersects macro/island")
   slot["bit_sites_um"]=banks.round(6).tolist()
   slot["regs_um"]=[a.mean(axis=0).round(6).tolist(),*[(bk+CELL/2).mean(axis=0).round(6).tolist() for bk in banks]]
   note="first-bank north translation "+str(round(.27*step,6))+"um"
  else:
   if slot["name"]=="cws3" and old==4:
    # The entire W collar is macro-free. A continuous descending bank sequence
    # avoids paying an extra cycle for the generic spine's forced middle knee.
    used=set(al.used);banks=None
    for radius in (8.64,17.28,34.56):
     al.used=set(used);trial=[]
     try:
      for j,y in enumerate((1000.,630.,280.),1):
       desired=a+(b-a)*(j/4);desired[:,1]=y
       points=[]
       for xy in desired:
        point,_=al.allocate(xy,1,max_radius_um=radius);points.append(point[0])
       trial.append(np.array(points))
     except ValueError:continue
     chain=[a,*trial,b]
     candidate_hops=[float(np.abs(v-u).sum(axis=1).max()) for u,v in zip(chain,chain[1:])]
     if max(candidate_hops)<=403.:
      banks=trial;hops=candidate_hops;break
    if banks is None:raise ValueError(tn+": four-stage collar allocation failed")
   else:
    path,banks,stats,hops=allocate_bank_chain(al,a,b,slot["in_face"],slot["out_face"],old)
   slot["stations"]=len(banks)+1
   slot["regs_um"]=[a.mean(axis=0).round(6).tolist(),*[bk.mean(axis=0).round(6).tolist() for bk in banks]]
   slot["bit_site_cell_um"]=CELL.tolist()
   slot["bit_sites_um"]=[(bank-CELL/2).round(6).tolist() for bank in banks]
   note="explicit legal corridor banks" if banks else "direct per-bit reach already legal; station0 remains face capture"
  ledger.append(dict(type=tn,slot=slot["name"],old_stations=old,new_stations=slot["stations"],added_cycles=slot["stations"]-old,added_flops=(slot["stations"]-old)*n,max_hop_um=max(hops),all_hops_um=hops,note=note))
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
(out/"plan.json").write_text(json.dumps(raw,indent=0)+"\n")
(out/"ledger.json").write_text(json.dumps(ledger,indent=1)+"\n")
print(json.dumps(ledger),flush=True)
