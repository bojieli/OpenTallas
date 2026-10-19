#!/usr/bin/env python3
import argparse,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('candidate');p.add_argument('--out',required=True);a=p.parse_args()
d=json.loads(Path(a.candidate).read_text());W,H=d['outline_um'];halo=d['halo_um'];G=d['lattice_um'];rs=d['rects'];bad=[]
for r in rs:
 for k in ('x','y'):
  if abs(r[k]/G-round(r[k]/G))>1e-6:bad.append(['lattice',r['name'],k])
 if r['x']<0 or r['y']<0 or r['x']+r['w']>W+1e-6 or r['y']+r['h']>H+1e-6:bad.append(['outside',r['name']])
for i,r in enumerate(rs):
 for s in rs[i+1:]:
  if r['x']<s['x']+s['w']+halo-1e-6 and s['x']<r['x']+r['w']+halo-1e-6 and r['y']<s['y']+s['h']+halo-1e-6 and s['y']<r['y']+r['h']+halo-1e-6:bad.append(['halo_overlap',r['name'],s['name']])
area=sum(r['w']*r['h'] for r in rs)
# Exact f4c frame dependence: 8 SM columns across,4 tiles/column;2 half-dies,4 tile rows/column.
# Reproduced from plan_p4.sm_dims/plan_f4c; retain baseline non-SM service band.
baseW,baseH=d["baseline_die_um"]
cases=[]
for tw,th in [(630.72,2203.2),(630.72,2246.4),(630.72,2289.6),(673.92,2203.2)]:
 fw=baseW+32*(tw-630.72);fh=baseH+8*(th-2203.2)
 cases.append(dict(tile_um=[tw,th],die_um=[fw,fh],die_mm2=fw*fh/1e6,reticle_fit=fw<=26000 and fh<=33000))
res=dict(status='PASS' if not bad else 'FAIL',rectangles=len(rs),baseline_children=34,new_dualclk=4,new_pad=7,outline_um=[W,H],halo_um=halo,hard_area_um2=area,hard_fill=area/(W*H),problems=bad,frame_cases=cases,scope='rectangle/lattice/halo feasibility only; not timing/pin/clock/gate qualification',att_increment_mm2=69.215,att_raw_additive_floor_mm2=cases[0]['die_mm2']+69.215,att_note='Additive area is not a packed frame. ATT432x432 and new VM475.2x280.8 need actual die-level packing; no frame-fit claim from additive area.')
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'verdict.json').write_text(json.dumps(res,indent=1)+'\n');print(json.dumps(res,indent=1),flush=True)
try:
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,ax=plt.subplots(figsize=(5,12),dpi=180)
 for r in rs:
  color='#e8ac49' if r['name'].startswith('new_dual') else '#e88484' if r['name'].startswith('new_pad') else '#7fa9d2'
  ax.add_patch(Rectangle((r['x'],r['y']),r['w'],r['h'],facecolor=color,edgecolor='black',linewidth=.4));ax.text(r['x']+r['w']/2,r['y']+r['h']/2,r['name'].split('.')[-1],ha='center',va='center',fontsize=4,clip_on=True)
 ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='um',ylabel='um',title='P3 SM:34children+4dualclock+7pad; no outline growth')
 fig.tight_layout();fig.savefig(out/'packing.png');plt.close(fig)
except ImportError:pass
raise SystemExit(bool(bad))
