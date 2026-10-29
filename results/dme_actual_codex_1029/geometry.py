#!/usr/bin/env python3
"""Review/check the final native clock-cell homes of an isolated DME coupon."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'die_plan'))
import die_trial as D
import schema as S
from clock_reach import actual_reach
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plan,treefile,out=sys.argv[1:];out=Path(out);out.mkdir(parents=True,exist_ok=True)
P=S.Plan(S.load(plan),Path(plan));site=D.clock_site(P)
tree=json.loads(Path(treefile).read_text());xy=tree['sites'];over=[];illegal=[];off=[]
items=list(xy.items())
for k,(name,(x,y)) in enumerate(items):
    if not site.legal((x,y)):illegal.append(name)
    if abs(x/.054-round(x/.054))>1e-5 or abs(y/.54-round(y/.54))>1e-5:off.append(name)
    for other,(a,b) in items[:k]:
        if x<a+1.62-1e-6 and x+1.62>a+1e-6 and y<b+.27-1e-6 and y+.27>b+1e-6:
            over.append([name,other])
reach=actual_reach(tree,405.)
rec=dict(verdict='PASS' if not(over or illegal or off) and reach['verdict']=='PASS' else 'FAIL',
         cells=len(xy),body_overlap_count=len(over),body_overlaps=over,illegal_body_homes=illegal,
         off_r0_grid=off,actual_reach=reach)
(out/'body_geometry.json').write_text(json.dumps(rec,indent=1)+'\n')
fig,ax=plt.subplots(figsize=(14,9))
xs=[p[0] for p in xy.values()];ys=[p[1] for p in xy.values()]
x0,x1=min(xs)-60,max(xs)+60;y0,y1=min(ys)-60,max(ys)+60
for a,b,c,d,*_ in D.SiteMap(P).forb:
    if a<x1 and c>x0 and b<y1 and d>y0:ax.add_patch(Rectangle((a,b),c-a,d-b,color='gray',alpha=.28))
for child,parent in tree['parent_of'].items():
    a,b=xy[parent],xy[child];ax.plot([a[0],b[0]],[a[1],b[1]],color='#3b82b6',lw=.55,alpha=.6)
ax.scatter(xs,ys,s=8,c='#125d92',label='native frozen clock cells')
tx=[t['xy'][0] for t in tree['taps']];ty=[t['xy'][1] for t in tree['taps']]
ax.scatter(tx,ty,s=22,c='#d64232',marker='x',label='tap pins')
ax.set(xlim=(x0,x1),ylim=(y0,y1),xlabel='die x (um)',ylabel='die y (um)',
       title=f"Native isolated clock coupon: {len(xy)} cells / {len(tx)} taps; geometry {rec['verdict']}")
ax.set_aspect('equal');ax.legend(loc='upper right');fig.tight_layout();fig.savefig(out/'body_clock.png',dpi=180)
print(json.dumps({k:v for k,v in rec.items() if k!='actual_reach'}))
raise SystemExit(0 if rec['verdict']=='PASS' else 1)
