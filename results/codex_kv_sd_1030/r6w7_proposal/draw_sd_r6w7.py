import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
r=Path(__file__).resolve().parent;p=json.load(open(r/'plan_of_record/plan_c_sd_r6w7_candidate.json'))
t=p['partition_types']['kv3_sys_SD'];ck=t['clock'];lc=ck['landing_contract']
fig,axes=plt.subplots(1,2,figsize=(17,10),gridspec_kw={'width_ratios':[1.6,1]})
for ax in axes:
 ax.add_patch(Rectangle((17.28,54),1848.96,972,facecolor='#d8d8d8',edgecolor='black',label='Actual PHY bbox'))
 ax.add_patch(Rectangle((1866.24,54),4.32,972,facecolor='#ffcf92',edgecolor='brown',label='PHY PG margin'))
 for b,v in lc['bands'].items():
  x,y,X,Y=v['rect_um'];ax.add_patch(Rectangle((x,y),X-x,Y-y,fill=True,alpha=.4,facecolor='green',edgecolor='green',label=b+' FF bank'))
 for n in lc['collector_tree']['relays']:
  ax.plot(*n['xy'],marker='.',color='purple',ms=4)
 for kind,color in [('landing_reader_start','blue'),('landing_writer_start','red')]:
  for b,v in ck[kind]['branches'].items():
   xy=[[190.56,21.6]]+[s['xy_um'] for s in v['stages']]
   ax.plot([q[0] for q in xy],[q[1] for q in xy],color=color,lw=1,marker='o',ms=3,label=kind.split('_')[1]+' '+b)
 for v in ck['taps']:
  ax.plot(*v['xy'],marker='*',color='black',ms=10);ax.annotate(v['name'],v['xy'],fontsize=8)
 for n in ck['landing_local_resets']:ax.plot(*n['xy_um'],marker='s',color='orange',ms=5)
 ax.set_ylim(0,1040);ax.grid(alpha=.2);ax.set_xlabel('x / um');ax.set_ylabel('y / um')
axes[0].set_xlim(0,1900.8);axes[0].set_aspect('equal')
axes[1].set_xlim(1860,1901);axes[1].set_title('E corridor (x enlarged)')
axes[0].set_title('SD R6/W7 + old 5S / new 2E taps\nPROPOSAL ONLY: no density/placement/PG continuity qualification')
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=8)
fig.tight_layout(rect=(0,.08,1,1));fig.savefig(r/'sd_r6w7_candidate.png',dpi=160)
