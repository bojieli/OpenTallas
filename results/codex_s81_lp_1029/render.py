#!/usr/bin/env python3
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path(__file__).resolve().parent;p=json.load(open(b/'pins.json')); e=json.load(open(b/'estimate.json'))
f,a=plt.subplots(figsize=(10,8));W,H=p['outline_um'];a.set_xlim(-8,W+8);a.set_ylim(-8,H+8);a.set_aspect('equal');a.add_patch(Rectangle((0,0),W,H,fill=False,lw=2))
for j,m in enumerate(json.load(open(b/'spec.json'))['macros']):
 x,y=m['at'];a.add_patch(Rectangle((x-4.32,y-4.32),94.824+8.64,41.064+8.64,fill=False,ls=':',ec='orange'));a.add_patch(Rectangle((x,y),94.824,41.064,fc='.8',ec='black'));a.text(x+47.4,y+20.5,f'SRAM bank {j}',ha='center')
for name,col in [('wd','blue'),('rd','green'),('rc','purple')]:
 z=[v for v in p['pins'] if v['name'].split('[')[0]==name];a.scatter([v['x'] for v in z],[v['y'] for v in z],s=2,c=col,label=name)
a.scatter(*[[v] for v in e['clock_entry_um']],s=180,marker='*',c='red',label='centre clock');a.set_title(f'LP compact source candidate | {W} x {H} um\n{e["macro_area_pct"]:.2f}% macros; bank-local faces, 4.32 um halos; PLACE census only');a.legend(loc='upper right');f.savefig(b/'compact_plan.png',dpi=150,bbox_inches='tight')
