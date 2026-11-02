import csv,json,math
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
O=Path(__file__).resolve().parent;C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector');m=json.load(open(O/'actual_geom.json'))['metrics'];cells=list(csv.DictReader(open(C/'placed.csv')))
fig,axes=plt.subplots(1,2,figsize=(15,8));axes[0].set_title('Actual final DPL: FFs pink, combinational cells gray\nSix fixed SRAMs blue; public pins orange')
for kind,color,size in [('std','#888c95',.4),('buf','#888c95',.4),('ff','#a12273',1.2),('pin','#f08c00',1)]:
 p=[q for q in cells if q['kind']==kind];axes[0].scatter([float(q['x'])+float(q['w'])/2 for q in p],[float(q['y'])+float(q['h'])/2 for q in p],s=size,c=color,alpha=.5,rasterized=True,zorder=2)
bins=math.ceil(371.52/10.8);heat=np.zeros((bins,bins))
for c in cells:
 x,y,w,h=[float(c[k]) for k in ['x','y','w','h']]
 if c['kind'] not in ['macro','pin','tap']:heat[min(bins-1,int((y+h/2)/10.8)),min(bins-1,int((x+w/2)/10.8))]+=w*h/(10.8**2)
 if c['kind']=='macro':
  for ax in axes:ax.add_patch(Rectangle((x,y),w,h,facecolor='#7895ae',edgecolor='#143c5d',lw=1,zorder=4));ax.text(x+w/2,y+h/2,c['name'].split('.')[-1],ha='center',fontsize=6,zorder=5)
 if c['kind']=='pin' and c['name'] in ['clk','rst_n','por_n']:
  axes[0].plot(x,y,'*',c='#e3362c',ms=10,zorder=8);axes[0].annotate(c['name'],(x,y),xytext=(8,8),textcoords='offset points',fontsize=8,zorder=8)
im=axes[1].imshow(heat,origin='lower',extent=[0,bins*10.8,0,bins*10.8],vmin=0,vmax=.6,cmap='YlOrRd',interpolation='nearest',zorder=0);fig.colorbar(im,ax=axes[1],fraction=.04,pad=.02,label='standard-cell area / bin area')
axes[1].set_title('Actual cell spread: center-assigned 10.8um bins\nLarge unused regions remain a design blocker')
for ax in axes:ax.set(xlim=(0,371.52),ylim=(0,371.52),xlabel='x (um)',ylabel='y (um)');ax.set_aspect('equal')
fig.suptitle('CTL actual final DPL: 18,768 FFs; native row violations 0; R2R391.61/0far; pins15.92p90/149.32max\nHOLD: fill0.0896, empty0.7621, channels H0.742/V0.677, column0.704; no CTS/GRT',fontsize=12)
fig.tight_layout();fig.savefig(O/'actual_dpl_review.png',dpi=160)
