from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parent;fig,axs=plt.subplots(1,2,figsize=(12,7))
for ax,n in zip(axs,['recip','zh']):
 f=next((R/n).glob('*.lef'));d=json.loads((R/n/'selected_pin_shapes.json').read_text());W,H=d['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False))
 for name,p in d['signal_pins'].items():
  for sh in p['rects']:
   x,y,xx,yy=sh['rect_um'];ax.add_patch(Rectangle((x,y),xx-x,yy-y,fill=False,edgecolor='#38679a' if p['direction']=='INPUT' else '#cc853c'));ax.scatter((x+xx)/2,(y+yy)/2,s=4,color='#38679a' if p['direction']=='INPUT' else '#cc853c')
  if name in ('clk','rst_n','x[31]'):
   a=p['rects'][0]['rect_um'];ax.annotate(name,((a[0]+a[2])/2,(a[1]+a[3])/2),xytext=(5,5),textcoords='offset points',fontsize=8)
 ax.set_title(f"Actually selected {n.upper()}: {W:g}×{H:g} / {len(d['signal_pins'])} signal bits");ax.set_aspect('equal');ax.set_xlim(-5,W+5);ax.set_ylim(-5,H+5);ax.grid(alpha=.2);ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('Exact published old AHUB-selected pin geometry — source inspection only\nNo compact RECIP/Q6 ZH pin spread substituted; no native clock graph or new physical result',fontsize=11);fig.tight_layout();fig.savefig(R/'selected_old_pin_geometry.png',dpi=150)
