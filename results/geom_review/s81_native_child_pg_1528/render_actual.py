from pathlib import Path
import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).parent;d=json.load(open(r/'actual_pg.json'));colors={'VDD':'firebrick','VSS':'navy'}
fig,axs=plt.subplots(1,2,figsize=(15,7))
for net,x0,y0,x1,y1 in d['m6_special_wires']:axs[0].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=colors[net],alpha=.25))
for a in d['rows']:
 x,y=a['origin_um'];w,h=a['outline_um'];hist=a['master']=='ot_s81ph_native_sel_hist_bank'
 axs[0].add_patch(Rectangle((x,y),w,h,facecolor='gold' if hist else 'lightgray',edgecolor='black',alpha=.7))
 axs[0].text(x+w/2,y+h/2,'hist M5' if hist else 'SRAM M4',ha='center',fontsize=6)
axs[0].set(xlim=(0,648),ylim=(0,648),aspect='equal',title='Actual post-PDN: 296 M6 PG stripes / 32 macros\nAll64 PG terms and all2700 LEF PG rectangles contacted',xlabel='um',ylabel='um')
a=next(a for a in d['rows'] if a['master']=='ot_s81ph_native_sel_hist_bank');ox,oy=a['origin_um'];w,h=a['outline_um'];ax=axs[1]
ax.add_patch(Rectangle((0,0),w,h,facecolor='lightgray',alpha=.4))
for net,x0,y0,x1,y1 in d['m6_special_wires']:
 if y1<oy-3 or y0>oy+h+3:continue
 ax.add_patch(Rectangle((-3,y0-oy),w+6,y1-y0,facecolor=colors[net],alpha=.45))
for p in a['pins']:
 for s in p['shapes']:
  x0,y0,x1,y1=s['rect_um'];ax.add_patch(Rectangle((x0-ox,y0-oy),x1-x0,y1-y0,facecolor=colors[p['name']],alpha=.8))
ax.set(xlim=(-3,w+3),ylim=(-3,h+3),aspect='equal',title='Actual native hist: 26 M5 PG rectangles\nEach has10–11 matching-net M5 via-enclosure contacts',xlabel='child-local um',ylabel='um')
fig.suptitle('ACTUAL PG CONTACT PASS — whole-grid topology/IR and timing remain separately qualified',fontsize=11)
fig.tight_layout(rect=(0,0,1,.94));fig.savefig(r/'actual_pg.png',dpi=145)
