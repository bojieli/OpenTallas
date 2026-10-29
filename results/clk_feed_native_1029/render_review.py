from pathlib import Path
import sys,json,pickle
sys.path.insert(0,str(Path('tools/die_plan').resolve()))
import die_trial as D
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
R=Path('review03');R.mkdir(exist_ok=True)
t=json.load(open('geometry_feed03/clock/tree.json'))
a,k=pickle.load(open('preexport.pkl','rb'));site=a[3];nodes=t['nodes'];xy=t['sites']
fixed=[(i,n) for i,n in nodes.items() if n.get('reach_fix')]
fig,axs=plt.subplots(3,3,figsize=(15,11),dpi=140)
for ax,(i,n) in zip(axs.flat,fixed):
 p=nodes[str(n['parent'])];chain=n['physical_leg']['chain'];xx=[q[0] for q in chain];yy=[q[1] for q in chain]
 lo=(min(xx)-120,min(yy)-120);hi=(max(xx)+120,max(yy)+120)
 for r in site.forb:
  if r[0]<hi[0] and r[2]>lo[0] and r[1]<hi[1] and r[3]>lo[1]:ax.add_patch(Rectangle(r[:2],r[2]-r[0],r[3]-r[1],fc='.8',ec='.5',lw=.3))
 c=[v for v in xy.values() if lo[0]<=v[0]<=hi[0] and lo[1]<=v[1]<=hi[1]]
 if c:ax.scatter([v[0] for v in c],[v[1] for v in c],s=3,c='tab:blue')
 ax.plot(xx,yy,'o-',c='crimson',ms=3,lw=1)
 ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_aspect('equal');ax.tick_params(labelsize=5)
 ax.set_title(f"FEED {i}: old {n['reach_fix']['span_before_um']:.1f} um; new {max(D.chain_spans(chain)):.1f} um",fontsize=8)
fig.suptitle('S81 global FEED repair: frozen native bodies / grey macro+PHY exclusions / blue clock cells / red repaired chain\nGeometry only; PG/actual routing and CA on current composed plan remain pending',fontsize=11)
fig.tight_layout();fig.savefig(R/'feed_zoom.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(14,11),dpi=140)
for r in site.parts:ax.add_patch(Rectangle(r[:2],r[2]-r[0],r[3]-r[1],fill=False,ec='.65',lw=.25))
lines=[(xy[a],xy[b]) for a,b in t['parent_of'].items()]
ax.add_collection(LineCollection(lines,lw=.35,colors='steelblue',alpha=.6))
for i,n in fixed:ax.plot(*zip(*n['physical_leg']['chain']),c='crimson',lw=1.3)
ax.set_xlim(0,site.W);ax.set_ylim(0,site.H);ax.set_aspect('equal');ax.set_title('S81 frozen physical clock: 43,378 cells, 8,501 tap edges; max wire 389.988 um / zero over 405\nFEED balancing residual max 6.289 ps (4 declared overshoots); no actual timing/PG qualification')
fig.tight_layout();fig.savefig(R/'clock_global.png');plt.close(fig)
print('CLOCK_REVIEW_IMAGES_DONE')
