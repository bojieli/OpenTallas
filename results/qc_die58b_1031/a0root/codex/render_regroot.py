from pathlib import Path
import re,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path('/home/ubuntu/tmp/codex-qca0/icg0')
d=json.loads((p/'core_infra_plan.json').read_text());W,H=d['outline_um']
fig,ax=plt.subplots(figsize=(7,15));ax.add_patch(Rectangle((0,0),W,H,fc='white',ec='black'))
sizes={}
for lf in p.glob('*.lef'):
 m=re.search(r'MACRO\s+(\S+).*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lf.read_text(),re.S)
 if m:sizes[m[1]]=tuple(map(float,m.groups()[1:]))
for part in (p/'macro_place.tcl').read_text().split('set hit {}')[1:]:
 m=re.search(r'getMaster\] getName\] eq "([^"]+)"',part);xy=re.findall(r'round\(([\d.]+) \* \$dbu\)',part)
 if m and len(xy)>=2:
  w,h=sizes[m[1]];x,y=map(float,xy[:2]);ax.add_patch(Rectangle((x,y),w,h,fc='#c9d7e6',ec='#345',lw=.7,hatch='//'))
xx=[];yy=[]
for l in (p/'regroot_graph_homes.tsv').read_text().splitlines():
 f=l.split('\t')
 if len(f)>=3:xx.append(float(f[1]));yy.append(float(f[2]))
ax.scatter(xx,yy,s=.5,c='#4466aa',alpha=.25,label='Planned register homes')
pins=json.loads((p/'pins.json').read_text());ax.scatter([v['x'] for v in pins],[v['y'] for v in pins],s=1,c='#229944')
cx,cy=d['clock_entry']['xy_um'];gx,gy=228.972,730.93
ax.scatter([cx],[cy],s=120,marker='*',c='#ffcc00',ec='black',zorder=6,label='Clock entry')
ax.scatter([gx],[gy],s=65,marker='s',c='#d13b31',ec='black',zorder=7,label='Registered root gate')
ax.plot([cx,gx],[cy,gy],c='#cc7a00',lw=2)
for x,y,name in [(9.8,800.556,'n_a valid/fault'),(9.8,900.78,'n_b valid/fault'),(448.1,561.036,'go face')]:
 ax.plot([x,gx],[y,gy],c='#a32040',lw=1,ls='--');ax.annotate(name,(x,y),(x+8,y+12),fontsize=7,color='#a32040')
 dist=abs(gx-x)+abs(gy-y);ax.text((gx+x)/2,(gy+y)/2,f'{dist:.1f} um',fontsize=7,color='#a32040')
ax.text(268,270,'GRT50 pinch watch',fontsize=7,c='red')
ax.set(xlim=(-15,W+15),ylim=(-15,H+15),xlabel='x (um)',ylabel='y (um)',title='NK registered root structural trial planning review\nICG1 / EREG1; direct ENA legs <=405um, unchanged data homes')
ax.set_aspect('equal');ax.legend(loc='upper center',fontsize=7);fig.tight_layout();fig.savefig(p/'regroot-plan.png',dpi=150)
print('Rendered',len(xx),'register homes; direct ENA max',max(abs(gx-x)+abs(gy-y) for x,y in [(9.8,800.556),(9.8,900.78),(448.1,561.036)]))
