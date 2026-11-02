import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent
rows=list(csv.DictReader((r/'placed.csv').open()));meta=json.load(open(r/'regions.json'))
fig,ax=plt.subplots(figsize=(11,10))
colors={'tap':'#c5cbd0','logic':'#407b9d','ff':'#d59637'}
for kind in ['tap','logic','ff']:
 pts=[v for v in rows if v['kind']==kind]
 ax.scatter([float(v['x'])+float(v['w'])/2 for v in pts],[float(v['y'])+float(v['h'])/2 for v in pts],s=.35 if kind!='ff' else .6,c=colors[kind],alpha=.50,label=f'{kind}: {len(pts)}',rasterized=True)
for v in [v for v in rows if v['kind']=='macro']:
 ax.add_patch(Rectangle((float(v['x']),float(v['y'])),float(v['w']),float(v['h']),facecolor='#adb9c2',edgecolor='black'))
x0,y0,x1,y1=meta['die'];ax.set(xlim=(x0,x1),ylim=(y0,y1),xlabel='x (um)',ylabel='y (um)',aspect='equal')
ax.legend(loc='upper right',markerscale=8);ax.set_title('Actual PV P1 5_route.odb — read-only geometry LOOK\nP2 legalization 6 overlap / 6 padding remains FAIL; no timing/source/route credit')
fig.tight_layout();fig.savefig(r/'actual_p1.png',dpi=180)
