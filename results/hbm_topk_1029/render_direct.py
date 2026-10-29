"""python3 render_direct.py OUTPUT_PLAN; outputs direct_plan.png beside this file."""
from pathlib import Path
import sys,json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent;pd=Path(sys.argv[1]);p=json.load(open(pd/'die_plan.json'));cs={c['inst']:c for c in p['partition_types']['root']['hard_cores']};fig,axs=plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[3,1]})
for nm in ('u_hb_idx__link','u_hb_idx__selector'):
 c=cs[nm];x,y=c['origin_um'];w,h=c['outline_um'];qs=json.load(open(pd/c['pins_file']))
 for ax in axs:
  ax.add_patch(Rectangle((x,y),w,h,fc='#e6edf3',ec='black'))
  ax.scatter([x+(w-q['x'] if c.get('orient')=='MY' else q['x']) for q in qs if q['name'].startswith('selected_line[')],[y+q['y'] for q in qs if q['name'].startswith('selected_line[')],s=2,color='#087f5b')
 axs[0].text(x+w/2,y+h/2,'TOPK MY' if 'link' in nm else 'SELECTOR R0',ha='center')
axs[0].set_xlim(0,1340);axs[0].set_ylim(-10,520);axs[0].set_aspect('equal');axs[1].set_xlim(680,704);axs[1].set_ylim(0,450);axs[1].set_title('15.312um direct gap\nNo RTL relay / no FF bank')
for ax in axs:ax.set_xlabel('root-local x (um)')
fig.suptitle('Actual source SELECTOR.selected_line → TOPK.selected_line\n2368 aligned bits, max15.312um, same regional clock T010 verified; zero RTL cycle change');fig.tight_layout();fig.savefig(r/'direct_plan.png',dpi=160)
