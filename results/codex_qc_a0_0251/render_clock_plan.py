#!/usr/bin/env python3
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan=json.loads(Path(sys.argv[1]).read_text());geom=json.loads(Path(sys.argv[2]).read_text())
fig,ax=plt.subplots(figsize=(8,14));ax.set_aspect('equal')
for m in geom['macros']:ax.add_patch(Rectangle((m[0],m[1]),m[2]-m[0],m[3]-m[1],fc='#d7dbe2',ec='#5e6879',lw=.7))
def line(pts,color,lw=1):
 x,y=zip(*pts);ax.plot(x,y,c=color,lw=lw,alpha=.8)
def tree(nd):
 for lg,k in zip(nd.get('legs',[]),nd.get('kids',[])):
  line(lg['pts'],'#187e9b' if nd.get('kind')!='icg' else '#ce6512',.6);tree(k)
line(plan['root_leg'],'#c72e39',2);tree(plan['tree'])
for c in geom['clusters']:
 x,y=c['root'];ax.plot(x,y,'o',ms=2,c='#ce6512' if c['ungated'] else '#096f57')
for s in plan['sinks']:
 if s['kind']=='child':ax.plot(*s['p'],'s',ms=4,c='#5f3495')
ax.plot(*plan['summary']['entry'],'*',ms=12,c='#c72e39')
ax.set(xlim=(0,geom['W']),ylim=(0,geom['H']),xlabel='um',ylabel='um',title='NL parent proposed clock: exact local CTS roots, DME trunk (UNBUILT)')
fig.tight_layout();fig.savefig(sys.argv[3],dpi=160)
