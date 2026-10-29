import sys,json
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot')
import geom_rules as g
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D=g.Design(sys.argv[1]);fig,ax=plt.subplots(figsize=(7,14));ax.set_aspect('equal')
for c in D.cells.values():
 if c[0]=='M':ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc='#d7dbe2',ec='#66758a'))
ck=next(p for p in D.pins if p['name']=='ck');todo=[D.pin_net[ck['k']]];seen=set()
def pt(r):
 if r[0]=='p':p=D.pin_by_k[r[1]];return p['x'],p['y']
 return g.ctr(D.cells[r[1]])
while todo:
 n=todo.pop()
 if n in seen:continue
 seen.add(n);sig,dr,sk=D.nets[n]
 if not dr:continue
 for r in sk:
  if r[0]!='i' or r[1] not in D.cells:continue
  c=D.cells[r[1]]
  if c[0] in 'BK':
   a,b=pt(dr),pt(r);isdelay='delaybuf_' in c[6]
   ax.plot([a[0],b[0]],[a[1],b[1]],c='#d94242' if isdelay else '#278ba3',lw=.8 if isdelay else .4,alpha=.9)
   ax.scatter(*b,s=6 if isdelay else 2,c='#d94242' if isdelay else '#00866b')
   todo.extend(D.drives[r[1]])
ax.scatter(ck['x'],ck['y'],c='#c52535',s=120,marker='*')
ax.set(xlim=(0,D.die[2]),ylim=(0,D.die[3]),xlabel='um',ylabel='um',title='NL native CTS ICG1: actual tree / red 27 balancing delays (FAIL)')
fig.tight_layout();fig.savefig(sys.argv[2],dpi=150)
