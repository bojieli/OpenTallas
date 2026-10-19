import json,gzip
from pathlib import Path
p=Path(__file__).resolve().parent
x=json.loads((p/'placed_geometry.json').read_text());ports=x['ports'];cells=x['cells'];metrics=json.loads((p/'metrics.json').read_text());band=metrics['band_um'];area=metrics['std_area_um2'];cap=metrics['band_area_um2']
macros={n:c for n,c in cells.items() if c['block']};std={n:c for n,c in cells.items() if not c['block']};boundary={v['inst'] for v in json.loads((p/'boundary_ownership.json').read_text())}
with gzip.open(p/'reach_census.json.gz','rt') as f:legs=json.load(f)['legs']
byrole={k:sorted([v for v in legs if v['role']==k],key=lambda v:-v['manhattan_um']) for k in ('data','reset')}
def xyport(n):
 rs=ports[n]['boxes'];return [sum((a[0]+a[2])/2 for a in rs)/len(rs),sum((a[1]+a[3])/2 for a in rs)/len(rs)]
# Visualization is an artifact, never a geometry substitute.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(13,9))
for n,c in macros.items():
 a,b,cx,d=c['bbox'];ax.add_patch(Rectangle((a,b),cx-a,d-b,facecolor='#d9e8ef',edgecolor='#355968'));ax.text((a+cx)/2,(b+d)/2,n+'\nR0',ha='center',va='center',fontsize=8)
a,b,c,d=band;ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#61a96c',alpha=.8))
for n,z in std.items():
 a,b,c,d=z['bbox'];ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#882d2d' if n in boundary else '#28639c',edgecolor='none'))
for n in ports:
 xx,yy=xyport(n);ax.plot(xx,yy,'.',ms=2,color='#222222')
for role,color in [('data','#c12d2d'),('reset','#a26b00')]:
 for v in byrole[role][:3]:
  a=v['driver']['xy'];b=v['sink']['xy'];ax.plot([a[0],b[0]],[a[1],b[1]],'--',color=color,alpha=.6,lw=1)
clk=xyport('ck');ax.plot(*clk,'*',color='#f08a00',ms=12);ax.annotate('Clock entry; native phase unmeasured',clk,(390,560),arrowprops={'arrowstyle':'->'},fontsize=8)
ax.add_patch(Rectangle((0,0),734.4,540,fill=False,lw=2));ax.text(367.2,211,f'Single legal band; {area:.2f} µm² / {cap:.2f} µm² = {area/cap*100:.2f}%\n645 dedicated boundary FF; full restored native graph',ha='center',fontsize=9)
ax.set(xlim=(-20,755),ylim=(-20,580),aspect='equal',xlabel='µm',ylabel='µm');ax.set_title('AHUB revised source: exact native placement and reach preflight\nGeometry only; no CTS / routing / PG / timing qualification');fig.tight_layout();fig.savefig(p/'placement.png',dpi=160)
