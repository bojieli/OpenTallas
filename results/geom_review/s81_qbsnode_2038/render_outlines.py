import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path('/srv/opentallas-scratch/claude/codex-s81-qbsnode-2038/gen2')
fig,axs=plt.subplots(1,3,figsize=(12,7))
for ax,mod in zip(axs,['dsfd_node_LLfu','dsfd_node_LLfd','dsfd_node_NNfu']):
 k=root/(mod+'_c');p=json.load(open(k/'pins.json'))
 cfg=(k/'config.mk').read_text(); line=next(x for x in cfg.splitlines() if x.startswith('export DIE_AREA')); _,_,w,h=map(float,line.split('=')[1].split())
 ax.add_patch(Rectangle((0,0),w,h,fill=False,ec='black'));ax.add_patch(Rectangle((4.32,4.32),w-8.64,h-8.64,fill=False,ec='gray',ls='--'))
 for bus in sorted({x['bus'] for x in p}):
  b=[x for x in p if x['bus']==bus];ax.scatter([x['x'] for x in b],[x['y'] for x in b],s=11,label=f'{bus} ({len(b)})')
 ax.set_aspect('equal');ax.set_xlim(-6,w+6);ax.set_ylim(-5,h+5);ax.set_title(mod+'\n'+f'{w} x {h} um, {len(p)} pins');ax.legend(fontsize=8,loc='center');ax.set_xlabel('um')
fig.suptitle('QBS node reconstruction — exact current plan outline/pins, no macros\npre-placement review only; cell density/reach/clock balance await actual PLACE')
fig.tight_layout();fig.savefig(root.parent/'node_outlines.png',dpi=150)
