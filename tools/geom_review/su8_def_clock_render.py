#!/usr/bin/env python3
"""Read-only final DEF origin density and named CTS-cell overlay, no timing inference."""
import argparse,json,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=argparse.ArgumentParser();p.add_argument('--def',dest='deffile',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();s=a.deffile.read_text();a.out.mkdir(parents=True,exist_ok=True)
u=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',s)[1]);die=list(map(int,re.search(r'DIEAREA\s*\(\s*(\d+)\s+(\d+)\s*\)\s*\(\s*(\d+)\s+(\d+)\s*\)',s).groups()));die=[v/u for v in die]
section=re.search(r'COMPONENTS\s+(\d+)\s*;(.*?)END COMPONENTS',s,re.S);rows=[]
for m in re.finditer(r'-\s+(\S+)\s+(\S+)(.*?)\s*;',section[2],re.S):
 n,master,b=m.groups();xy=re.search(r'\+\s+(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)',b)
 if xy:rows.append(dict(name=n,master=master,x=int(xy[1])/u,y=int(xy[2])/u))
assert len(rows)==int(section[1])
filler=[r for r in rows if r['name'].startswith('FILLER') or 'DECAP' in r['master']];active=[r for r in rows if not (r['name'].startswith('FILLER') or 'DECAP' in r['master'])];clocks=[r for r in rows if re.search(r'^(clkbuf|clkload|clockbuf)',r['name'])];ff=[r for r in active if re.search('DFF|SDFF',r['master'])]
fig,axes=plt.subplots(1,2,figsize=(14,6))
for ax in axes:ax.add_patch(Rectangle((die[0],die[1]),die[2]-die[0],die[3]-die[1],fill=False,color='black'));ax.set_xlim(-2,die[2]+2);ax.set_ylim(-2,die[3]+2);ax.set_aspect('equal');ax.set_xlabel('µm');ax.set_ylabel('µm')
axes[0].hist2d([r['x'] for r in active],[r['y'] for r in active],bins=[87,65],range=[[0,172.8],[0,129.6]],cmap='Blues');axes[0].set_title('Actual final DEF active component origin counts\n(excludes named fillers/DECAP; not cell-area utilization)')
axes[1].scatter([r['x'] for r in ff],[r['y'] for r in ff],s=.4,c='#7398bb',alpha=.3,label=f'FF origins ({len(ff)})');axes[1].scatter([r['x'] for r in clocks],[r['y'] for r in clocks],s=9,c='#c54b36',label=f'named CTS cell origins ({len(clocks)})');axes[1].legend(fontsize=8);axes[1].set_title('Actual retained placement, named CTS overlay\nNo clock graph, arrival or skew inferred')
fig.suptitle('Retained SU8 rst3 final fixture172.8×129.6µm — read-only TT/FF clock coupon only');fig.tight_layout();fig.savefig(a.out/'final_def_clock.png',dpi=150)
dictout=dict(schema='opentallas.su8.final_def_placement.v1',source=str(a.deffile),dbu=u,outline=die,components=len(rows),filler_decap=len(filler),active_components=len(active),ff_master_origins=len(ff),named_cts_cells=len(clocks),clock_cells=clocks,scope='read-only TT/FF clock coupon; no gate expansion/80ps waiver/legacy SIGNOFF claim')
(a.out/'placement.json').write_text(json.dumps(dictout,indent=2)+'\n');print(json.dumps({k:v for k,v in dictout.items() if k!='clock_cells'},indent=2))
