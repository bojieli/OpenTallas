"""Explicit soft-FT bank plan; preserve stage count before adding a priced edge."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools/die_plan"));sys.path.insert(0,str(ROOT))
import schema as S
from gen_phys import type_pins
from ft_knee_sites import allocate_bank_chain
from tools.die_trial.legal_sites import RowAllocator
CELL=np.array([1.404,.27])
raw=json.load(open(ROOT/"physical/die_plan/qwen_compute/die_plan.json"));P=S.Plan(raw);ledger=[]
for tn in ("coll_ftc","coll_ftn"):
 ty=raw["partition_types"][tn];w,h=ty["outline_um"]
 pins={(b,i):np.array([x,y]) for b,i,l,x,y,f in type_pins(P,tn)}
 al=RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=ty.get("clock",{}).get("die_islands_um",[]),cell_size=tuple(CELL),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
 for slot in sorted(ty["ft_slots"],key=lambda x:-x["width"]):
  n=slot["width"]+1;a=np.array([pins[(slot["name"]+"_i",i)]for i in range(n)]);b=np.array([pins[(slot["name"]+"_o",i)]for i in range(n)])
  old=slot["stations"];used=set(al.used);banks=None
  # Soft-only footprint has no macro walls. Distributed turn waypoints give
  # each bit a short Manhattan hop without requiring a bank at every knee.
  for radius in (8.64,17.28,34.56):
   al.used=set(used);trial=[]
   try:
    for j in range(1,old):
     desired=a+(b-a)*(j/old);points=[]
     for xy in desired:
      point,_=al.allocate(xy,1,max_radius_um=radius);points.append(point[0])
     trial.append(np.array(points))
   except ValueError:continue
   chain=[a,*trial,b]
   hops=[float(np.abs(v-u).sum(axis=1).max())for u,v in zip(chain,chain[1:])]
   if max(hops)<=403.:
    banks=trial;method="distributed rectilinear waypoints";break
  if banks is None:
   al.used=set(used)
   path,banks,stats,hops=allocate_bank_chain(al,a,b,slot["in_face"],slot["out_face"],old)
   method="shared knee"
  slot["stations"]=len(banks)+1
  slot["regs_um"]=[a.mean(axis=0).round(6).tolist(),*[bk.mean(axis=0).round(6).tolist()for bk in banks]]
  slot["bit_site_cell_um"]=CELL.tolist()
  slot["bit_sites_um"]=[(bk-CELL/2).round(6).tolist()for bk in banks]
  ledger.append(dict(type=tn,slot=slot["name"],old_stations=old,new_stations=slot["stations"],added_cycles=slot["stations"]-old,added_flops=(slot["stations"]-old)*n,max_hop_um=max(hops),all_hops_um=hops,method=method))
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
(out/"plan.json").write_text(json.dumps(raw,indent=0)+"\n")
(out/"ledger.json").write_text(json.dumps(ledger,indent=1)+"\n")
print(json.dumps(dict(slots=len(ledger),added_flops=sum(r["added_flops"]for r in ledger),added_cycles=sum(r["added_cycles"]for r in ledger),max_hop=max(r["max_hop_um"]for r in ledger),changed=[r for r in ledger if r["added_cycles"]])),flush=True)
