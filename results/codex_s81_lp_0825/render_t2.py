#!/usr/bin/env python3
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parent
s=json.loads((R/'t2/spec.json').read_text())
pins=json.loads((R/'t2/plan_pins.json').read_text())['pins']
parents=json.loads((R/'t2/parent_receipt.json').read_text())
fig,axs=plt.subplots(1,2,figsize=(15,8))
a=axs[0];w=s['outline']['w'];h=s['outline']['h']
a.add_patch(Rectangle((0,0),w,h,fill=False))
for m in s['macros']:
    small='32x64' in m['view'];mw,mh=(31.992,17.304) if small else (34.584,41.352)
    a.add_patch(Rectangle(m['at'],mw,mh,color='lightgrey',ec='black',lw=.3))
    a.add_patch(Rectangle((m['at'][0]-4.32,m['at'][1]-4.32),mw+8.64,mh+8.64,fill=False,ec='tab:orange',lw=.3))
a.scatter([p['x'] for p in pins if p['name']!='ck[0]'],[p['y'] for p in pins if p['name']!='ck[0]'],s=.3,color='black')
c=next(p for p in pins if p['name']=='ck[0]');a.scatter(c['x'],c['y'],s=120,marker='*',color='red')
a.set(xlim=(-5,w+5),ylim=(-5,h+8),aspect='equal',title='T2 candidate: same 55 SRAM lattice, cropped N band\n295.92 x 444.96; orange=4.32 halo; red=clock entry')
b=axs[1];p=parents['s_0N_LP'];b.add_patch(Rectangle((0,0),1442.88,1226.88,fill=False))
for k,box in enumerate(p['lane_boxes']):
    x,y,x1,y1=box;b.add_patch(Rectangle((x,y),x1-x,y1-y,color='lightgrey',ec='black'));b.text((x+x1)/2,(y+y1)/2,f'lane {k}\nMX',ha='center')
x0,x1=p['other_window_street'];b.add_patch(Rectangle((x0,700),x1-x0,526.88,color='tab:blue',alpha=.15));b.text((x0+x1)/2,800,'other\nface\nwindows',ha='center')
b.set(xlim=(-10,1455),ylim=(-10,1240),aspect='equal',title='s_0N_LP parent cut proposal\n4 children + uninterrupted window street; parent std cells ~284k')
for a in axs:a.set_xlabel('um');a.set_ylabel('um')
fig.tight_layout();fig.savefig(R/'t2_candidate.png',dpi=160)
