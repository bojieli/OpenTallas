import json,csv
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
O=Path(__file__).resolve().parent;C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-repack-r3-0130/failed_collector');p=json.load(open(O/'rowfix_plan.json'));rows=json.load(open(C/'rows.json'))['rows'];cells=list(csv.DictReader(open(C/'placed.csv')))
fig,axes=plt.subplots(1,2,figsize=(15,8));lims=[(0,371.52,0,371.52),(97,163,246,296)]
for ax,(x0,x1,y0,y1) in zip(axes,lims):
 segs=[[(r['x0']/1000,r['y0']/1000),(r['x1']/1000,r['y0']/1000)] for r in rows if y0<=r['y0']/1000<=y1];ax.add_collection(LineCollection(segs,colors='#bdc9d1',linewidths=.3,alpha=.6))
 for c in cells:
  x,y,w,h=[float(c[k]) for k in ['x','y','w','h']]
  if not(x0<=x<=x1 and y0<=y<=y1):continue
  if c['kind']=='macro':ax.add_patch(Rectangle((x,y),w,h,facecolor='#7895ae',edgecolor='#143c5d',lw=1,zorder=3));ax.text(x+w/2,y+h/2,c['name'].split('.')[-1],ha='center',fontsize=6,zorder=4)
  elif ax is axes[1] and c['kind']!='pin':ax.add_patch(Rectangle((x,y),w,h,facecolor=('#a879a8' if c['kind']=='ff' else '#636b71'),alpha=.5,lw=0,zorder=2))
 for m in p['moves']:
  x,y=[v/1000 for v in m['old_ll_dbu']];nx,ny=[v/1000 for v in m['new_ll_dbu']];w,h=[v/1000 for v in m['size_dbu']]
  if x0<=x<=x1 and y0<=y<=y1:
   ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='#c93632',lw=.9,zorder=6));ax.add_patch(Rectangle((nx,ny),w,h,facecolor='#0b9d77',edgecolor='#006145',lw=.6,zorder=7));ax.annotate('',xy=(nx+w/2,ny+h/2),xytext=(x+w/2,y+h/2),arrowprops=dict(arrowstyle='->',lw=.7,color='#087953'),zorder=8)
 ax.set(xlim=(x0,x1),ylim=(y0,y1),xlabel='x (um)',ylabel='y (um)');ax.set_aspect('equal')
axes[0].set_title('Actual native cut rows and six SRAMs\n70 red invalid FFs -> green legal sites')
axes[1].set_title('Top-left SRAM detail: native row gaps are real\nOther FFs/taps fixed; combinational DPL required')
fig.suptitle('CTL row repair PREP: 70 FF moves <=3.51um; R2R391.61/0far; pin149.32max\n18,698 FFs unchanged; no RTL/cycle/clock/reset/pin change; no physical successor launched',fontsize=12)
fig.tight_layout();fig.savefig(O/'rowfix_review.png',dpi=160)
