import json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path('/srv/opentallas-scratch/claude/wt/codex-qc-kits-2249/results/qc_codex_kits_2249');j=json.load((R/'macro_plan.json').open());report=json.load((R/'macro_site_report.json').open())
ns=['sle_st_a_v2','sle_st_b_v1','coll_s','coll_n','coll_core','glue','tt_ctlm','sle_stm_v1__cl27746664']
fig,axes=plt.subplots(2,4,figsize=(19,13))
for ax,n in zip(axes.flat,ns):
 t=j['partition_types'][n];w,h=t['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fill=False,color='black',lw=1))
 for b in t['clock'].get('landing_contract',{}).get('bands',{}).values():
  a,c,d,e=b['rect_um'];ax.add_patch(Rectangle((a,c),d-a,e-c,color='#888888',alpha=.5))
 for q in t.get('hard_cores',[]):
  if not q.get('note','').startswith('Exact existing native'):continue
  x,y=q['origin_um'];a,b=q['outline_um'];halo=q['halo_um'];ax.add_patch(Rectangle((x-halo,y-halo),a+2*halo,b+2*halo,fc='#ffd78a',alpha=.8));ax.add_patch(Rectangle((x,y),a,b,fc='#416da1',alpha=.8))
  lbl=q['inst'].replace('u_bound.','').split('.')[-2:];ax.text(x+a/2,y+b/2,'.'.join(lbl),ha='center',va='center',fontsize=4,clip_on=True)
 for q in t['clock'].get('taps',[]):
  if 'xy'in q:ax.plot(*q['xy'],'go',ms=3)
 if t['clock'].get('tap_um'):ax.plot(*t['clock']['tap_um'],'rx',ms=5)
 ax.set_xlim(-5,w+5);ax.set_ylim(-5,h+5);ax.set_aspect('equal');ax.set_title(n+'\n'+str(report[n]['macros'])+' actual macros, '+str(round(100*report[n]['fraction'],1))+'% area',fontsize=8);ax.tick_params(labelsize=6)
fig.suptitle('QC physical-only native memory sites: blue SRAM/ROM, orange4.32um halo, grey existinglandingbands, green clocktaps',fontsize=13);fig.tight_layout(rect=(0,0,1,.96));fig.savefig('/tmp/qc-macro-sites-review.png',dpi=180)
