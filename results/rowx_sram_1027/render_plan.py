import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2]
R=Path(__file__).parent
rec=json.loads((R/'recipes.json').read_text())['dsdv_rowx_xm_sram']
spec=json.loads((ROOT/'physical/ref_tile/dsdv_rowx_xm_sram/spec.json').read_text())
W,H=spec['outline_um'];fig,ax=plt.subplots(figsize=(8,10))
for master,sites in rec['macro_sites'].items():
 d=json.loads((ROOT/'physical/asap7_memory_macros'/master/(master+'.json')).read_text());w,h=d['area']['macro_width_um'],d['area']['macro_height_um']
 for j,(x,y,o) in enumerate(sites):
  ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,facecolor='#dddddd',edgecolor='none'))
  ax.add_patch(Rectangle((x,y),w,h,facecolor='#a8cde8' if '64x512' in master else '#b7dfc4',edgecolor='#264157'))
  label=['RP A0','RP A1','RP B'][j] if '64x512' in master else ['BC high','BC low','RED high','RED low'][j]
  ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=11)
  ax.plot([x,x],[y+6,y+h-6],color='#6b3780',lw=2)
x,y=spec['clock_entry_um'];ax.add_patch(Rectangle((x-4.32,y-4.32),8.64,8.64,facecolor='#e6af34',edgecolor='black'));ax.annotate('centre clock entry',(x,y),(x-105,y+20),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.text(W/2,H-20,'RO + BI: north neighbour',ha='center',fontsize=10)
ax.text(W/2,17,'RI + BO: south neighbour',ha='center',fontsize=10)
ax.text(16,H/2,'local export + egress',rotation=90,ha='center',va='center',fontsize=9)
ax.text(W-15,H/2,'48um edge corridor',rotation=90,ha='center',va='center',fontsize=9)
ax.set(xlim=(0,W),ylim=(0,H),xlabel='um',ylabel='um',aspect='equal',title='ROWX native SRAM standalone recipe\nPLAN FORM ONLY: current svc5/svc11 lot FAIL')
fig.tight_layout();fig.savefig(R/'render/macro_plan.png',dpi=160)
report=dict(verdict='PASS-COND PLAN FORM ONLY',outline_um=[W,H],macro_count=7,macro_halo_um=4.32,channel_min_um=48,
 usable_channel_after_halos_um=39.36,assumed_derated_horizontal_tracks_per_um=35,
 worst_RP_W_dynamic_pins=793,channel_util_est=793/(39.36*35),
 conditions=['Actual parent lot FAIL: no build until S81 plan owner reserves a legal dedicated/repacked lot.','Complete pin/FF placement, reach census, PG and clock-tree plan are still needed before physical trial.','No routed timing or signoff claim.'])
(R/'recipe_geom_review.json').write_text(json.dumps(report,indent=2)+'\n')
