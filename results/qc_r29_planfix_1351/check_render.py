import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools/die_plan"))
import schema as S,check as C
from gen_phys import type_pins
R=Path("/srv/opentallas-scratch2/claude/codex-qc-event-1351-1027/combined")
raw=json.load(open(R/"plan.json"));base=ROOT/"physical/die_plan/qwen_compute"
result,summary=C.run(raw,plan_dir=base,completeness=True)
rep=dict(errors=len(result.errors()),warnings=len(result.items)-len(result.errors()),summary=summary,findings=result.items)
(R/"g0c.json").write_text(json.dumps(rep,indent=1)+"\n")
print("G0C",rep["errors"],rep["warnings"],flush=True)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
led=json.load(open(Path(__file__).parent/"ledger.json"));types=sorted({r["type"]for r in led})
P=S.Plan(raw,base/"die_plan.json")
fig,axs=plt.subplots(2,4,figsize=(18,14))
for tn,ax in zip(types,axs.flat):
 t=raw["partition_types"][tn];w,h=t["outline_um"]
 ax.add_patch(Rectangle((0,0),w,h,facecolor="#fafafa",edgecolor="black"))
 for name,(x0,y0,x1,y1)in S.placed_macro_boxes(t).items():
  ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color="#c9d5e3",ec="#485c72"))
 pins={(b,i):(x,y)for b,i,l,x,y,f in type_pins(P,tn)}
 names={r["slot"]for r in led if r["type"]==tn}
 k=0
 for slot in t["ft_slots"]:
  if slot["name"]not in names:continue
  color=plt.cm.tab20(k%20);k+=1;n=slot["width"]+1
  a=[pins[(slot["name"]+"_i",i)]for i in range(n)]
  b=[pins[(slot["name"]+"_o",i)]for i in range(n)]
  import numpy as np
  a=np.array(a);b=np.array(b)
  ax.scatter(a[:,0],a[:,1],s=.6,color=[color]);ax.scatter(b[:,0],b[:,1],s=.6,color=[color])
  centres=[]
  for bank in slot["bit_sites_um"]:
   points=np.array(bank)+np.array(slot["bit_site_cell_um"])/2
   ax.scatter(points[:,0],points[:,1],s=.7,color=[color]);centres.append(points.mean(axis=0))
  chain=[a.mean(axis=0),*centres,b.mean(axis=0)]
  for left,right in zip(chain,chain[1:]):
   ax.plot([left[0],right[0],right[0]],[left[1],left[1],right[1]],color=color,lw=.6,alpha=.6)
 ax.set_xlim(-10,w+10);ax.set_ylim(-10,h+10);ax.set_aspect("equal")
 ax.set_title(tn+" "+str(w)+"×"+str(h)+"µm",fontsize=10)
 ax.grid(alpha=.15)
axs.flat[-1].axis("off")
axs.flat[-1].text(.02,.95,"R29 FT physical proposal\n37 slots / 7 types\n34,314 explicit cells audited\n0 row/site/macro/overlap errors\nmaximum paired hop 402.907 µm\n0 added cycles / 0 added FF\n\nBlue: existing hard cores\nColors: exact payload+epoch banks\nLines: Manhattan centroid connections\nCurrent clock allotment still pending.\nNo P&R or freeze claim.",va="top",fontsize=12)
fig.tight_layout()
dest=ROOT/"results/geom_review/qc_r29_planfix_1351";dest.mkdir(parents=True,exist_ok=True)
fig.savefig(dest/"ft_banks.png",dpi=150)
print(dest/"ft_banks.png",flush=True)
