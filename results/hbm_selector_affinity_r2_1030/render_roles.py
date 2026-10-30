#!/usr/bin/env python3
import sys,json,runpy,re
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
K,O=map(Path,sys.argv[1:3]);sys.argv=[sys.argv[0],str(K),str(O/'render_ingest')]
v=runpy.run_path(str(Path(__file__).with_name('ingest_estimate.py')))
g=json.load(open(O/'groups.json'));claims=json.load(open(O/'claims.json'));summary=json.load(open(O/'summary.json'))
regions=json.load(open(O/'regions.json')) if (O/'regions.json').exists() else {n:[b] for n,b in g.items()}
fig,ax=plt.subplots(figsize=(12,9));ax.add_patch(Rectangle((0,0),600.048,450.36,fill=False,lw=2))
for (q,m),b in v['macros'].items():
 ax.add_patch(Rectangle((b['x'],b['y']),v['w'],v['h'],color='gray',alpha=.4));ax.text(b['x']+v['w']/2,b['y']+v['h']/2,f'q{q}m{m} {b["orient"]}',ha='center',fontsize=8)
for b in {tuple(c['rect_um']) for c in json.load(open(K/'core_infra_plan.json'))['cells']}:
 ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],color='purple',alpha=.5))
colors=['royalblue','green','orange','crimson']
for q,c in enumerate(colors):
 a,b,d,e=g[f'q{q}'];ax.add_patch(Rectangle((a,b),d-a,e-b,fill=False,color=c,lw=2));ax.text((a+d)/2,(b+e)/2,f'q{q} FF',rotation=90,color=c,ha='center',fontsize=8)
 for a,b,d,e in regions[f'q{q}']:ax.add_patch(Rectangle((a,b),d-a,e-b,color=c,alpha=.15))
for a,b,d,e in regions['root']:ax.add_patch(Rectangle((a,b),d-a,e-b,color='red',alpha=.15))
for q in range(4):
 a,b,d,e=g[f'threshold{q}'];ax.add_patch(Rectangle((a,b),d-a,e-b,color='purple',alpha=.35))
ax.text(300,225,'root',ha='center',fontsize=7)
for r in claims:
 x,y=r['point']
 if r['kind'] in ('quarter_control','reset_global','reset_quarter'):ax.plot(x,y,'.',color='black',ms=3)
 else:ax.plot(x,y,'.',color='steelblue',ms=.6,alpha=.18)
worst=max((r for r in claims if r['kind']=='quarter_control'),key=lambda r:r['box_leg_bound_um']);q=int(worst['register'].split('[')[1].split(']')[0]);field,bit=re.search(r'\.(op|pass|addr)_q\[(\d+)\]',worst['register']).groups();p=v['pins'][f'{field}[{bit}]'];x,y=worst['point'];ends=[(a,b) for a,b,c,d in regions[f'q{q}'] for a,b in [(a,b),(a,d),(c,b),(c,d)]];tx,ty=max(ends,key=lambda t:abs(t[0]-x)+abs(t[1]-y));ax.plot([p['x'],x,tx],[p['y'],y,ty],'k--',lw=1,label='representative local-control relay')
ax.set(xlim=(-15,615),ylim=(-15,465),aspect='equal',xlabel='um',ylabel='um',title='Selector revised placement roles: existing FFs, 0 added cycles\n12 fixed SRAMs, central histogram/quarter state, separate control/input/output relays')
ax.text(0,-38,f'MODEL ONLY: max station-box bound {summary["max_station_box_leg_bound_um"]:.2f} um; macro RD→quarter FF {summary["macro_rd_to_any_quarter_ff_bound_um"]:.2f} um\nActual mapped FF identity, capacity, face offsets, full geometry and timing remain required.',fontsize=9)
fig.tight_layout();fig.savefig(O/'selector_roles_r2.png',dpi=150)
